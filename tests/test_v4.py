"""V4: traces (Part A), concept map explorer (Part B), personal data redaction (Part C)."""
import json
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from rag_app.api import create_app
from rag_app.models import Settings
from rag_app.redaction import Redactor
from rag_app.service import ROOT, RagService
from rag_app.tracing import Trace, TraceStore, llm_cost

TEXT = 'The water tank holds 1.8 litres. ' * 12
KESTREL = sorted((ROOT / 'docs' / 'kestrel').glob('*.md'))


def answer_first(question, evidence):
    return json.dumps({'answer': 'The tank holds 1.8 litres.', 'answerable': True,
                       'citations': [evidence[0]['id']]})


@pytest.fixture
def service(tmp_path):
    # Real local embeddings, Chroma and BM25; only the hosted LLM is stubbed.
    return RagService(tmp_path, generator=answer_first)


@pytest.fixture
def client(service):
    return TestClient(create_app(service))


def upload(client, name='manual.txt', text=TEXT):
    return client.post('/api/documents', files={'file': (name, text.encode(), 'text/plain')}).json()['id']


def ask(client, doc, question='How much water does the tank hold?', retrievers=('dense', 'bm25')):
    return client.post('/api/ask', json={'document_ids': [doc], 'question': question,
                                         'retrieval': {'retrievers': list(retrievers)}})


# ---------- Part A: traces

def test_question_trace_has_one_span_per_step(client):
    doc = upload(client)
    result = ask(client, doc).json()
    trace = client.get('/api/traces/' + result['trace_id']).json()
    assert trace['kind'] == 'question' and trace['outcome'] == 'answered'
    assert [s['name'] for s in trace['spans']] == ['dense', 'bm25', 'fusion', 'redact', 'generate', 'validate']
    assert all(s['status'] == 'ok' and s['duration_ms'] >= 0 for s in trace['spans'])
    spans = {s['name']: s['attributes'] for s in trace['spans']}
    # The trace points to the same chunks as the answer, by id.
    assert [r['chunk_id'] for r in spans['fusion']['results']] == [e['id'] for e in result['retrieved']]
    assert spans['validate']['cited_chunk_ids'] == result['citations']
    assert trace['llm_calls'] == 1
    # Chunk ids are enough: no document text and no answer text in the trace.
    stored = json.dumps(trace)
    assert 'water tank holds' not in stored and 'The tank holds' not in stored


def test_legacy_ask_without_retrieval_is_traced(client):
    doc = upload(client)
    result = client.post('/api/ask', json={'document_ids': [doc], 'question': 'Tank size?'}).json()
    trace = client.get('/api/traces/' + result['trace_id']).json()
    assert [s['name'] for s in trace['spans']] == ['dense', 'redact', 'generate', 'validate']


def test_invalid_llm_output_trace_is_reachable_from_the_error(client, service):
    service.generator = lambda question, evidence: 'not json'
    response = ask(client, upload(client))
    assert response.status_code == 502
    trace = client.get('/api/traces/' + response.json()['trace_id']).json()
    assert trace['outcome'] == 'invalid' and 'invalid structured output' in trace['error']
    assert trace['spans'][-1]['name'] == 'validate' and trace['spans'][-1]['status'] == 'error'


def test_abstention_and_pipeline_error_outcomes(client, service):
    doc = upload(client)
    service.generator = lambda question, evidence: json.dumps(
        {'answer': 'I do not know.', 'answerable': False, 'citations': []})
    trace_id = ask(client, doc).json()['trace_id']
    assert service.traces.get(trace_id)['outcome'] == 'abstained'

    def unavailable(question, evidence):
        raise RuntimeError('network down')
    service.generator = unavailable
    with pytest.raises(RuntimeError):
        service.ask_configured('Tank size?', [doc], Settings(), None)
    last = service.traces.recent(1, 'question')[0]
    assert last['outcome'] == 'error'


def test_tokens_and_cost_are_recorded_on_the_generate_span(client, service):
    def with_usage(question, evidence):
        service.last_usage = dict(model='gemini-3.5-flash-lite', input_tokens=1000, output_tokens=100)
        return answer_first(question, evidence)
    service.generator = with_usage
    trace = service.traces.get(ask(client, upload(client)).json()['trace_id'])
    assert (trace['input_tokens'], trace['output_tokens']) == (1000, 100)
    assert trace['cost_usd'] == pytest.approx((1000 * 0.30 + 100 * 2.50) / 1e6)
    assert llm_cost('unknown-model', 10, 10) is None


