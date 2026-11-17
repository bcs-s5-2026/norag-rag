"""RRF contracts, opt-in service/API, retrieval-only CLI and V2 compatibility."""
import copy
import json
import math
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from evaluation import v3
from rag_app.api import create_app
from rag_app.fusion import reciprocal_rank_fusion as rrf
from rag_app.models import RetrievalConfig, Settings
from rag_app.service import PipelineError, RagService


def row(identifier, score=0.5, **fields):
    return dict(id=identifier, document_id='doc', name='doc.md', text=identifier,
                similarity=score, score=score, **fields)


def test_rrf_numeric_scoring_order_and_provenance():
    rankings = {'dense': [row('a', 0.9), row('b', 0.8)],
                'bm25': [row('b', 7), row('c', 3)]}
    original = copy.deepcopy(rankings)
    results = rrf(rankings, 60, 10)
    assert [r['id'] for r in results] == ['b', 'a', 'c']
    assert results[0]['rrf_score'] == pytest.approx(1/62+1/61)
    assert results[1]['rrf_score'] == pytest.approx(1/61)
    assert results[0]['origins'] == {'bm25': {'rank': 1, 'raw_score': 7},
                                     'dense': {'rank': 2, 'raw_score': 0.8}}
    assert [r['fused_rank'] for r in results] == [1, 2, 3]
    assert 'similarity' not in results[0] and 'score' not in results[0]
    assert rankings == original
    assert rrf(rankings, 0, 1)[0]['rrf_score'] == pytest.approx(1+1/2)
    assert rrf(rankings, 10, 2)[0]['rrf_score'] == pytest.approx(1/11+1/12)


def test_duplicate_ids_one_contribution_and_contiguous_ranks():
    results = rrf({'dense': [row('a'), row('a'), row('b')],
                   'bm25': [row('b'), row('a'), row('a')]}, top_k=10)
    assert len(results) == 2
    lookup = {r['id']: r for r in results}
    assert lookup['a']['origins']['dense']['rank'] == 1
    assert lookup['b']['origins']['dense']['rank'] == 2
    assert lookup['a']['rrf_score'] == pytest.approx(1/61+1/62)


def test_conflicting_chunk_data_rejected():
    corrupt = row('a')
    corrupt['text'] = 'different source'
    with pytest.raises(ValueError, match='Conflicting'):
        rrf({'dense': [row('a')], 'bm25': [corrupt]})
    with pytest.raises(ValueError, match='stable ID'):
        rrf({'dense': [{'text': 'no ID'}]})


def test_ties_ignore_retriever_mapping_order_and_raw_scores():
    rankings = {'dense': [row('z', 100), row('a', -2)],
                'bm25': [row('a', 0.1), row('z', 1000)]}
    first = rrf(rankings)
    assert [r['id'] for r in first] == ['a', 'z']
    assert first[0]['rrf_score'] == first[1]['rrf_score']
    assert first == rrf(dict(reversed(list(rankings.items()))))


@pytest.mark.parametrize('rankings', [{}, {'dense': []}, {'dense': [], 'bm25': []}])
def test_empty_rankings(rankings):
    assert rrf(rankings) == []


@pytest.mark.parametrize('kwargs', [{'rank_constant': -1}, {'rank_constant': 1.5},
                                   {'rank_constant': True}, {'top_k': 0}, {'top_k': True}])
def test_invalid_fusion_parameters(kwargs):
    with pytest.raises(ValueError):
        rrf({}, **kwargs)


@pytest.mark.parametrize('kwargs', [{'retrievers': []}, {'retrievers': ['unknown']},
                                   {'retrievers': ['dense', 'dense']}, {'rrf_k': -1},
                                   {'rrf_k': 1.5}, {'candidate_depth': 0}])
def test_invalid_retrieval_config(kwargs):
    with pytest.raises(ValidationError):
        RetrievalConfig(**kwargs)


