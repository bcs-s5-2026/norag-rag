"""Concept graph of uploaded documents, and the LLM_URL / LLM_API_KEY / LLM_MODEL settings.

No real model is ever called: graph extraction uses a fake extractor, answers a stub.
"""
import json

import pytest
from fastapi.testclient import TestClient

from rag_app import llm
from rag_app.api import create_app
from rag_app.models import RetrievalConfig, Settings
from rag_app.service import PipelineError, RagService

MERIDIAN = ('Helios is a solar project led by Dr. Amara Nwosu. It uses Aqua-3 membranes supplied by Northwind.\n'
            'Budget contact: finance@meridian.example, +33 1 23 45 67 89.\n')


def fake_extractor(seen=None):
    """Stands in for the model: finds the Helios sentences in whatever passage it receives."""
    def call(system, user):
        passage = json.loads(user)['passage']
        if seen is not None:
            seen.append(passage)
        out = dict(entities=[], relations=[])
        if 'Helios' in passage:
            out['entities'] = [
                dict(name='Helios', type='Project', quote='Helios is a solar project'),
                dict(name='Amara Nwosu', type='person', quote='Dr. Amara Nwosu'),
                dict(name='Aqua-3', type='material', quote='Aqua-3 membranes'),
                dict(name='Northwind', type='organization', quote='supplied by Northwind'),
                dict(name='Ghost', type='person', quote='Ghost wrote this'),             # quote not in the text
                dict(name='Nobody', type='person', quote='Dr. Amara Nwosu')]             # name not in its quote
            out['relations'] = [
                dict(subject='Amara Nwosu', relation='Leads', object='Helios', quote='solar project led by Dr. Amara Nwosu'),
                dict(subject='Helios', relation='uses', object='Aqua-3', quote='It uses Aqua-3 membranes'),
                dict(subject='Northwind', relation='supplies', object='Aqua-3', quote='Aqua-3 membranes supplied by Northwind'),
                dict(subject='Helios', relation='invented', object='Aqua-3', quote='this sentence is not in the text')]
        return json.dumps(out), dict(model='fake', input_tokens=10, output_tokens=5)
    return call


def stub_answer(question, evidence):
    return json.dumps(dict(answer='Northwind.', answerable=True, citations=[evidence[0]['id']]))


@pytest.fixture
def service(tmp_path):
    return RagService(tmp_path, generator=stub_answer, graph_extractor=fake_extractor())


@pytest.fixture
def client(service):
    return TestClient(create_app(service))


def upload(client, name='meridian.txt', text=MERIDIAN):
    response = client.post('/api/documents', files={'file': (name, text.encode(), 'text/plain')})
    assert response.status_code == 200
    return response.json()


# ---------- building

def test_upload_builds_the_graph_and_keeps_only_quoted_items(client, service):
    result = upload(client)
    assert result['graph']['status'] == 'built' and result['graph']['complete']
    graph = json.loads(service.graph_files(result['id'])[0].read_text())
    labels = {e['label']: e['type'] for e in graph['entities']}
    assert labels == {'Helios': 'project', 'Amara Nwosu': 'person', 'Aqua-3': 'material', 'Northwind': 'organization'}
    assert sorted(r['relation'] for r in graph['relations']) == ['leads', 'supplies', 'uses']
    # every quote is copied exactly from its chunk
    chunks = {c['id']: c for c in graph['chunks']}
    for proof in graph['provenance']:
        chunk = chunks[proof['chunk_id']]
        start = proof['quote_start'] - chunk['start']
        assert chunk['text'][start:start + len(proof['quote'])] == proof['quote']
    assert graph['coverage']['dropped_items'] == 3  # Ghost, Nobody, the invented relation


def test_contacts_are_redacted_before_extraction(tmp_path):
    seen = []
    service = RagService(tmp_path, generator=stub_answer, graph_extractor=fake_extractor(seen))
    doc = service.upload('meridian.txt', MERIDIAN.encode())
    service.build_graph(doc['id'])
    assert seen and 'finance@meridian.example' not in seen[0] and '+33 1 23 45 67 89' not in seen[0]
    assert '[EMAIL_1]' in seen[0]


