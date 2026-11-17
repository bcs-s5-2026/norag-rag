"""Concept graph construction contracts. Every provider call is mocked."""
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from rag_app import graph as cli
from rag_app.graph_build import (GraphBuilder, GraphConfig, GraphError, GoogleExtractor,
                                 atomic_json, digest, source_chunks)
from rag_app.graph_schema import Extraction, ProviderResponse, normalize, validate_extraction
from rag_app.models import Settings


def triple(subject='postroom', obj='Messaging', quote='postroom is owned by Messaging.'):
    return dict(subject={'type': 'Service', 'label': subject}, relation='OWNED_BY',
                object={'type': 'Team', 'label': obj}, evidence_quote=quote, condition_quote=None)


def extraction(triples=None, aliases=None):
    return json.dumps(dict(triples=[triple()] if triples is None else triples, aliases=aliases or []))


def reply(text=None, **kwargs):
    return ProviderResponse(text=text or extraction(), model='mock-extraction-model',
                            input_tokens=kwargs.pop('input_tokens', 100),
                            output_tokens=kwargs.pop('output_tokens', 50), **kwargs)


def builder(tmp_path, texts=None, **kwargs):
    sources = tmp_path/'sources'; sources.mkdir(exist_ok=True)
    for name, text in (texts or {'a.md': 'postroom is owned by Messaging.'}).items():
        (sources/name).write_text(text)
    return GraphBuilder(data_dir=tmp_path/'runtime', source_dir=sources, **kwargs)


def test_normalization_preserves_identity_distinctions():
    assert normalize('  Ｐlatform\n TEAM ') == 'platform team'
    assert normalize('KST–2044') == 'kst-2044'
    assert normalize('KST-2044') != normalize('KST-2040')
    assert normalize('mailman') != normalize('postroom')
    assert normalize('Café') != normalize('Cafe')


def test_valid_and_empty_extraction():
    chunk = {'text': 'postroom is owned by Messaging.'}
    assert len(validate_extraction(extraction(), chunk).triples) == 1
    assert validate_extraction(extraction([]), chunk).triples == []


@pytest.mark.parametrize('damage', ['unknown_type', 'unknown_relation', 'direction', 'extra',
                                    'missing_quote', 'wrong_entity', 'condition', 'blank_label', 'identifier'])
def test_rejects_invalid_whole_outputs(damage):
    t = triple()
    if damage == 'unknown_type': t['subject']['type'] = 'Anything'
    if damage == 'unknown_relation': t['relation'] = 'INFERRED_FROM'
    if damage == 'direction': t['subject'], t['object'] = t['object'], t['subject']
    if damage == 'extra': t['confidence'] = 1
    if damage == 'missing_quote': t['evidence_quote'] = 'This sentence was invented.'
    if damage == 'wrong_entity': t['subject']['label'] = 'ledger'
    if damage == 'condition': t['condition_quote'] = 'if it rains'
    if damage == 'blank_label': t['subject']['label'] = ' '
    if damage == 'identifier': t['subject'] = {'type': 'ErrorCode', 'label': 'KST-204'}
    with pytest.raises(ValueError):
        validate_extraction(extraction([triple(), t]), {'text': 'postroom is owned by Messaging.'})


def test_endpoint_anchor_is_not_weak_substring():
    t = triple(subject='auth', quote='author is owned by Messaging.')
    with pytest.raises(ValueError, match='endpoint'):
        validate_extraction(extraction([t]), {'text': t['evidence_quote']})


def test_historical_replacement_is_not_alias():
    alias = dict(canonical={'type': 'Service', 'label': 'postroom'}, alias='mailman',
                 evidence_quote='postroom replaced the older mailman service.')
    with pytest.raises(ValueError, match='Historical'):
        validate_extraction(extraction([], [alias]), {'text': alias['evidence_quote']})


