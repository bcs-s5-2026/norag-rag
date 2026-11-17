"""Offline graph traversal/integration tests; hosted generation is always mocked."""
import copy
import json
from pathlib import Path
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from rag_app.api import create_app
from rag_app.fusion import reciprocal_rank_fusion
from rag_app.graph_build import GraphBuilder, digest
from rag_app.graph_schema import ProviderResponse
from rag_app.graph_retrieval import GraphIndex, GraphRetrievalError
from rag_app.models import RetrievalConfig, Settings
from rag_app.service import PipelineError, RagService


@pytest.fixture
def snapshot(tmp_path):
    source = tmp_path/'sources'; source.mkdir()
    texts = {'a.md': 'KST-5031 is raised by postroom.',
             'b.md': 'postroom is owned by Messaging.',
             'c.md': 'Messaging uses #oncall-messaging.'}
    for name, text in texts.items(): (source/name).write_text(text)
    builder = GraphBuilder(data_dir=tmp_path/'build', source_dir=source)
    def fake(messages, config):
        c = json.loads(messages[1]['content'])['chunk']
        if c['name'] == 'a.md': a, r, b = ('ErrorCode','KST-5031'),'RAISED_BY',('Service','postroom')
        elif c['name'] == 'b.md': a, r, b = ('Service','postroom'),'OWNED_BY',('Team','Messaging')
        else: a, r, b = ('Team','Messaging'),'CONTACT_CHANNEL',('Channel','#oncall-messaging')
        raw = dict(triples=[dict(subject={'type':a[0],'label':a[1]},relation=r,object={'type':b[0],'label':b[1]},evidence_quote=c['text'])],aliases=[])
        return ProviderResponse(text=json.dumps(raw), model='mock-only',input_tokens=10,output_tokens=10)
    graph = builder.build(approved=True,extractor=fake)
    path = tmp_path/'graph.json'; path.write_text(json.dumps(graph))
    service = RagService(tmp_path/'library',graph_path=path,
        generator=lambda q, es: json.dumps({'answer':'Messaging in #oncall-messaging.','answerable':True,'citations':[es[-1]['id']]}))
    ids = [service.upload(name,text.encode())['id'] for name,text in texts.items()]
    return graph,path,service,ids


def test_three_edges_return_ranked_bridge_and_terminal_chunks(snapshot):
    graph,path,service,ids = snapshot
    rows,trace = GraphIndex.load(path).search('Who owns KST-5031 and where?',ids,Settings())
    assert {r['document_id'] for r in rows} == set(ids)
    assert [r['rank'] for r in rows] == list(range(1,len(rows)+1))
    assert any([e['relation'] for e in p['edges']]==['RAISED_BY','OWNED_BY','CONTACT_CHANNEL'] for p in trace['paths'])
    assert trace['matched_entities'][0]['type']=='ErrorCode'
    assert all(r['graph_path_ids'] for r in rows)
    assert rows == GraphIndex.load(path).search('Who owns KST-5031 and where?',ids,Settings())[0]


def test_descriptor_seeds_and_selection_scope(snapshot):
    graph,path,service,ids = snapshot
    rows,trace = GraphIndex.load(path).search('Who is raised by this code?',ids,Settings())
    assert trace['matched_entities'] and trace['matched_entities'][0]['matched_by']=='lexical_graph_descriptor'
    subset,trace = GraphIndex.load(path).search('KST-5031',ids[:1],Settings())
    assert {r['document_id'] for r in subset} == {ids[0]}
    assert all(c['document_id']==ids[0] for c in trace['chunks'])
    assert all(p['document_id']==ids[0] for path in trace['paths'] for edge in path['edges'] for p in edge['evidence'])
    with pytest.raises(GraphRetrievalError,match='Kestrel'):
        GraphIndex.load(path).search('q',['unknown'],Settings())
    with pytest.raises(GraphRetrievalError,match='settings'):
        GraphIndex.load(path).search('q',ids,Settings(chunk_size=500))


def test_empty_graph_and_partial_coverage_explicit(snapshot):
    graph,path,service,ids = snapshot
    rows,trace=GraphIndex(graph).search('unicorn bananas',ids,Settings())
    assert rows==[] and trace['reason']
    partial=copy.deepcopy(graph);partial['complete']=False
    partial['coverage']['valid_chunks']=1
    path.write_text(json.dumps(partial))
    result=service.retrieve_configured('KST-5031',ids,Settings(),RetrievalConfig(retrievers=['graph']))
    assert result['retrievers']['graph']['status']=='partial'
    assert not result['graph_trace']['complete']


def test_missing_corrupt_and_invalid_proof_fail_explicitly(snapshot,tmp_path):
    graph,path,service,ids=snapshot
    with pytest.raises(GraphRetrievalError,match='unavailable'): GraphIndex.load(tmp_path/'missing')
    bad=copy.deepcopy(graph);bad['provenance'][0]['quote']='made up'
    bad['graph_content_sha256']=digest({k:bad[k] for k in ('entities','relations','provenance','merge_decisions')})
    with pytest.raises(GraphRetrievalError,match='proof'):GraphIndex(bad)
    path.write_text('broken')
    with pytest.raises(PipelineError,match='graph retrieval failed'):
        service.retrieve_configured('KST-5031',ids,Settings(),RetrievalConfig(retrievers=['dense','graph']))