def test_enabled_components_candidate_depth_and_single_modes(tmp_path, monkeypatch):
    service = RagService(tmp_path)
    dense = Mock(return_value=[row('a'), row('b')])
    sparse_index = Mock()
    sparse_index.search.return_value = [row('b', 4), row('c', 2)]
    sparse = Mock(return_value=(sparse_index, {'index': 'snapshot', 'rebuilt': False}))
    monkeypatch.setattr(service, '_dense_candidates', dense)
    monkeypatch.setattr(service, '_bm25', sparse)
    for enabled, expected in [(['dense'], ['a', 'b']), (['bm25'], ['b', 'c']),
                               (['dense', 'bm25'], ['b', 'a'])]:
        dense.reset_mock()
        sparse.reset_mock()
        config = RetrievalConfig(retrievers=enabled, candidate_depth=7)
        response = service.retrieve_configured('question', ['doc'], Settings(top_k=2), config)
        assert [r['id'] for r in response['results']] == expected
        assert set(response['retrievers']) == set(enabled)
        assert dense.call_count == int('dense' in enabled)
        assert sparse.call_count == int('bm25' in enabled)
        if 'dense' in enabled:
            assert dense.call_args.args[-1] == 7
        if 'bm25' in enabled:
            assert sparse_index.search.call_args.args == ('question', 7)
        for r in response['results']:
            assert set(r['origins']) <= set(enabled)
    assert RetrievalConfig(retrievers=['bm25', 'dense']).retrievers == ['dense', 'bm25']


def test_no_silent_fallback_on_either_failure(tmp_path, monkeypatch):
    service = RagService(tmp_path)
    config = RetrievalConfig(retrievers=['dense', 'bm25'])
    dense = Mock(side_effect=PipelineError('Vector database unavailable.'))
    sparse = Mock()
    monkeypatch.setattr(service, '_dense_candidates', dense)
    monkeypatch.setattr(service, '_bm25', sparse)
    with pytest.raises(PipelineError, match='dense retrieval failed'):
        service.retrieve_configured('q', ['doc'], Settings(), config)
    sparse.assert_not_called()
    dense.side_effect = None
    dense.return_value = [row('a')]
    sparse.side_effect = PipelineError('BM25 index unavailable.')
    with pytest.raises(PipelineError, match='bm25 retrieval failed'):
        service.retrieve_configured('q', ['doc'], Settings(), config)


def test_empty_enabled_retriever_reported_not_treated_as_failure(tmp_path, monkeypatch):
    service = RagService(tmp_path)
    monkeypatch.setattr(service, '_dense_candidates', lambda *args: [row('a')])
    index = Mock()
    index.search.return_value = []
    monkeypatch.setattr(service, '_bm25', lambda *args: (index, {'index': 'snapshot', 'rebuilt': False}))
    response = service.retrieve_configured('q', ['doc'], Settings(),
                   RetrievalConfig(retrievers=['dense', 'bm25']))
    assert len(response['results']) == 1
    assert response['retrievers']['bm25'] == {'status': 'empty', 'candidate_count': 0,
                                             'index': 'snapshot', 'index_rebuilt': False}
    response = service.retrieve_configured('q', ['doc'], Settings(), RetrievalConfig(retrievers=['bm25']))
    assert response['results'] == []