def test_real_kestrel_dry_run_zero_external_side_effects(tmp_path, monkeypatch):
    monkeypatch.setattr('rag_app.graph_build.GoogleExtractor', Mock(side_effect=AssertionError('client initialized')))
    runtime = tmp_path/'data'
    b = GraphBuilder(data_dir=runtime)
    plan = b.plan()
    assert plan['chunks'] == 43 and plan['pending_chunks'] == 43
    assert plan['first_pass_calls'] == 43 and plan['dispatchable_calls_now'] == 43
    assert plan['model'] == 'gemini-3.5-flash-lite'
    assert plan['llm_calls_made_by_dry_run'] == 0
    assert plan['approximate_input_tokens'] > 0 and plan['estimated_first_pass_usd'] > 0
    assert not runtime.exists()
    assert [s['name'] for s in plan['documents']] == sorted(s['name'] for s in plan['documents'])
    for row in b.rows:
        assert row['id'] == f"{row['document_id']}:{row['start']}:{row['end']}"


def test_key_does_not_authorize_external_dispatch(tmp_path, monkeypatch):
    b = builder(tmp_path)
    client = Mock()
    monkeypatch.setenv('GOOGLE_API_KEY', 'test-only-placeholder')
    with pytest.raises(GraphError, match='approval'):
        b.build(extractor=client)
    client.assert_not_called()
    assert not b.root.exists()
    with pytest.raises(GraphError, match='approval'):
        GoogleExtractor()(None, GraphConfig())


def test_persistence_provenance_and_cache_resume(tmp_path):
    b = builder(tmp_path, {'a.md': 'postroom is owned by Messaging.',
                           'b.md': 'Postroom is owned by Messaging.'})
    def fake(messages, config):
        chunk = json.loads(messages[1]['content'])['chunk']
        subject = 'Postroom' if chunk['name'] == 'b.md' else 'postroom'
        return reply(extraction([triple(subject=subject, quote=chunk['text'])]))
    client = Mock(side_effect=fake)
    graph = b.build(approved=True, extractor=client)
    assert graph['complete'] and client.call_count == 2
    assert len(graph['entities']) == 2 and len(graph['relations']) == 1
    assert graph['build_stats']['reserved_llm_calls'] == 2
    assert graph['build_stats']['input_tokens'] == 200 and graph['build_stats']['output_tokens'] == 100
    assert graph['last_run']['latency_seconds'] >= 0
    assert graph['build_stats']['actual_model_identifiers'] == ['mock-extraction-model']
    assert any(d['kind'] == 'normalized_exact' for d in graph['merge_decisions'])
    by_proof = {p['id']: p for p in graph['provenance']}
    for entity in graph['entities']:
        assert len(entity['provenance_ids']) == 2
        assert all(p in by_proof for p in entity['provenance_ids'])
    assert len(graph['relations'][0]['provenance_ids']) == 2
    for proof in by_proof.values():
        chunk = b.by_id[proof['chunk_id']]
        assert proof['source_document'] == chunk['name']
        assert proof['quote'] in chunk['text']
        assert proof['extraction_model'] == 'mock-extraction-model'
        assert proof['cache_key'] and proof['prompt_sha256']
    restarted = GraphBuilder(data_dir=tmp_path/'runtime', source_dir=tmp_path/'sources')
    assert restarted.inspect()['graph_content_sha256'] == graph['graph_content_sha256']
    again = restarted.build(extractor=Mock(side_effect=AssertionError('cache miss')))
    assert again['last_run']['new_reserved_calls'] == 0
    assert again['graph_content_sha256'] == graph['graph_content_sha256']


def test_explicit_alias_with_recorded_evidence(tmp_path):
    text = 'postroom is owned by Messaging. mail delivery is also called postroom.'
    b = builder(tmp_path, {'a.md': text, 'b.md': 'mail delivery is owned by Messaging.'})
    def fake(messages, config):
        chunk = json.loads(messages[1]['content'])['chunk']
        if chunk['name'] == 'a.md':
            return reply(extraction([triple(quote='postroom is owned by Messaging.')], [dict(
                canonical={'type': 'Service', 'label': 'postroom'}, alias='mail delivery',
                evidence_quote='mail delivery is also called postroom.')]))
        return reply(extraction([triple(subject='mail delivery', quote=chunk['text'])]))
    graph = b.build(approved=True, extractor=fake)
    assert len([e for e in graph['entities'] if e['type'] == 'Service']) == 1
    assert len(graph['relations']) == 1
    assert any(d['kind'] == 'explicit_alias' and d['merged'] and d['provenance_ids'] for d in graph['merge_decisions'])


