"""BM25 contract/lifecycle tests: no model downloads, embeddings or hosted APIs."""
import json
import math
from html.parser import HTMLParser
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from rag_app.api import create_app
from rag_app.bm25 import BM25Index
from rag_app.lexical import tokens
from rag_app.models import Settings
from rag_app.service import ROOT, PipelineError, RagService, chunks


def row(identifier, text):
    return dict(id=identifier, text=text)


def lexical_service(directory):
    service = RagService(directory)
    # Fail immediately if lexical paths touch either dense or hosted generation.
    service.client = Mock(side_effect=AssertionError('BM25 touched Chroma'))
    service.embedding = Mock(side_effect=AssertionError('BM25 touched embeddings'))
    service.generate = Mock(side_effect=AssertionError('BM25 touched the LLM'))
    return service


def test_tokenization_and_known_scores():
    assert tokens("KST-2044 connector-hub #oncall-payments CAFÉ isn't l’eau 20%") == [
        'kst-2044', 'connector-hub', 'oncall-payments', 'café', "isn't", 'l’eau', '20']
    index = BM25Index([row('b', 'apple pear'), row('a', 'apple apple')])
    results = index.search('apple', 10)
    idf = math.log1p(0.5/2.5)
    assert [r['id'] for r in results] == ['a', 'b']
    assert results[0]['score'] == pytest.approx(idf*2*2.5/3.5)
    assert results[1]['score'] == pytest.approx(idf)
    assert [r['rank'] for r in results] == [1, 2]
    assert index.search('apple apple APPLE', 10) == results
    assert index.search('apple', 1) == results[:1]


def test_length_normalization_and_stable_ties():
    a, b = row('a', 'needle filler'), row('b', 'needle filler')
    first = BM25Index([b, a]).search('needle', 9)
    assert [r['id'] for r in first] == ['a', 'b']
    assert first == BM25Index([a, b]).search('needle', 9)
    assert BM25Index([row('a', 'needle filler filler'), row('b', 'needle')]).search('needle', 2)[0]['id'] == 'b'
    with pytest.raises(ValueError, match='Duplicate'):
        BM25Index([a, a])


@pytest.mark.parametrize('rows,question', [([], 'needle'), ([row('a', '!!!')], 'needle'),
                                         ([row('a', 'needle')], 'unknown'),
                                         ([row('a', 'needle')], '!!!')])
def test_empty_and_no_match(rows, question):
    assert BM25Index(rows).search(question, 5) == []


@pytest.mark.parametrize('k', [0, -1, 1.5, True])
def test_invalid_top_k(k):
    with pytest.raises(ValueError):
        BM25Index([]).search('needle', k)


def test_canonical_ids_and_offsets_without_dense(tmp_path):
    service = lexical_service(tmp_path)
    text = '# Short\n\n' + 'KST-2044 needle café. '*30
    doc = service.upload('manual.md', text.encode())['id']
    settings = Settings(chunk_size=100, chunk_overlap=20, top_k=20)
    info = service.index_bm25([doc, doc], settings)
    expected = list(chunks(text, settings))
    assert info['chunks'] == len(expected) and info['documents'] == 1
    results = service.retrieve_bm25('needle', [doc], settings)
    for result in results:
        assert result['id'] == f"{doc}:{result['start']}:{result['end']}"
        assert result['text'] == text[result['start']:result['end']]
        assert result['line'] == text.count('\n', 0, result['start'])+1
        assert result['retriever'] == 'bm25' and 'similarity' not in result
    snapshot = json.loads(next((tmp_path/'bm25').glob('*.json')).read_text())
    assert snapshot['payload']['rows'][0]['text'].startswith('# Short')
    assert not (tmp_path/'chroma').exists()


def test_restart_loads_counts_without_rebuilding_or_tokenizing(tmp_path, monkeypatch):
    service = lexical_service(tmp_path)
    doc = service.upload('a.md', b'needle apple')['id']
    settings = Settings()
    first = service.index_bm25([doc], settings)
    path = tmp_path/'bm25'/f"{first['index']}.json"
    original = path.read_bytes()
    modified = path.stat().st_mtime_ns
    restarted = lexical_service(tmp_path)
    # Index loading must use persisted term counts, not tokenize source again.
    monkeypatch.setattr('rag_app.bm25.tokens', Mock(side_effect=AssertionError('Retokenized source')))
    assert restarted.index_bm25([doc], settings) == {**first, 'rebuilt': False}
    assert path.read_bytes() == original and path.stat().st_mtime_ns == modified