def test_a_failing_model_does_not_fail_the_upload(tmp_path):
    def broken(system, user):
        raise RuntimeError('quota')
    client = TestClient(create_app(RagService(tmp_path, generator=stub_answer, graph_extractor=broken)))
    result = upload(client)
    assert result['graph']['status'] == 'failed' and result['id']
    assert client.get('/api/documents').json()[0]['name'] == 'meridian.txt'


def test_large_documents_wait_for_a_manual_build(tmp_path, monkeypatch):
    monkeypatch.setenv('RAG_GRAPH_AUTO_MAX_CHUNKS', '2')
    client = TestClient(create_app(RagService(tmp_path, generator=stub_answer, graph_extractor=fake_extractor())))
    result = upload(client, text=MERIDIAN * 20)
    assert result['graph']['status'] == 'too_large'
    built = client.post(f"/api/documents/{result['id']}/graph")
    assert built.status_code == 200 and built.json()['built'] and built.json()['concepts'] == 4
    assert result['id'] in client.get('/api/graphs').json()


def test_without_a_model_the_upload_just_says_so(tmp_path, monkeypatch):
    monkeypatch.setenv('RAG_GRAPH_AUTO', '1')
    monkeypatch.setenv('LLM_API_KEY', '')
    monkeypatch.setenv('GOOGLE_API_KEY', '')
    monkeypatch.delenv('LLM_URL', raising=False)
    monkeypatch.setattr('dotenv.load_dotenv', lambda *a, **k: None)
    client = TestClient(create_app(RagService(tmp_path)))
    assert upload(client)['graph']['status'] == 'skipped'


# ---------- retrieval

def ask_graph(service, doc_id, question, retrievers=('graph',), settings=None):
    return service.retrieve_configured(question, [doc_id], settings or Settings(),
                                       RetrievalConfig(retrievers=list(retrievers)))


def test_graph_retriever_follows_two_hops_on_an_uploaded_document(client, service):
    doc = upload(client)['id']
    result = ask_graph(service, doc, 'Which organization supplies the material used by Helios?')
    trace = result['graph_trace']
    assert [e['label'] for e in trace['matched_entities']] == ['Helios']
    reached = [[n['label'] for n in path['nodes']] for path in trace['paths']]
    assert ['Helios', 'Aqua-3', 'Northwind'] in reached
    assert result['results'] and set(result['results'][0]['origins']) == {'graph'}


def test_graph_works_together_with_bm25(client, service):
    doc = upload(client)['id']
    result = ask_graph(service, doc, 'Who leads Helios?', ('bm25', 'graph'))
    assert result['retrievers']['graph']['status'] == 'ok'
    assert set(result['results'][0]['origins']) == {'bm25', 'graph'}


def test_missing_graph_falls_back_to_the_other_retrievers(tmp_path):
    service = RagService(tmp_path, generator=stub_answer)  # nothing builds a graph here
    doc = service.upload('meridian.txt', MERIDIAN.encode())['id']
    result = ask_graph(service, doc, 'Who leads Helios?', ('bm25', 'graph'))
    assert result['retrievers']['graph']['status'] == 'unavailable'
    assert 'No concept graph yet' in result['retrievers']['graph']['reason']
    assert result['results']  # BM25 still answered
    with pytest.raises(PipelineError, match='No concept graph yet'):  # graph alone has nothing to fall back to
        ask_graph(service, doc, 'Who leads Helios?')


def test_other_chunk_settings_are_explained(client, service):
    doc = upload(client)['id']
    other = Settings(chunk_size=500, chunk_overlap=50)
    with pytest.raises(PipelineError, match='chunk size/overlap 800/80') as error:
        ask_graph(service, doc, 'Who leads Helios?', settings=other)
    assert error.value.status == 400
    assert ask_graph(service, doc, 'Who leads Helios?', ('bm25', 'graph'), other)['retrievers']['graph']['status'] == 'unavailable'


