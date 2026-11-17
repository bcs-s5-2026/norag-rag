"""Recipe v2 (V3 rebuild): heading context, per-triple validation, separate budget. Provider mocked."""
import json
from unittest.mock import Mock

import pytest

from rag_app import graph as cli
from rag_app.graph_build import GraphBuilder, GraphConfig, GraphError
from rag_app.graph_retrieval import GraphIndex
from rag_app.graph_schema import ProviderResponse, filter_extraction, section_context
from rag_app.models import Settings

RUNBOOK = ('# Runbook\n\n## Connectors (KST-2xxx)\n\n### KST-2040 — Connection timed out\n\n'
           '**Cause:** connector-hub could not reach the source.\n'
           '**Escalate:** to Data Integrations if it repeats.\n')


def t(subject, s_type, relation, obj, o_type, quote, condition=None):
    return dict(subject=dict(type=s_type, label=subject), relation=relation,
                object=dict(type=o_type, label=obj), evidence_quote=quote, condition_quote=condition)


def builder(tmp_path, texts, **config):
    sources = tmp_path/'sources'; sources.mkdir(exist_ok=True)
    for name, text in texts.items():
        (sources/name).write_text(text)
    return GraphBuilder(data_dir=tmp_path/'runtime', source_dir=sources,
                        config=GraphConfig(recipe='v2', **config))


def test_section_context_heading_path_and_table_header():
    assert section_context(RUNBOOK, RUNBOOK.index('**Escalate')) == (
        '# Runbook > ## Connectors (KST-2xxx) > ### KST-2040 — Connection timed out')
    table = '# G\n\n## Plans\n\n| | Free | Team |\n|---|---|---|\n| Seats | 1 | 10 |\n| Rows | 5 | 50 |\n'
    assert section_context(table, table.index('| Rows')).endswith('Table header: | | Free | Team |')
    assert 'Table header' not in section_context(table, table.index('## Plans'))


def test_filter_keeps_valid_triples_and_records_dropped():
    chunk = dict(text='**Cause:** connector-hub could not reach the source.')
    context = '### KST-2040 — Connection timed out'
    good = t('KST-2040', 'ErrorCode', 'RAISED_BY', 'connector-hub', 'Service', 'connector-hub could not reach the source')
    invented = t('KST-2040', 'ErrorCode', 'RAISED_BY', 'gateway', 'Service', 'invented quote')
    wrong_dir = t('connector-hub', 'Service', 'RAISED_BY', 'KST-2040', 'ErrorCode', 'connector-hub could not')
    heading_only = t('KST-2040', 'ErrorCode', 'ESCALATE_TO', 'Platform', 'Team', 'could not reach')
    kept, dropped = filter_extraction(json.dumps(dict(triples=[good, invented, wrong_dir, heading_only], aliases=[])),
                                      chunk, context)
    assert [x.object.label for x in kept.triples] == ['connector-hub']
    assert [d['index'] for d in dropped] == [1, 2, 3]
    with pytest.raises(ValueError):  # malformed JSON still rejects the whole response
        filter_extraction('{not json', chunk, context)
    # Without the heading the error code is unanchored, so the triple is dropped.
    assert filter_extraction(json.dumps(dict(triples=[t('KST-2040', 'ErrorCode', 'RAISED_BY', 'connector-hub',
        'Service', 'connector-hub could not reach the source')], aliases=[])), chunk, '')[0].triples == []


def test_heading_anchor_is_the_section_containing_the_quote():
    text = 'Escalate: no.\n\n### KST-1007 — Two-factor\n\n**Cause:** the auth service clock.\n'
    chunk = dict(text=text)
    context = '# Runbook > ## Sign-in > ### KST-1001 — Invalid credentials'
    wrong = t('KST-1001', 'ErrorCode', 'RAISED_BY', 'auth', 'Service', 'the auth service clock')
    right = t('KST-1007', 'ErrorCode', 'RAISED_BY', 'auth', 'Service', 'the auth service clock')
    kept, dropped = filter_extraction(json.dumps(dict(triples=[wrong, right], aliases=[])), chunk, context)
    assert [x.subject.label for x in kept.triples] == ['KST-1007'] and dropped[0]['index'] == 0