def test_selection_updates_rebuild_and_delete(tmp_path):
    service = lexical_service(tmp_path)
    a = service.upload('a.md', b'needle alpha')['id']
    b = service.upload('b.md', b'needle beta')['id']
    settings = Settings()
    first = service.index_bm25([a, b], settings)
    assert service.index_bm25([b, a, a], Settings(top_k=1))['index'] == first['index']
    assert service.index_bm25([a, b], settings)['rebuilt'] is False
    assert service.index_bm25([a, b], settings, rebuild=True)['rebuilt'] is True
    assert service.index_bm25([a], settings)['index'] != first['index']
    assert {r['document_id'] for r in service.retrieve_bm25('needle', [a], settings)} == {a}
    assert service.index_bm25([a], Settings(chunk_size=100, chunk_overlap=20))['index'] != first['index']
    c = service.upload('a.md', b'needle revised')['id']
    assert c != a
    assert service.index_bm25([c], settings)['index'] != first['index']
    service.delete(a)
    assert not list((tmp_path/'bm25').glob('*.json'))
    with pytest.raises(PipelineError) as exc:
        service.retrieve_bm25('needle', [a], settings)
    assert exc.value.status == 404
    assert {r['document_id'] for r in service.retrieve_bm25('needle', [b, c], settings)} == {b, c}


@pytest.mark.parametrize('damage', ['truncated', 'checksum', 'schema'])
def test_corrupt_snapshot_rebuilds(tmp_path, damage):
    service = lexical_service(tmp_path)
    doc = service.upload('a.md', b'needle')['id']
    info = service.index_bm25([doc], Settings())
    path = tmp_path/'bm25'/f"{info['index']}.json"
    saved = json.loads(path.read_text())
    if damage == 'checksum':
        saved['payload']['counts'][f'{doc}:0:6']['needle'] = 100
    elif damage == 'schema':
        saved = []
    path.write_text('{' if damage == 'truncated' else json.dumps(saved))
    assert service.index_bm25([doc], Settings())['rebuilt'] is True
    assert service.retrieve_bm25('needle', [doc], Settings())[0]['score'] == pytest.approx(math.log(4/3))
    assert not list((tmp_path/'bm25').glob('*.tmp'))


def test_version_invalidates_snapshot(tmp_path, monkeypatch):
    service = lexical_service(tmp_path)
    doc = service.upload('a.md', b'needle')['id']
    first = service.index_bm25([doc], Settings())
    monkeypatch.setattr('rag_app.bm25.TOKENIZER_VERSION', 'new-tokenizer')
    assert service.index_bm25([doc], Settings())['index'] != first['index']


def test_atomic_write_failure_preserves_previous_snapshot(tmp_path, monkeypatch):
    service = lexical_service(tmp_path)
    doc = service.upload('a.md', b'needle')['id']
    first = service.index_bm25([doc], Settings())
    path = tmp_path/'bm25'/f"{first['index']}.json"
    original = path.read_bytes()
    monkeypatch.setattr('rag_app.bm25.os.replace', Mock(side_effect=OSError('private disk detail')))
    with pytest.raises(PipelineError, match='BM25 index unavailable'):
        service.index_bm25([doc], Settings(), rebuild=True)
    assert path.read_bytes() == original
    assert not list((tmp_path/'bm25').glob('*.tmp'))