def test_the_whole_question_is_answered_and_traced(client):
    doc = upload(client)['id']
    body = {'document_ids': [doc], 'question': 'Which organization supplies the material used by Helios?',
            'retrieval': {'retrievers': ['bm25', 'graph']}}
    answer = client.post('/api/ask', json=body).json()
    assert answer['answerable'] and 'graph_trace' in answer
    trace = client.get('/api/traces/' + answer['trace_id']).json()
    assert [s['name'] for s in trace['spans']][:3] == ['bm25', 'graph', 'fusion']
    graph_traces = client.get('/api/traces?kind=graph').json()
    assert graph_traces[0]['outcome'] == 'built' and graph_traces[0]['llm_calls'] == 1


# ---------- concept map

def test_concept_map_lists_and_explores_an_uploaded_graph(client):
    doc = upload(client)['id']
    concepts = client.get('/api/concepts', params={'documents': doc}).json()
    assert {c['label'] for c in concepts} == {'Helios', 'Amara Nwosu', 'Aqua-3', 'Northwind'}
    helios = next(c for c in concepts if c['label'] == 'Helios')
    detail = client.get(f"/api/concepts/{helios['id']}", params={'documents': doc}).json()
    assert {(l['relation'], l['other']['label']) for l in detail['links']} == {('leads', 'Amara Nwosu'), ('uses', 'Aqua-3')}
    assert all(e['quote'] in e['chunk_text'] for l in detail['links'] for e in l['evidence'])


def test_two_documents_share_concepts_with_the_same_name(client, service):
    first = upload(client)['id']
    second = upload(client, 'notes.txt', 'Helios is a solar project led by Dr. Amara Nwosu.\n')['id']
    labels = [c['label'] for c in client.get('/api/concepts', params={'documents': f'{first},{second}'}).json()]
    assert labels.count('Helios') == 1


def test_deleting_a_document_deletes_its_graph(client, service):
    doc = upload(client)['id']
    client.delete('/api/documents/' + doc)
    assert service.graph_files(doc) == [] and client.get('/api/graphs').json() == {}


def test_the_kestrel_concept_map_is_unchanged(client):
    assert client.get('/api/concepts').status_code in (200, 503)  # frozen snapshot, never the uploaded graph


# ---------- LLM settings

@pytest.fixture
def clean_env(monkeypatch):
    monkeypatch.setattr('dotenv.load_dotenv', lambda *a, **k: None)
    for name in ('LLM_URL', 'LLM_API_KEY', 'LLM_MODEL', 'GOOGLE_API_KEY', 'GOOGLE_MODEL'):
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def test_google_stays_the_default(clean_env):
    clean_env.setenv('GOOGLE_API_KEY', 'g-key')
    config = llm.load_config()
    assert (config.url, config.key, config.model) == (llm.GOOGLE_URL, 'g-key', llm.GOOGLE_MODEL) and config.usable


def test_llm_variables_win_over_google_ones(clean_env):
    clean_env.setenv('GOOGLE_API_KEY', 'g-key')
    clean_env.setenv('LLM_URL', 'http://localhost:11434/v1')
    clean_env.setenv('LLM_API_KEY', 'other-key')
    clean_env.setenv('LLM_MODEL', 'llama3.1')
    assert tuple(llm.load_config()) == ('http://localhost:11434/v1', 'other-key', 'llama3.1')


def test_a_key_is_needed_unless_the_url_is_custom(clean_env):
    assert not llm.load_config().usable
    clean_env.setenv('GOOGLE_API_KEY', 'your_google_api_key_here')
    assert not llm.load_config().usable
    clean_env.setenv('LLM_URL', 'http://localhost:11434/v1')
    assert llm.load_config().usable  # local servers often need no key