def test_missing_corrupt_and_unavailable_bm25_explicit(tmp_path, monkeypatch):
    service = RagService(tmp_path)
    doc = service.upload('a.md', b'needle')['id']
    config = RetrievalConfig(retrievers=['bm25'])
    monkeypatch.setattr(service, 'client', Mock(side_effect=AssertionError('dense invoked')))
    first = service.retrieve_configured('needle', [doc], Settings(), config)
    assert first['retrievers']['bm25']['index_rebuilt'] is True
    loaded = service.retrieve_configured('needle', [doc], Settings(), config)
    assert loaded['retrievers']['bm25']['index_rebuilt'] is False
    path = next((tmp_path/'bm25').glob('*.json'))
    path.write_text('{broken')
    recovered = service.retrieve_configured('needle', [doc], Settings(), config)
    assert recovered['retrievers']['bm25']['index_rebuilt'] is True
    assert recovered['results'] == first['results']
    path.unlink()
    monkeypatch.setattr('rag_app.bm25.os.replace', Mock(side_effect=OSError('private disk error')))
    with pytest.raises(PipelineError, match='bm25 retrieval failed') as exc:
        service.retrieve_configured('needle', [doc], Settings(), config)
    assert exc.value.status == 503 and 'private disk error' not in str(exc.value)


def test_dense_ties_resolved_before_candidate_cutoff(tmp_path, monkeypatch):
    service = RagService(tmp_path)
    monkeypatch.setattr(service, 'index', Mock())
    collection = Mock()
    collection.get.return_value = {'ids': ['a', 'z', 'b']}
    monkeypatch.setattr(service, 'collection', lambda *args: collection)
    retrieve = Mock(return_value=[row('z', 1), row('b', 0), row('a', 1)])
    monkeypatch.setattr(service, 'retrieve', retrieve)
    assert [r['id'] for r in service._dense_candidates('q', ['doc'], Settings(), 1)] == ['a']
    assert retrieve.call_args.args[-1].top_k == 3


def test_api_config_validation_and_legacy_path(tmp_path, monkeypatch):
    service = RagService(tmp_path)
    client = TestClient(create_app(service))
    monkeypatch.setattr(service, 'retrieve', Mock(return_value=[{'id': 'legacy', 'similarity': 0.7}]))
    body = {'document_ids': ['doc'], 'question': 'q'}
    assert client.post('/api/search', json=body).json() == [{'id': 'legacy', 'similarity': 0.7}]
    assert client.post('/api/retrieve', json={**body, 'retrieval': {'retrievers': []}}).status_code == 422
    assert client.post('/api/retrieve', json={**body, 'retrieval': {'candidate_depth': 1}}).status_code == 422
    monkeypatch.setattr(service, '_dense_candidates', lambda *args: [row('a')])
    result = client.post('/api/retrieve', json=body)
    assert result.status_code == 200
    assert result.json()['results'][0]['origins']['dense']['rank'] == 1
    monkeypatch.setattr(service, '_dense_candidates', Mock(side_effect=PipelineError('unavailable')))
    error = client.post('/api/retrieve', json=body)
    assert error.status_code == 503 and 'dense retrieval failed' in error.json()['error']
    assert 'results' not in error.json()


def test_real_components_corpus_isolation_and_independent_order(tmp_path):
    service = RagService(tmp_path)
    a = service.upload('a.md', b'needle alpha. '*30)['id']
    b = service.upload('b.md', b'needle beta. '*30)['id']
    settings = Settings(top_k=5)
    dense = service.retrieve('needle', [a], settings)
    sparse = service.retrieve_bm25('needle', [a], settings)
    for enabled, independent in [(['dense'], dense), (['bm25'], sparse), (['dense', 'bm25'], None)]:
        config = RetrievalConfig(retrievers=enabled)
        response = service.retrieve_configured('needle', [a], settings, config)
        assert response['results']
        assert {r['document_id'] for r in response['results']} == {a}
        if independent is not None:
            assert [r['id'] for r in response['results']] == [r['id'] for r in independent]
        assert response['results'] == service.retrieve_configured('needle', [a], settings, config)['results']
    both = service.retrieve_configured('needle', [a, b], settings, RetrievalConfig(retrievers=['dense', 'bm25']))
    assert {r['document_id'] for r in both['results']} == {a, b}