def test_weakly_related_services_and_policy_versions_stay_separate(tmp_path):
    texts = {'a.md': 'Billing Policy defines Annual refund at 30 days.',
             'b.md': 'Billing Policy defines Annual refund at 60 days.',
             'c.md': 'mailman was replaced by postroom.'}
    b = builder(tmp_path, texts)
    def fake(messages, config):
        chunk = json.loads(messages[1]['content'])['chunk']
        if chunk['name'] == 'c.md':
            t = dict(subject={'type': 'Service', 'label': 'mailman'}, relation='REPLACED_BY',
                     object={'type': 'Service', 'label': 'postroom'}, evidence_quote=chunk['text'])
        else:
            t = dict(subject={'type': 'Policy', 'label': 'Billing Policy'}, relation='HAS_RULE',
                     object={'type': 'Rule', 'label': 'Annual refund'}, evidence_quote=chunk['text'])
        return reply(extraction([t]))
    graph = b.build(approved=True, extractor=fake)
    assert len([e for e in graph['entities'] if e['type'] == 'Policy']) == 2
    assert len([e for e in graph['entities'] if e['type'] == 'Rule']) == 2
    assert len([e for e in graph['entities'] if e['type'] == 'Service']) == 2


def test_validation_quarantine_partial_resume_and_usage(tmp_path):
    b = builder(tmp_path, {'a.md': 'postroom is owned by Messaging.', 'b.md': 'Other: postroom is owned by Messaging.'})
    client = Mock(side_effect=[reply('not JSON'), reply()])
    graph = b.build(approved=True, extractor=client)
    assert not graph['complete'] and graph['coverage']['valid_chunks'] == 1
    assert graph['build_stats']['validation_rejections'] == 1
    assert graph['build_stats']['input_tokens'] == 200
    assert len(list((b.root/'quarantine').glob('*.json'))) == 1
    assert not (b.root/'latest.json').exists()
    resumed = b.build(approved=True, extractor=Mock(return_value=reply()))
    assert resumed['complete'] and resumed['last_run']['cache_hits'] == 1
    assert resumed['last_run']['new_reserved_calls'] == 1
    assert resumed['build_stats']['reserved_llm_calls'] == 3


def test_provider_failure_halts_dispatch_unknown_usage_and_resumes(tmp_path):
    b = builder(tmp_path, {'a.md': 'postroom is owned by Messaging.', 'b.md': 'B: postroom is owned by Messaging.',
                           'c.md': 'C: postroom is owned by Messaging.'})
    client = Mock(side_effect=[reply(), RuntimeError('private credential detail')])
    graph = b.build(approved=True, extractor=client)
    assert client.call_count == 2 and not graph['complete']
    assert graph['build_stats']['provider_failures'] == 1
    assert graph['build_stats']['input_tokens'] is None
    assert graph['build_stats']['known_input_tokens'] == 100
    assert graph['build_stats']['input_usage_unknown_calls'] == 1
    assert graph['pending'][-1]['reason'] == 'provider_halted'
    assert 'private credential detail' not in json.dumps(graph)
    assert b.build(approved=True, extractor=Mock(return_value=reply()))['complete']


