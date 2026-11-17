import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from evaluation import v2
from rag_app.api import create_app
from rag_app.models import Settings
from rag_app.service import ROOT, RagService, chunks
from rag_app.words import analyze, tokens


def test_frozen_v1_and_kestrel():
    baseline=json.loads((ROOT/'evaluation/baseline.json').read_text())
    old=json.loads((ROOT/'evaluation/questions.json').read_text())
    assert hashlib.sha256(json.dumps(old,sort_keys=True).encode()).hexdigest()==baseline['dataset_sha256']
    assert hashlib.sha256((ROOT/'docs/vellora-duo-espresso-machine.txt').read_bytes()).hexdigest()==baseline['corpus_sha256']['vellora-duo-espresso-machine.txt']
    converted=v2.questions('vellora')
    assert len(converted)==15
    for a,b in zip(old,converted):
        assert a['question']==b['question'] and a['expected_answer']==b['expected_answer']
        if a['answerable']: assert b['evidence']==[{'source':a['source'],'quote':a['passage']}]
    kestrel=v2.questions('kestrel')
    assert len(kestrel)==10
    for q in kestrel:
        for e in q['evidence']:
            assert e['quote'] in (ROOT/'docs/kestrel'/e['source']).read_text()


def test_words_counts_offsets_filtering(tmp_path):
    service=RagService(tmp_path)
    a=service.upload('a.txt',b'Tank tank KST-2044. '+b'water '*30)['id']
    b=service.upload('b.txt',b'Excluded phone')['id']
    settings=Settings(chunk_size=100,chunk_overlap=20)
    result=analyze(service,[a,a],settings,'TANK phone KST-2044')
    assert tokens("KST-2044 isn't CAFÉ")==['kst-2044',"isn't",'café']
    assert [r['present'] for r in result['words']]==[True,False,True]
    assert result['words'][0]['occurrences']==2
    assert result['chunk_count']==len(list(chunks(service.read(a)['text'],settings)))
    for w in result['words']:
        for p in w['passages']:
            assert p['document_id']==a and p['document_id']!=b
            assert p['text']==service.read(a)['text'][p['start']:p['end']]
    assert analyze(service,[a],settings,word='phone')['words'][0]['passages']==[]


def test_metrics_multiquote_and_unanswerable():
    rows=[dict(answerable=True,hits={'1':True},quote_recall={'1':.5}),dict(answerable=True,hits={'1':False},quote_recall={'1':0}),dict(answerable=False,hits={'1':None},quote_recall={'1':None})]
    assert v2.metrics(rows,1)==dict(answerable=2,hits=1,hit_rate=.5,quote_recall=.25)
    assert v2.metrics(rows[-1:],1)['hit_rate'] is None


def test_evaluator_mock_llm_real_retrieval(tmp_path):
    service=RagService(tmp_path,generator=lambda q,e:json.dumps(dict(answer='The selected documents do not provide enough evidence.',answerable=False,citations=[])))
    result=v2.evaluate(service,'kestrel',Settings(),answers=True,check_no_context=True,no_context_fn=lambda q:'I do not know.')
    assert len(result['corpus_sha256'])==5  # include superseded billing policy, too
    assert result['unanswerable_excluded']==2
    assert set(result['overall'])=={'1','3','5','10'}
    assert sum(len([r for r in result['results'] if r['type']==t and r['answerable']]) for t in result['by_type'])==8
    for row in result['results']:
        assert row['no_context_correct'] is None and row['grade'] is None
        assert row['no_context_answer']=='I do not know.'
        assert row['response']['answerable'] is False
        assert len(row['retrieved'])==10
        if row['answerable']:
            assert row['hits']['1'] <= row['hits']['3'] <= row['hits']['5'] <= row['hits']['10']
        else: assert all(v is None for v in row['hits'].values())


