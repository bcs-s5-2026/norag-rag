import json
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from rag_app.api import create_app
from rag_app.models import Settings
from rag_app.service import PipelineError, RagService, chunks


@pytest.fixture
def service(tmp_path):
    # Real local embedding model and real Chroma, only hosted generation is stubbed.
    return RagService(tmp_path, generator=lambda q, es: json.dumps({
        'answer': 'The tank holds 1.8 litres.', 'answerable': True, 'citations': [es[0]['id']]}))


@pytest.fixture
def client(service):
    return TestClient(create_app(service))


def upload(client, name='manual.txt', text='The water tank holds 1.8 litres. ' * 12):
    response = client.post('/api/documents', files={'file': (name, text.encode(), 'text/plain')})
    assert response.status_code == 200
    return response.json()['id']


def test_complete_workflow(client, service):
    doc = upload(client)
    assert len(client.get('/api/documents').json()) == 1
    body = {'document_ids': [doc], 'settings': Settings().model_dump()}
    first = client.post('/api/index', json=body).json()
    assert first['chunks'] > 0
    assert client.post('/api/index', json=body).json() == first
    response = client.post('/api/ask', json=dict(**body, question='How much water does the tank hold?'))
    assert response.status_code == 200, response.text
    result = response.json()
    assert result['answerable']
    assert result['references'][0]['id'] in [e['id'] for e in result['retrieved']]
    assert '1.8 litres' in result['references'][0]['text']
    stored = service.collection(Settings()).get(include=['embeddings'])
    assert len(stored['embeddings'][0]) == 384
    assert client.delete('/api/documents/' + doc).status_code == 200
    assert service.collection(Settings()).count() == 0
    assert client.post('/api/ask', json=dict(**body, question='Tank size?')).status_code == 404


def test_selection_settings_and_deletion(service):
    a = service.upload('a.md', b'Alpha is the selected document. ' * 50)['id']
    b = service.upload('b.txt', b'Beta is excluded from this question. ' * 50)['id']
    default = Settings()
    service.index([a,b], default)
    es = service.retrieve('Beta document', [a], Settings(top_k=1))
    assert len(es) == 1 and es[0]['document_id'] == a
    assert service.collection_name(default) == service.collection_name(Settings(top_k=2))
    other = Settings(chunk_size=300, chunk_overlap=30)
    assert service.collection_name(default) != service.collection_name(other)
    assert service.index([a], other)['chunks'] > service.index([a], default)['chunks']
    service.delete(a)
    assert service.collection(other).count() == 0
    assert {m['document_id'] for m in service.collection(default).get()['metadatas']} == {b}


def test_chunk_offsets():
    text = '0123456789' * 26
    rows = list(chunks(text, Settings(chunk_size=100, chunk_overlap=20)))
    assert [s for s,e,t in rows] == [0,80,160]
    assert all(text[s:e] == t for s,e,t in rows)
    assert rows[-1][1] == len(text)


@pytest.mark.parametrize('name,content', [('bad.pdf', b'Hello'), ('empty.txt', b'  '), ('bad.md', b'\xff'), ('../escape.txt', b'text'), ('null.txt', b'\x00')])
def test_bad_uploads(client, name, content):
    assert client.post('/api/documents', files={'file': (name,content)}).status_code == 400


def test_size_limit(client):
    assert client.post('/api/documents', files={'file': ('big.txt', b'x'*(5*1024*1024+1))}).status_code == 413


def test_duplicate_content(client):
    first = upload(client)
    assert upload(client, name='copy.md') == first
    assert len(client.get('/api/documents').json()) == 1


@pytest.mark.parametrize('settings', [{'chunk_size': 0}, {'chunk_overlap': 800}, {'top_k': 0}, {'top_k': 21}, {'chunk_size': 800.5}])
def test_invalid_settings(client, settings):
    assert client.post('/api/index', json={'document_ids':['x'], 'settings':settings}).status_code == 422


@pytest.mark.parametrize('body', [{'document_ids':[], 'question':'hello'}, {'document_ids':['x'], 'question':' '}, {'document_ids':['x'], 'question':''}])
def test_bad_questions(client, body):
    assert client.post('/api/ask', json=body).status_code == 422


@pytest.mark.parametrize('raw', ['not json', '{}', '{"answer":"x","answerable":true,"citations":["fake"]}', '{"answer":"x","answerable":true,"citations":[]}', '{"answer":"x","answerable":"yes","citations":[]}'])
def test_invalid_llm_output(client, service, raw):
    doc = upload(client)
    service.generator = lambda q,e: raw
    response = client.post('/api/ask', json={'document_ids':[doc], 'question':'Tank size?'})
    assert response.status_code == 502
    assert 'No answer was accepted' in response.json()['error']


def test_abstention(client, service):
    doc = upload(client)
    service.generator = lambda q,e: '{"answer":"Invented content", "answerable":false,"citations":[]}'
    result = client.post('/api/ask',json={'document_ids':[doc],'question':'Price?'}).json()
    assert result['answerable'] is False
    assert result['references'] == []
    assert 'Invented' not in result['answer']


def test_missing_credentials(service, monkeypatch):
    service.generator = None
    monkeypatch.setenv('GOOGLE_API_KEY', '')
    with pytest.raises(PipelineError, match='GOOGLE_API_KEY'):
        service.generate('hello', [])


def test_database_failure(client, service, monkeypatch):
    doc = upload(client)
    monkeypatch.setattr(service, 'client', Mock(side_effect=RuntimeError('private backend details')))
    response = client.post('/api/index',json={'document_ids':[doc]})
    assert response.status_code == 503
    assert 'private backend details' not in response.text


def test_embedding_failure(client, service, monkeypatch):
    doc = upload(client)
    monkeypatch.setattr(service, 'embedding', Mock(side_effect=RuntimeError('embedding unavailable')))
    assert client.post('/api/index',json={'document_ids':[doc]}).status_code == 503


def test_llm_api_error(service, monkeypatch):
    import openai
    service.generator = None
    monkeypatch.setenv('GOOGLE_API_KEY', 'test-only')
    monkeypatch.setattr(openai, 'OpenAI', Mock(side_effect=RuntimeError('secret provider detail')))
    with pytest.raises(PipelineError, match='LLM unavailable'):
        service.generate('question', [])


def test_baseline_dataset_and_metric(service):
    from evaluation.run import evaluate
    from rag_app.service import ROOT
    dataset=json.loads((ROOT/'evaluation/questions.json').read_text())
    result = evaluate(service, Settings(), dataset)
    assert result['answerable_count'] == 12
    assert result['unanswerable_count'] == 3
    assert 0 <= result['hit_at_k'] <= 1
    assert result['hits'] == sum(r['hit'] is True for r in result['results'])


def test_frontend_and_evaluation(client):
    assert 'Ask with evidence.' in client.get('/').text
    assert client.get('/app.js').status_code == 200
    assert client.get('/api/evaluation').status_code == 200