def test_budget_and_chunk_attempt_limits_are_durable(tmp_path):
    b = builder(tmp_path)
    invalid = Mock(return_value=reply('bad'))
    assert not b.build(approved=True, extractor=invalid, max_calls=1)['complete']
    assert not b.build(approved=True, extractor=invalid, max_calls=1)['complete']
    assert invalid.call_count == 1
    assert not b.build(approved=True, extractor=invalid, max_calls=3, max_attempts=2)['complete']
    assert invalid.call_count == 2
    assert not b.build(approved=True, extractor=invalid, max_calls=3, max_attempts=2)['complete']
    assert invalid.call_count == 2 and b.plan(max_calls=3)['dispatchable_calls_now'] == 0


def test_interruption_reuses_valid_cache_and_counts_unresolved_attempt(tmp_path):
    b = builder(tmp_path, {'a.md': 'postroom is owned by Messaging.', 'b.md': 'B: postroom is owned by Messaging.'})
    with pytest.raises(KeyboardInterrupt):
        b.build(approved=True, extractor=Mock(side_effect=[reply(), KeyboardInterrupt()]))
    assert b.plan()['cached_valid'] == 1
    graph = b.build(approved=True, extractor=Mock(return_value=reply()))
    assert graph['complete'] and graph['last_run']['new_reserved_calls'] == 1
    assert graph['build_stats']['unresolved_calls'] == 1
    assert graph['build_stats']['reserved_llm_calls'] == 3
    assert graph['build_stats']['input_tokens'] is None


def test_corrupt_cache_readonly_plan_and_quarantined_rebuild(tmp_path):
    b = builder(tmp_path)
    b.build(approved=True, extractor=Mock(return_value=reply()))
    path = next((b.root/'cache').glob('*.json'))
    path.write_text('{broken')
    assert b.plan()['invalid_cache_entries'] == 1 and path.read_text() == '{broken'
    graph = b.build(approved=True, extractor=Mock(return_value=reply()))
    assert graph['complete'] and list((b.root/'quarantine').glob('cache-*.json'))


def test_cache_recipe_change_and_incremental_source_update(tmp_path):
    b = builder(tmp_path, {'a.md': 'postroom is owned by Messaging.', 'b.md': 'B: postroom is owned by Messaging.'})
    b.build(approved=True, extractor=Mock(return_value=reply()))
    changed_model = GraphBuilder(data_dir=tmp_path/'runtime', source_dir=tmp_path/'sources', config=GraphConfig(model='other-model'))
    assert changed_model.build_id != b.build_id and changed_model.plan()['pending_chunks'] == 2
    assert changed_model.plan()['estimated_first_pass_usd'] is None
    (tmp_path/'sources/b.md').write_text('Changed: postroom is owned by Messaging.')
    changed = GraphBuilder(data_dir=tmp_path/'runtime', source_dir=tmp_path/'sources')
    assert changed.build_id != b.build_id and changed.plan()['cached_valid'] == 1
    assert changed.build(approved=True, extractor=Mock(return_value=reply()))['last_run']['new_reserved_calls'] == 1


def test_manual_alias_reuses_cache_without_external_calls(tmp_path):
    b = builder(tmp_path, {'a.md': 'postroom is owned by Messaging. mail delivery is also called postroom.'})
    b.build(approved=True, extractor=Mock(return_value=reply()))
    alias = dict(canonical={'type': 'Service', 'label': 'postroom'}, alias='mail delivery',
                 evidence_quote='mail delivery is also called postroom.', chunk_id=b.rows[0]['id'])
    changed = GraphBuilder(data_dir=tmp_path/'runtime', source_dir=tmp_path/'sources', aliases=[alias])
    assert changed.build_id != b.build_id and changed.plan()['cached_valid'] == 1
    graph = changed.build(extractor=Mock(side_effect=AssertionError('called')))
    assert graph['complete'] and graph['build_stats']['reserved_llm_calls'] == 0
    assert any(p['kind'] == 'manual_explicit_alias' for p in graph['provenance'])


def test_cache_only_partial_and_empty_extraction_coverage(tmp_path):
    b = builder(tmp_path)
    graph = b.build(cache_only=True)
    assert not graph['complete'] and graph['build_stats']['reserved_llm_calls'] == 0
    done = b.build(approved=True, extractor=Mock(return_value=reply(extraction([]))))
    assert done['complete'] and done['coverage']['empty_extractions'] == 1
    assert not done['entities'] and not done['relations']