def test_new_api_and_validation(tmp_path):
    client=TestClient(create_app(RagService(tmp_path)))
    assert client.post('/api/corpora/unknown',json={}).status_code==400
    docs=client.post('/api/corpora/kestrel',json={}).json()
    assert len(docs)==5
    body={'document_ids':[docs[0]['id']], 'question':'refund'}
    response=client.post('/api/search',json=body)
    assert response.status_code==200
    assert all(p['document_id']==docs[0]['id'] for p in response.json())
    assert client.post('/api/words',json={**body,'word':''}).status_code==200
    assert client.post('/api/words',json={'document_ids':[]}).status_code==422
    assert client.post('/api/evaluations',json={'corpus':'../secret'}).status_code==422
    assert len(client.get('/api/question-sets').json()['kestrel'])==10
    assert 'Denis Amselemovitch' in client.get('/about').text
    assert '/about' not in client.get('/').text
    assert client.get('/api/evaluations/not-a-run').status_code==404


def test_frontend_evaluation_save_grade_download(tmp_path,monkeypatch):
    sample=dict(corpus='kestrel',results=[dict(id='q01',response={'answer':'example'},no_context_answer='I do not know.',grade=None)],grading_rules=v2.GRADING_RULES)
    monkeypatch.setattr(v2,'run',lambda *args:sample)
    client=TestClient(create_app(RagService(tmp_path)))
    response=client.post('/api/evaluations',json={'corpus':'kestrel','answers':True})
    assert response.status_code==200
    run_id=response.json()['run_id']
    grade=dict(question_id='q01',grade='partial',notes='One expected fact omitted.',reviewer='Test reviewer',no_context_correct=False)
    assert client.post(f'/api/evaluations/{run_id}/grades',json=grade).status_code==200
    result=client.get(f'/api/evaluations/{run_id}').json()
    assert result['results'][0]['grade']=='partial'
    assert result['results'][0]['no_context_correct'] is False
    assert json.loads((tmp_path/'evaluations'/f'{run_id}.json').read_text())==result
    assert client.post(f'/api/evaluations/{run_id}/grades',json={**grade,'grade':'invented'}).status_code==422
    assert client.post(f'/api/evaluations/{run_id}/grades',json={**grade,'question_id':'missing'}).status_code==404


def test_no_context_missing_key(monkeypatch):
    monkeypatch.setenv('GOOGLE_API_KEY','')
    from rag_app.service import PipelineError
    with pytest.raises(PipelineError,match='GOOGLE_API_KEY'): v2.no_context('secret question')


def test_no_context_only_review_and_grade_guard(tmp_path):
    sample=dict(corpus='vellora',results=[dict(id='q01',no_context_answer='I do not know.',grade=None,no_context_correct=None)])
    run_id=v2.save(sample,tmp_path/'evaluations')
    client=TestClient(create_app(RagService(tmp_path)))
    review=dict(question_id='q01',notes='No factual answer.',reviewer='Test reviewer',no_context_correct=False)
    assert client.post(f'/api/evaluations/{run_id}/grades',json=review).status_code==200
    assert client.get(f'/api/evaluations/{run_id}').json()['results'][0]['no_context_correct'] is False
    assert client.post(f'/api/evaluations/{run_id}/grades',json={**review,'grade':'correct'}).status_code==400
    assert client.post(f'/api/evaluations/{run_id}/grades',json={**review,'no_context_correct':None}).status_code==422


def test_measured_run_import_does_not_modify_evidence(tmp_path):
    path=ROOT/'evaluation/results/vellora-800-80.json'
    original=path.read_bytes()
    client=TestClient(create_app(RagService(tmp_path)))
    assert path.name in client.get('/api/measured-runs').json()
    result=client.post('/api/measured-runs/'+path.name,json={})
    assert result.status_code==200
    assert result.json()['result']['corpus']=='vellora'
    assert path.read_bytes()==original
    assert client.post('/api/measured-runs/not-a-file.json',json={}).status_code==404


def test_evaluation_errors_retained_without_fake_grades(tmp_path):
    from rag_app.service import PipelineError
    class FakeService:
        def upload(self,name,content): return {'id':name}
        def retrieve(self,*args): return []
        def ask(self,*args): raise PipelineError('LLM unavailable.')
    def failure(q): raise PipelineError('No-context unavailable.')
    result=v2.evaluate(FakeService(),'kestrel',Settings(),True,True,failure)
    assert len(result['results'])==10
    assert all(r['grade'] is None and r['no_context_correct'] is None for r in result['results'])
    assert all('generation_error' in r and 'no_context_error' in r for r in result['results'])
    assert result['overall']['10']['hit_rate']==0