def test_v3_evaluator_selected_prefix_metrics_and_no_llm(tmp_path, monkeypatch):
    service = RagService(tmp_path)
    monkeypatch.setattr(service, 'generate', Mock(side_effect=AssertionError('LLM invoked')))
    monkeypatch.setattr(service, 'client', Mock(side_effect=AssertionError('dense invoked')))
    result = v3.evaluate(service, 'vellora', Settings(top_k=3), RetrievalConfig(retrievers=['bm25']))
    assert result['version'] == 3 and result['llm_calls'] == 0
    assert result['retrieval_depth'] == 10
    assert set(result['overall']) == {'1', '3', '5', '10'}
    assert result['unanswerable_excluded'] == 3
    for r in result['results']:
        assert r['selected'] == r['retrieved'][:3]
        assert r['retrieval_seconds'] >= 0 and r['llm_calls'] == 0
        assert all(set(p['origins']) == {'bm25'} for p in r['retrieved'])
    with pytest.raises(ValueError, match='at least'):
        v3.evaluate(service, 'vellora', Settings(), RetrievalConfig(candidate_depth=5))


def test_v3_evaluation_error_aborts_not_scored_as_miss(tmp_path, monkeypatch):
    service = RagService(tmp_path)
    monkeypatch.setattr(service, 'retrieve_configured', Mock(side_effect=PipelineError('bm25 retrieval failed')))
    with pytest.raises(PipelineError, match='bm25 retrieval failed'):
        v3.evaluate(service, 'kestrel', Settings(), RetrievalConfig(retrievers=['bm25']))


def test_cli_selection_output_and_guards(tmp_path, monkeypatch):
    output = tmp_path/'new.json'
    runner = Mock(return_value={'overall': {}, 'results': []})
    monkeypatch.setattr(v3, 'run', runner)
    v3.main(['--corpus', 'kestrel', '--retrievers', 'dense', 'bm25',
             '--candidate-depth', '30', '--rrf-k', '10', '--top-k', '7', '--output', str(output)])
    corpus, settings, config = runner.call_args.args
    assert corpus == 'kestrel' and settings.top_k == 7
    assert config.model_dump() == {'retrievers': ['dense', 'bm25'], 'candidate_depth': 30, 'rrf_k': 10}
    assert json.loads(output.read_text()) == runner.return_value
    original = output.read_bytes()
    with pytest.raises(SystemExit) as exc:
        v3.main(['--corpus', 'kestrel', '--output', str(output)])
    assert exc.value.code == 2 and output.read_bytes() == original
    with pytest.raises(SystemExit):
        v3.main(['--corpus', 'kestrel', '--candidate-depth', '5', '--output', str(tmp_path/'bad.json')])
    runner.side_effect = PipelineError('dense retrieval failed')
    with pytest.raises(SystemExit):
        v3.main(['--corpus', 'kestrel', '--output', str(tmp_path/'failure.json')])
    assert not (tmp_path/'failure.json').exists()


@pytest.mark.parametrize('corpus,size,overlap', [('kestrel', 800, 80), ('kestrel', 500, 100),
                                                ('vellora', 800, 80), ('vellora', 500, 100)])
def test_all_v2_dense_baselines_and_new_dense_only(tmp_path, corpus, size, overlap):
    from evaluation import v2
    from rag_app.service import ROOT
    service = RagService(tmp_path)
    settings = Settings(chunk_size=size, chunk_overlap=overlap)
    saved = json.loads((ROOT/'evaluation/results'/f'{corpus}-{size}-{overlap}.json').read_text())
    legacy = v2.evaluate(service, corpus, settings)
    configured = v3.evaluate(service, corpus, settings, RetrievalConfig(retrievers=['dense']))
    for result in (legacy, configured):
        assert result['overall'] == saved['overall']
        assert result['by_type'] == saved['by_type']
        assert result['dataset_sha256'] == saved['dataset_sha256']
        assert result['corpus_sha256'] == saved['corpus_sha256']
        assert [(r['id'], r['hits'], r['quote_recall']) for r in result['results']] == [
                (r['id'], r['hits'], r['quote_recall']) for r in saved['results']]