def test_indexing_run_trace(client, service):
    doc = upload(client)
    body = {'document_ids': [doc]}
    assert client.post('/api/index', json=body).status_code == 200
    first = client.get('/api/traces?kind=indexing&limit=1').json()[0]
    spans = client.get('/api/traces/' + first['id']).json()['spans']
    assert [s['name'] for s in spans] == ['embed_document', 'bm25_index']
    assert spans[0]['attributes']['document_id'] == doc and spans[0]['attributes']['chunks'] > 0
    assert first['outcome'] == 'indexed' and first['attributes']['newly_embedded'] == 1
    assert first['llm_calls'] == 0
    # A second run has nothing to embed, and still leaves a trace saying so.
    client.post('/api/index', json=body)
    second = client.get('/api/traces?kind=indexing&limit=1').json()[0]
    assert second['id'] != first['id'] and second['attributes']['newly_embedded'] == 0


def test_automatic_indexing_is_traced_once(client, service):
    doc = upload(client)
    ask(client, doc)
    ask(client, doc)
    indexing = service.traces.recent(10, 'indexing')
    assert len(indexing) == 1 and indexing[0]['attributes']['trigger'] == 'question'


def test_old_traces_are_pruned(tmp_path):
    store = TraceStore(tmp_path)
    old, new = Trace('question'), Trace('question')
    old.started_at = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()
    store.save(old)
    store.save(new)
    assert store.prune() == 1
    assert [t['id'] for t in store.all()] == [new.id]
    assert store.get(old.id) is None


def test_unknown_trace_is_404(client):
    assert client.get('/api/traces/' + '0' * 32).status_code == 404


# ---------- Part C: personal data redaction

def test_redactor_replaces_emails_and_phones():
    redactor = Redactor()
    text = 'Write to jane.doe@example.org or call +33 6 12 34 56 78 (or 06 12 34 56 78). jane.doe@example.org again.'
    safe = redactor.redact(text)
    assert safe == 'Write to [EMAIL_1] or call [PHONE_1] (or [PHONE_2]). [EMAIL_1] again.'
    assert redactor.counts() == dict(emails=1, phones=2)
    assert redactor.restore(safe) == text


def test_phone_at_the_end_of_a_sentence_is_fully_replaced():
    # Found in the live check: the old pattern left the last two digits ("[PHONE_1] 78.").
    assert Redactor().redact('My phone is +33 6 12 34 56 78. Thanks.') == 'My phone is [PHONE_1]. Thanks.'
    assert Redactor().redact('Call (555) 123-4567, please.') == 'Call [PHONE_1], please.'


@pytest.mark.parametrize('text', [
    'Allow the IP 203.0.113.10 and 203.0.113.11.', 'Effective 2026-01-01 until 2026-12-31.',
    'Error KST-5031 after 120 seconds.', 'It costs 1,200 EUR for 25 seats.', 'Order 12345678.',
    'The allowlist is 203.0.113.10.', 'Version 3.141592653589 of pi.'])
def test_redactor_leaves_other_numbers_alone(text):
    assert Redactor().redact(text) == text


def test_course_corpora_have_no_false_phone_matches():
    for path in KESTREL + [ROOT / 'docs' / 'vellora-duo-espresso-machine.txt']:
        redactor = Redactor()
        redactor.redact(path.read_text(encoding='utf-8'))
        assert redactor.counts()['phones'] == 0, path.name