def test_output_truncation_is_quarantined(tmp_path):
    b = builder(tmp_path)
    graph = b.build(approved=True, extractor=Mock(return_value=reply(finish_reason='length')))
    assert not graph['complete'] and graph['build_stats']['validation_rejections'] == 1


def test_writer_lock_atomic_file_and_inspection_integrity(tmp_path, monkeypatch):
    b = builder(tmp_path)
    with b.lock():
        with pytest.raises(GraphError, match='Another graph build'):
            b.build(cache_only=True)
    graph = b.build(approved=True, extractor=Mock(return_value=reply()))
    target = b.directory/'graph.json'; original = target.read_bytes()
    with monkeypatch.context() as mp:
        mp.setattr('rag_app.graph_build.os.replace', Mock(side_effect=OSError('disk failed')))
        with pytest.raises(OSError): atomic_json(target, {'bad': True})
    assert target.read_bytes() == original and not list(b.directory.glob('*.tmp'))
    damaged = copy.deepcopy(graph); damaged['entities'][0]['label'] = 'corrupt'
    target.write_text(json.dumps(damaged))
    with pytest.raises(GraphError, match='checksum'):
        b.inspect()
    with pytest.raises(GraphError, match='Invalid build'):
        b.inspect('../outside')


def test_duplicate_source_content_rejected(tmp_path):
    with pytest.raises(GraphError, match='Duplicate source'):
        builder(tmp_path, {'a.md': 'same', 'b.md': 'same'})


def test_google_adapter_uses_explicit_model_budget_and_no_sdk_retries(monkeypatch):
    monkeypatch.setenv('GOOGLE_API_KEY', 'test-only-placeholder')
    monkeypatch.setenv('GOOGLE_MODEL', 'must-not-be-used')
    monkeypatch.setattr('dotenv.load_dotenv', Mock())
    response = SimpleNamespace(id='mock-response', model='actual-mock-model',
               usage=SimpleNamespace(prompt_tokens=123, completion_tokens=45),
               choices=[SimpleNamespace(message=SimpleNamespace(content=extraction()), finish_reason='stop')])
    client = Mock(); client.chat.completions.create.return_value = response
    factory = Mock(return_value=client)
    monkeypatch.setattr('openai.OpenAI', factory)
    result = GoogleExtractor(approved=True)([{'role': 'user', 'content': 'MOCK ONLY'}], GraphConfig())
    assert result.input_tokens == 123 and result.output_tokens == 45
    assert factory.call_args.kwargs['max_retries'] == 0
    params = client.chat.completions.create.call_args.kwargs
    assert params['model'] == 'gemini-3.5-flash-lite' and params['max_tokens'] == 4096
    assert 'tools' not in params


def test_cli_dry_run_approval_and_inspection(tmp_path, monkeypatch, capsys):
    runtime = tmp_path/'runtime'
    output = tmp_path/'estimate.json'
    assert cli.main(['build', '--dry-run', '--data-dir', str(runtime), '--estimate-output', str(output)]) == 0
    assert json.loads(output.read_text())['pending_chunks'] == 43 and not runtime.exists()
    with pytest.raises(SystemExit) as exc:
        cli.main(['build', '--data-dir', str(runtime)])
    assert exc.value.code == 2 and not runtime.exists()
    b = builder(tmp_path)
    b.build(approved=True, extractor=Mock(return_value=reply()))
    monkeypatch.setattr(cli, 'GraphBuilder', lambda **kwargs: b)
    assert cli.main(['inspect']) == 0
    assert cli.main(['resume', '--cache-only']) == 0
    assert 'mock-extraction-model' in capsys.readouterr().out


def test_alias_name_cooccurrence_is_not_identity():
    alias = dict(canonical={'type': 'Service', 'label': 'postroom'}, alias='auth',
                 evidence_quote='postroom and auth work together.')
    with pytest.raises(ValueError, match='equivalence'):
        validate_extraction(extraction([], [alias]), {'text': alias['evidence_quote']})