def test_all_three_rrf_origin_path_provenance(snapshot):
    graph,path,service,ids=snapshot
    response=service.retrieve_configured('KST-5031',ids,Settings(),RetrievalConfig(retrievers=['dense','bm25','graph']))
    assert set(response['retrievers'])=={'dense','bm25','graph'}
    assert len({p['id'] for p in response['results']})==len(response['results'])
    for p in response['results']:
        assert p['rrf_score']==pytest.approx(sum(1/(60+o['rank']) for o in p['origins'].values()))
        if 'graph' in p['origins']:assert p['origins']['graph']['path_ids']
    assert response['graph_trace']['fused_chunk_ranks']


def test_configured_answer_cites_exact_fused_snapshot_once(snapshot,monkeypatch):
    graph,path,service,ids=snapshot
    original=service.retrieve_configured
    spy=Mock(side_effect=original);monkeypatch.setattr(service,'retrieve_configured',spy)
    answer=service.ask_configured('KST-5031',ids,Settings(),RetrievalConfig(retrievers=['graph']))
    assert spy.call_count==1
    assert answer['references'][0]['origins']['graph']['path_ids']
    assert answer['references'][0]['id'] in {p['id'] for p in answer['retrieved']}
    assert answer['graph_trace']['paths']


def test_graph_api_ask_and_evaluation_controls(snapshot,monkeypatch):
    graph,path,service,ids=snapshot
    client=TestClient(create_app(service))
    body=dict(document_ids=ids,question='KST-5031',retrieval={'retrievers':['graph']})
    answer=client.post('/api/ask',json=body)
    assert answer.status_code==200 and answer.json()['graph_trace']['paths']
    assert client.post('/api/evaluations/v3',json={'corpus':'vellora','retrieval':{'retrievers':['graph']}}).status_code==422
    from evaluation import v3
    monkeypatch.setattr(v3,'run',lambda *args:{'corpus':'kestrel','results':[],'overall':{},'by_type':{}})
    assert client.post('/api/evaluations/v3',json={'corpus':'kestrel','retrieval':{'retrievers':['dense','bm25','graph']},'question_set':'v3'}).status_code==200
    assert client.post('/api/retrieve',json={**body,'retrieval':{'retrievers':[]}}).status_code==422


def test_append_only_three_two_hop_questions_and_evidence():
    from evaluation.v2 import questions
    from evaluation.v3_questions import load
    from rag_app.service import ROOT
    original=questions('kestrel');expanded,hashes,fingerprint=load('kestrel','v3')
    assert expanded[:10]==original and len(expanded)==12
    assert sum(q['type']=='two_hop' for q in expanded)==3
    assert set(q['id'] for q in expanded[-2:])=={'q11','q12'}
    assert len(hashes)==2
    for q in expanded[-2:]:
        assert len(q['evidence'])>=2
        for e in q['evidence']:assert e['quote'] in (ROOT/'docs/kestrel'/e['source']).read_text()
    assert load('vellora','v3')[0]==questions('vellora')


def test_bounded_context_repair_does_not_assign_wrong_neighbor_owner(tmp_path):
    from rag_app.graph_context import expand_quote
    from rag_app.graph_schema import Triple
    text='### gateway\nOwner: **Platform**.\n\n### auth\nOwner: **Identity**.'
    chunk={'text':text}
    def owner(name,team):
        return Triple.model_validate(dict(subject={'type':'Service','label':name},relation='OWNED_BY',
             object={'type':'Team','label':team},evidence_quote=f'Owner: **{team}**.'))
    fixed=expand_quote(owner('gateway','Platform'),chunk)
    assert fixed['evidence_quote']=='### gateway\nOwner: **Platform**.'
    assert fixed['subject']['label']=='gateway' and fixed['object']['label']=='Platform'
    assert expand_quote(owner('auth','Platform'),chunk) is None


def test_context_expansion_preserves_condition_and_does_not_repair_arbitrary_relations():
    from rag_app.graph_context import expand_quote
    from rag_app.graph_schema import Triple
    text='### KST-1012 — SSO failure\n**Escalate:** to Identity if the error persists.'
    value=dict(subject={'type':'ErrorCode','label':'KST-1012'},relation='ESCALATE_TO',
               object={'type':'Team','label':'Identity'},evidence_quote='**Escalate:** to Identity if the error persists.',condition_quote='if the error persists')
    fixed=expand_quote(Triple.model_validate(value),{'text':text})
    assert fixed['condition_quote']=='if the error persists'
    assert fixed['evidence_quote']==text


def test_published_snapshot_and_review_sampling_are_integral_and_ungraded(tmp_path):
    from rag_app.graph_review import prepare
    from rag_app.service import ROOT
    path=ROOT/'concepts/kestrel_graph/graph.json'
    index=GraphIndex.load(path)
    assert len(index.edges)>=10
    a=prepare(path,tmp_path/'one.json',seed=20261108)
    b=prepare(path,tmp_path/'two.json',seed=20261108)
    assert [x['id'] for x in a['triples']]==[x['id'] for x in b['triples']]
    assert len({x['id'] for x in a['triples']})==10
    assert a['counts'] is None and a['status']=='awaiting_human_grades'
    assert all(x['grade'] is None and x['reviewer'] is None for x in a['triples'])
    for row in a['triples']:
        for proof in row['evidence']:assert proof['provenance']['quote'] in proof['source_passage']
    with pytest.raises(ValueError,match='overwrite'):prepare(path,tmp_path/'one.json')
