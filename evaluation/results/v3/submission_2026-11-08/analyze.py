"""Recalculate final retrieval metrics, original-set slices and graph survival offline."""
import csv
import hashlib
import json
import statistics
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
BASE=Path(__file__).resolve().parent
KS=(1,3,5,10)


def metric(rows,k):
    eligible=[r for r in rows if r['answerable']]
    return dict(answerable=len(eligible),hits=sum(r['hits'][str(k)] for r in eligible),
                hit_rate=sum(r['hits'][str(k)] for r in eligible)/len(eligible) if eligible else None,
                quote_recall=sum(r['quote_recall'][str(k)] for r in eligible)/len(eligible) if eligible else None)


def analyze():
    summary=[]
    for record in json.loads((BASE/'run_manifest.json').read_text()):
        path=ROOT/record['output'];data=json.loads(path.read_text())
        assert hashlib.sha256(path.read_bytes()).hexdigest()==record['sha256']
        original=[json.loads(x) for x in (ROOT/'evaluation'/f"{data['corpus']}.jsonl").read_text().splitlines() if x.strip()]
        expected=original[:]
        if data['corpus']=='kestrel':expected += [json.loads(x) for x in (ROOT/'evaluation/kestrel-v3-additions.jsonl').read_text().splitlines() if x.strip()]
        assert len(expected)==len(data['results'])
        ids={name:hashlib.sha256((ROOT/'docs'/('kestrel' if data['corpus']=='kestrel' else '')/name).read_text(encoding='utf-8-sig').encode()).hexdigest() for name in data['corpus_sha256']}
        for name,h in data['corpus_sha256'].items():assert hashlib.sha256((ROOT/'docs'/('kestrel' if data['corpus']=='kestrel' else '')/name).read_bytes()).hexdigest()==h
        for gold,row in zip(expected,data['results']):
            assert all(row[k]==v for k,v in gold.items())
            assert row['llm_calls']==0 and row['input_tokens']==0 and row['output_tokens']==0
            assert row['selected']==row['retrieved'][:data['settings']['top_k']]
            for p in row['retrieved']:
                source=(ROOT/'docs'/('kestrel' if data['corpus']=='kestrel' else '')/p['name']).read_text(encoding='utf-8-sig')
                assert p['text']==source[p['start']:p['end']] and p['document_id']==ids[p['name']]
                assert p['id']==f"{p['document_id']}:{p['start']}:{p['end']}"
            for k in KS:
                found=[any(p['document_id']==ids[e['source']] and e['quote'] in p['text'] for p in row['retrieved'][:k]) for e in gold['evidence']]
                assert row['hits'][str(k)]==(any(found) if gold['answerable'] else None)
                assert row['quote_recall'][str(k)]==(sum(found)/len(found) if found else None)
        for k in KS:assert metric(data['results'],k)==data['overall'][str(k)]
        for typ,values in data['by_type'].items():
            for k in KS:assert metric([r for r in data['results'] if r['type']==typ],k)==values[str(k)]
        times=[r['retrieval_seconds'] for r in data['results']]
        old=data['results'][:len(original)]
        comparison=dict(corpus=data['corpus'],configuration=record['configuration'],output=record['output'],
                        questions=len(data['results']),retrieval=data['retrieval'],dataset_sha256=data['dataset_sha256'],
                        original_dataset_files=data['dataset_files_sha256'],overall=data['overall'],by_type=data['by_type'],
                        original_v2_slice={str(k):metric(old,k) for k in KS},
                        latency=dict(mean_ms=statistics.mean(times)*1000,median_ms=statistics.median(times)*1000,
                                     first_ms=times[0]*1000,post_first_mean_ms=statistics.mean(times[1:])*1000),
                        llm_calls=0,failures=0,partial_graph_questions=sum(r['retrievers'].get('graph',{}).get('status')=='partial' for r in data['results']),
                        per_question=[dict(id=r['id'],type=r['type'],hits=r['hits'],recall=r['quote_recall'],latency_seconds=r['retrieval_seconds'],
                                           graph_fusion=r.get('graph_fusion')) for r in data['results']])
        if 'graph' in data['retrieval']['retrievers']:
            comparison['graph_build_id']=data['results'][0]['graph_trace']['build_id']
            comparison['graph_fusion']={str(k):dict(surviving_chunks=sum(r['graph_fusion']['found_in_fused_at_k'][str(k)] for r in data['results']),
                                          candidate_chunks=sum(r['graph_fusion']['graph_candidate_count'] for r in data['results'])) for k in KS}
        summary.append(comparison)
    return dict(runs=summary,verified=dict(original_questions_preserved=True,added_questions_explicit=True,
              literal_metrics_recomputed=True,source_ids_and_offsets_verified=True,no_evaluation_llm_calls=True),
              manual_extraction_quality_counts=None)


if __name__=='__main__':
    result=analyze()
    path=BASE/'summary.json'
    if path.exists():raise SystemExit('Summary exists; refuse overwrite.')
    path.write_text(json.dumps(result,indent=2)+'\n')
    with (BASE/'comparison.csv').open('x',newline='') as stream:
        w=csv.writer(stream);w.writerow(['corpus','configuration','k','answerable','hit_rate','recall','mean_latency_ms','median_latency_ms','retrieval_failures','partial_graph_questions'])
        for r in result['runs']:
            for k in KS:
                m=r['overall'][str(k)]
                w.writerow([r['corpus'],r['configuration'],k,m['answerable'],m['hit_rate'],m['quote_recall'],r['latency']['mean_ms'],r['latency']['median_ms'],r['failures'],r['partial_graph_questions']])
    print('Verified',len(result['runs']),'evaluation configurations/sensitivity runs; all literal metrics recomputed.')