def test_both_corpora_and_api_isolation(tmp_path):
    service = lexical_service(tmp_path)
    client = TestClient(create_app(service))
    corpus_ids = {}
    for corpus, term in [('kestrel', 'KST-2044'), ('vellora', 'E47')]:
        response = client.post('/api/corpora/'+corpus)
        assert response.status_code == 200
        ids = [d['id'] for d in response.json()]
        corpus_ids[corpus] = set(ids)
        body = dict(document_ids=ids, settings={'top_k': 10})
        built = client.post('/api/bm25/index', json=body)
        assert built.status_code == 200 and built.json()['chunks'] == 43
        results = client.post('/api/bm25/search', json={**body, 'question': term}).json()
        assert results and all(term.casefold() in tokens(r['text']) for r in results)
        assert all(r['document_id'] in ids for r in results)
        assert client.post('/api/bm25/index?rebuild=true', json=body).json()['rebuilt'] is True
    # Both corpora are now in one library; selection still bounds ranking and IDF.
    body = dict(document_ids=sorted(corpus_ids['kestrel']), question='E47')
    assert client.post('/api/bm25/search', json=body).json() == []
    assert client.post('/api/bm25/search', json={**body, 'document_ids': []}).status_code == 422
    assert client.post('/api/bm25/search', json={**body, 'question': ' '}).status_code == 422
    assert client.post('/api/bm25/search', json={**body, 'settings': {'top_k': 0}}).status_code == 422
    assert client.post('/api/bm25/search', json={**body, 'document_ids': ['../x']}).status_code == 404


def test_route_and_absence_of_frontend_references(tmp_path):
    client = TestClient(create_app(lexical_service(tmp_path)))
    response = client.get('/bm25')
    assert response.status_code == 200 and response.headers['content-type'].startswith('text/html')
    class Text(HTMLParser):
        def __init__(self):
            super().__init__()
            self.paragraph = False
            self.text = ''
            self.style = ''
        def handle_starttag(self, tag, attrs):
            if tag == 'p':
                self.paragraph = True
                self.style = dict(attrs).get('style', '')
        def handle_endtag(self, tag):
            if tag == 'p': self.paragraph = False
        def handle_data(self, data):
            if self.paragraph: self.text += data
    parsed = Text()
    parsed.feed(response.text)
    assert parsed.text == 'Watch your sources!'
    assert 'font-size:3rem' in parsed.style
    for path in (ROOT/'rag_app/static').rglob('*'):
        if path.is_file():
            assert '/bm25' not in path.read_text() and 'Watch your sources!' not in path.read_text()
    assert '/bm25' not in client.get('/').text
    assert '/bm25' not in client.get('/about').text
    assert '/bm25' not in client.get('/openapi.json').json()['paths']


def test_restart_ranking_and_selection_statistics(tmp_path):
    service = lexical_service(tmp_path)
    a = service.upload('a.md', b'needle needle short')['id']
    b = service.upload('b.md', b'needle long filler filler filler')['id']
    settings = Settings()
    expected = service.retrieve_bm25('needle', [a, b], settings)
    # Unselected uploads must not affect corpus statistics or scores.
    service.upload('excluded.md', b'needle '*200)
    assert service.retrieve_bm25('needle', [b, a], settings) == expected
    assert lexical_service(tmp_path).retrieve_bm25('needle', [a, b], settings) == expected


def test_dense_chunk_compatibility_and_joint_deletion(tmp_path):
    service = RagService(tmp_path)
    a = service.upload('a.md', ('KST-2044 needle. '*40).encode())['id']
    b = service.upload('b.md', ('Other needle. '*40).encode())['id']
    settings = Settings(chunk_size=100, chunk_overlap=20)
    service.index([a, b], settings)
    service.index_bm25([a, b], settings)
    collection = service.collection(settings)
    stored = collection.get(include=['documents', 'metadatas'])
    dense = {ref: (text, meta) for ref, text, meta in
             zip(stored['ids'], stored['documents'], stored['metadatas'])}
    lexical = json.loads(next((tmp_path/'bm25').glob('*.json')).read_text())['payload']['rows']
    assert {r['id'] for r in lexical} == set(dense)
    for r in lexical:
        text, meta = dense[r['id']]
        assert r['text'] == text
        assert all(r[key] == value for key, value in meta.items())
    service.delete(a)
    assert not list((tmp_path/'bm25').glob('*.json'))
    assert {m['document_id'] for m in collection.get()['metadatas']} == {b}
    assert {r['document_id'] for r in service.retrieve_bm25('needle', [b], settings)} == {b}