def test_v2_build_heading_provenance_budget_and_retrieval(tmp_path):
    b = builder(tmp_path, {'runbook.md': RUNBOOK})
    seen = []
    def fake(messages, config):
        payload = json.loads(messages[1]['content']); seen.append(payload)
        assert 'section_heading' in payload and 'Extract EVERY relation' in messages[0]['content']
        return ProviderResponse(text=json.dumps(dict(triples=[
            t('KST-2040', 'ErrorCode', 'RAISED_BY', 'connector-hub', 'Service', 'connector-hub could not reach the source'),
            t('KST-2040', 'ErrorCode', 'ESCALATE_TO', 'Data Integrations', 'Team',
              '**Escalate:** to Data Integrations if it repeats.', 'if it repeats'),
            t('KST-2040', 'ErrorCode', 'RAISED_BY', 'gateway', 'Service', 'not in the chunk')], aliases=[])),
            model='mock', input_tokens=10, output_tokens=5)
    graph = b.build(approved=True, extractor=Mock(side_effect=fake), max_calls=120)
    assert graph['complete'] and len(graph['relations']) == 2
    assert graph['build_stats']['kept_triples'] == 2 and graph['build_stats']['dropped_items'] == 1
    assert graph['manifest']['recipe']['prompt_version'] == 'kestrel-grounded-extraction-v2'
    proofs = [p for p in graph['provenance'] if 'context_heading' in p]
    assert proofs and all('KST-2040' in p['context_heading'] for p in proofs)
    with pytest.raises(GraphError):
        b.build(approved=True, extractor=Mock(), max_calls=121)
    # v1 and v2 builds of the same sources never share a build ID or cache.
    v1 = GraphBuilder(data_dir=tmp_path/'runtime', source_dir=tmp_path/'sources')
    assert v1.build_id != b.build_id and v1.cache_key(v1.rows[0]) != b.cache_key(b.rows[0])
    # Retrieval validates the snapshot and follows the heading-anchored edges.
    index = GraphIndex(graph)
    results, trace = index.search('Who handles KST-2040?', [b.rows[0]['document_id']], Settings())
    assert results and trace['matched_entities'][0]['label'] == 'KST-2040'
    assert {e['relation'] for p in trace['paths'] for e in p['edges']} >= {'RAISED_BY', 'ESCALATE_TO'}


def test_cli_export_bundle(tmp_path, monkeypatch, capsys):
    b = builder(tmp_path, {'runbook.md': RUNBOOK})
    b.build(approved=True, extractor=Mock(return_value=ProviderResponse(
        text=json.dumps(dict(triples=[], aliases=[])), model='mock')))
    monkeypatch.setattr('rag_app.graph.GraphBuilder',
                        lambda **kw: GraphBuilder(source_dir=tmp_path/'sources', **kw))
    assert cli.main(['export', '--recipe', 'v2', '--data-dir', str(tmp_path/'runtime'),
                     '--out', str(tmp_path/'bundle')]) == 0
    assert (tmp_path/'bundle'/'graph.json').exists() and (tmp_path/'bundle'/'attempts.json').exists()
    assert len(list((tmp_path/'bundle'/'extraction_cache').glob('*.json'))) == 1


def test_common_word_entity_needs_matching_case(tmp_path):
    text = '# Guide\n\n## Plans\n\nPublic share links are available on the Team plan.\n'
    b = builder(tmp_path, {'guide.md': text})
    b.build(approved=True, extractor=Mock(return_value=ProviderResponse(text=json.dumps(dict(triples=[
        t('Public share links', 'Feature', 'AVAILABLE_ON', 'Team', 'Plan',
          'Public share links are available on the Team plan.')], aliases=[])), model='mock')))
    index = GraphIndex(b.inspect())
    doc = [b.rows[0]['document_id']]
    _, trace = index.search("Which team's channel handles this?", doc, Settings())
    assert all(s['label'] != 'Team' for s in trace['matched_entities'])
    _, trace = index.search('Is it on the Team plan?', doc, Settings())
    assert any(s['label'] == 'Team' and s['matched_by'] == 'exact_name' for s in trace['matched_entities'])