def test_model_preflight_failure_records_zero_dispatches(tmp_path, monkeypatch):
    b = builder(tmp_path)
    monkeypatch.setenv('GOOGLE_API_KEY', '')
    monkeypatch.setattr('dotenv.load_dotenv', Mock())
    with pytest.raises(GraphError, match='preflight failed'):
        b.build(approved=True)
    assert b.attempts() == []
    runs = [json.loads(p.read_text()) for p in (b.directory/'runs').glob('*.json')]
    assert runs[0]['status'] == 'preflight_failed'


def test_stable_entity_and_relation_ids_across_same_response_rebuild(tmp_path):
    b = builder(tmp_path)
    first = b.build(approved=True, extractor=Mock(return_value=reply()))
    next((b.root/'cache').glob('*.json')).unlink()
    second = b.build(approved=True, extractor=Mock(return_value=reply()))
    assert [e['id'] for e in first['entities']] == [e['id'] for e in second['entities']]
    assert [e['id'] for e in first['relations']] == [e['id'] for e in second['relations']]


def test_absent_provider_usage_is_unknown_even_for_valid_output(tmp_path):
    b = builder(tmp_path)
    graph = b.build(approved=True, extractor=Mock(return_value=reply(input_tokens=None, output_tokens=None)))
    assert graph['complete']
    assert graph['build_stats']['input_tokens'] is None and graph['build_stats']['output_tokens'] is None
    assert not graph['build_stats']['cost_complete']
    assert graph['extractions'][0]['input_tokens'] is None


def test_condition_provenance_and_distinct_conditional_edges(tmp_path):
    sentence = 'If several deliveries fail, KST-5031 is escalated to Messaging.'
    b = builder(tmp_path, {'a.md': sentence})
    t = dict(subject={'type': 'ErrorCode', 'label': 'KST-5031'}, relation='ESCALATE_TO',
             object={'type': 'Team', 'label': 'Messaging'}, evidence_quote=sentence,
             condition_quote='If several deliveries fail')
    graph = b.build(approved=True, extractor=Mock(return_value=reply(extraction([t]))))
    assert graph['relations'][0]['condition_quote'] == t['condition_quote']
    assert graph['provenance'][0]['quote'] == sentence


def test_prompt_change_invalidates_extraction_cache(tmp_path, monkeypatch):
    b = builder(tmp_path)
    b.build(approved=True, extractor=Mock(return_value=reply()))
    monkeypatch.setattr('rag_app.graph_build.PROMPT_VERSION', 'test-prompt-v2')
    next_builder = GraphBuilder(data_dir=tmp_path/'runtime', source_dir=tmp_path/'sources')
    assert next_builder.build_id != b.build_id and next_builder.plan()['cached_valid'] == 0


def test_hard_43_request_limit_cannot_be_raised(tmp_path):
    b = builder(tmp_path)
    client = Mock()
    with pytest.raises(GraphError, match='Hard extraction limit'):
        b.plan(max_calls=44)
    with pytest.raises(GraphError, match='Hard extraction limit'):
        b.build(approved=True, extractor=client, max_calls=44)
    client.assert_not_called()
    assert not b.root.exists()


def test_source_allowlist_ignores_unrelated_files_and_rejects_symlinks(tmp_path):
    from rag_app.graph_build import source_chunks
    (tmp_path/'approved.md').write_text('approved source')
    (tmp_path/'unrelated.md').write_text('must never be included')
    rows, sources = source_chunks(tmp_path, Settings(), allowed_names=['approved.md'])
    assert {r['name'] for r in rows} == {'approved.md'}
    assert [s['name'] for s in sources] == ['approved.md']
    (tmp_path/'link.md').symlink_to(tmp_path/'unrelated.md')
    with pytest.raises(GraphError, match='symlinks'):
        source_chunks(tmp_path, Settings(), allowed_names=['link.md'])