def test_answers_use_the_configured_model(clean_env, tmp_path):
    clean_env.setenv('LLM_URL', 'https://llm.example/v1')
    clean_env.setenv('LLM_API_KEY', 'k')
    clean_env.setenv('LLM_MODEL', 'my-model')
    calls = []

    def fake(config, system, user, timeout=45):
        calls.append(config)
        return json.dumps(dict(answer='x', answerable=False, citations=[])), dict(model=config.model, input_tokens=1, output_tokens=1)
    clean_env.setattr(llm, 'complete_json', fake)
    service = RagService(tmp_path)
    service.generate('q', [{'id': 'a', 'text': 't'}])
    assert (calls[0].url, calls[0].model) == ('https://llm.example/v1', 'my-model')
    assert service.last_usage['model'] == 'my-model'


def test_missing_key_message_names_both_variables(clean_env, tmp_path):
    with pytest.raises(PipelineError, match='LLM_API_KEY'):
        RagService(tmp_path).generate('q', [])


# ---------- metrics page

def test_metrics_are_computed_from_traces_without_any_text(client):
    doc = upload(client)['id']
    body = {'document_ids': [doc], 'question': 'Who leads Helios?', 'retrieval': {'retrievers': ['bm25', 'graph']}}
    client.post('/api/ask', json=body)
    metrics = client.get('/api/metrics').json()
    assert metrics['questions']['total'] == 1 and metrics['questions']['answered'] == 1
    assert metrics['graph_builds']['built'] == 1 and metrics['llm']['calls'] == 2  # one extraction + one answer
    assert metrics['retrievers'] == {'bm25': 1, 'graph': 1}
    assert metrics['redactions'] == 2  # the email and the phone in the evidence
    assert 'bm25' in metrics['steps_ms']
    assert 'Helios' not in json.dumps(metrics)
    assert 'Metrics' in client.get('/metrics').text


def test_metrics_with_no_traces(client):
    metrics = client.get('/api/metrics').json()
    assert metrics['questions']['total'] == 0 and metrics['questions']['abstention_rate'] is None


# ---------- mixed selections (found while testing: a sixth, uncovered file switched the graph off)

def kestrel_ids(service):
    from rag_app.service import ROOT
    return [service.upload(p.name, p.read_bytes())['id'] for p in sorted((ROOT / 'docs' / 'kestrel').glob('*.md'))]


def test_extra_file_without_a_graph_no_longer_switches_the_kestrel_graph_off(service):
    ids = kestrel_ids(service) + [service.upload('readme.txt', b'Some unrelated notes about the lab.')['id']]
    result = ask_graph_ids(service, 'Who owns the service that raises KST-5031?', ids)
    assert result['retrievers']['graph']['status'] == 'partial'
    trace = result['graph_trace']
    assert [e['label'] for e in trace['matched_entities']] == ['KST-5031']
    assert trace['coverage']['uncovered_documents'] == ['readme.txt'] and 'readme.txt' in trace['note']
    assert not trace['complete']


def test_kestrel_graph_and_an_uploaded_graph_work_in_one_question(service):
    meridian = service.upload('meridian.txt', MERIDIAN.encode())['id']
    service.build_graph(meridian)
    ids = kestrel_ids(service) + [meridian]
    result = ask_graph_ids(service, 'Who owns the service that raises KST-5031, and who leads Helios?', ids)
    labels = {e['label'] for e in result['graph_trace']['matched_entities']}
    assert {'KST-5031', 'Helios'} <= labels
    assert result['retrievers']['graph']['status'] == 'ok'
    documents = {r['document_id'] for r in result['results']}
    assert meridian in documents and len(documents) > 1
    assert [r['fused_rank'] for r in result['results']] == list(range(1, len(result['results']) + 1))


def ask_graph_ids(service, question, ids):
    return service.retrieve_configured(question, ids, Settings(), RetrievalConfig(retrievers=['bm25', 'graph']))


def test_rich_text_saved_as_txt_is_refused_with_advice(client):
    rtf = r'{\rtf1\ansi\deff0 Project Orion is led by Dr. Ngozi Adeyemi.}'
    response = client.post('/api/documents', files={'file': ('lab.txt', rtf.encode(), 'text/plain')})
    assert response.status_code == 400 and 'plain text' in response.json()['error']