def test_personal_data_never_reaches_the_llm_or_the_trace(tmp_path):
    sent = {}

    def capture(question, evidence):
        sent.update(question=question, evidence=evidence)
        # [EMAIL_1] is the address in the question, [EMAIL_2] the one in the document.
        return json.dumps({'answer': 'Write to [EMAIL_2].', 'answerable': True,
                           'citations': [evidence[0]['id']]})
    service = RagService(tmp_path, generator=capture)
    client = TestClient(create_app(service))
    doc = upload(client, text='For billing questions write to billing@kestrel.example. ' * 10)
    question = 'I am sam@student.example, phone +33 6 12 34 56 78. Who do I write to about billing?'
    result = ask(client, doc, question).json()
    payload = json.dumps(sent)
    for secret in ('billing@kestrel.example', 'sam@student.example', '+33 6 12 34 56 78'):
        assert secret not in payload
    assert '[EMAIL_1]' in sent['question'] and '[PHONE_1]' in sent['question']
    # The user still reads the real address, and the reference shows the real source text.
    assert result['answer'] == 'Write to billing@kestrel.example.'
    assert 'billing@kestrel.example' in result['references'][0]['text']
    stored = (tmp_path / 'traces' / 'traces.jsonl').read_text()
    for secret in ('billing@kestrel.example', 'sam@student.example', '+33 6 12 34 56 78'):
        assert secret not in stored
    trace = service.traces.get(result['trace_id'])
    redact = next(s for s in trace['spans'] if s['name'] == 'redact')
    assert redact['attributes'] == dict(emails=2, phones=1)


# ---------- Part B: concept map explorer

def test_concept_list_and_neighborhood(client):
    concepts = client.get('/api/concepts').json()
    assert len(concepts) == 42 and all(c['links'] > 0 for c in concepts)
    by_label = {c['label']: c for c in concepts}
    data = client.get('/api/concepts/' + by_label['Enterprise']['id']).json()
    assert data['concept']['type'] == 'Plan' and len(data['links']) == by_label['Enterprise']['links']
    trace = client.get('/api/traces/' + data['trace_id']).json()
    assert trace['kind'] == 'concept' and trace['outcome'] == 'found' and trace['llm_calls'] == 0
    assert [s['name'] for s in trace['spans']] == ['load_graph', 'neighborhood']
    assert trace['attributes']['label'] == 'Enterprise'


def test_every_link_and_mention_points_to_real_source_text(client):
    sources = {path.name: path.read_text(encoding='utf-8') for path in KESTREL}
    concepts = client.get('/api/concepts').json()
    links = 0
    for concept in concepts:
        data = client.get('/api/concepts/' + concept['id']).json()
        assert data['mentions'], concept['label']
        for proof in data['mentions'] + [e for link in data['links'] for e in link['evidence']]:
            # The quote is where the trace says it is, in the unchanged course document.
            assert sources[proof['document']][proof['quote_start']:proof['quote_end']] == proof['quote']
            assert proof['quote'] in proof['chunk_text']
        for link in data['links']:
            assert link['evidence']
            # A link is visible from both of its ends.
            back = client.get('/api/concepts/' + link['other']['id']).json()
            assert any(b['other']['id'] == concept['id'] and b['relation'] == link['relation']
                       and b['direction'] != link['direction'] for b in back['links'])
        links += len(data['links'])
    assert links == 2 * 39  # each of the 39 relations is seen from both ends


def test_unknown_concept_and_missing_graph(client, tmp_path):
    response = client.get('/api/concepts/e_missing')
    assert response.status_code == 404 and 'trace_id' in response.json()
    broken = TestClient(create_app(RagService(tmp_path / 'other', graph_path=tmp_path / 'none.json')))
    response = broken.get('/api/concepts')
    assert response.status_code == 503 and 'Concept map unavailable' in response.json()['error']


def test_invented_contact_details_are_removed_but_a_correct_guess_is_kept(client, service):
    # Seen in the live checks: the model wrote an address instead of copying [EMAIL_1].
    doc = upload(client, text='For billing questions write to billing@kestrel.example. ' * 10)
    service.generator = lambda question, evidence: json.dumps(
        {'answer': 'Write to refunds@kestrel.analytics.', 'answerable': True, 'citations': [evidence[0]['id']]})
    result = ask(client, doc, 'Who do I write to about billing?').json()
    assert 'refunds@kestrel.analytics' not in result['answer'] and 'contact removed' in result['answer']
    validate = service.traces.get(result['trace_id'])['spans'][-1]
    assert validate['attributes']['invented_contacts_removed'] == 1
    # The model can also guess the hidden address correctly: it is in the evidence, so it stays.
    service.generator = lambda question, evidence: json.dumps(
        {'answer': 'Write to billing@kestrel.example.', 'answerable': True, 'citations': [evidence[0]['id']]})
    result = ask(client, doc, 'Who do I write to about billing?').json()
    assert result['answer'] == 'Write to billing@kestrel.example.'
    assert service.traces.get(result['trace_id'])['spans'][-1]['attributes']['invented_contacts_removed'] == 0
