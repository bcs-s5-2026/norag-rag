"""Offline analysis of the graph-v2 evaluation runs (stdlib only, no LLM).

python evaluation/results/v3/graph_v2_2026-11-08/analyze.py [RESULT_DIR]
Writes summary.json, comparison.csv, by_type.csv, per_question.csv and tables.md
into RESULT_DIR (default: this folder). Overwrites them (derived files only)."""
import csv
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

KS = ('1', '3', '5', '10')
TYPES = ('exact_identifier', 'split_answer', 'vocabulary', 'versions', 'two_hop', 'not_in_corpus')


def load(base):
    runs = {}
    for path in sorted(base.glob('*.json')):
        if path.name == 'summary.json':
            continue
        data = json.loads(path.read_text())
        if 'results' in data:
            runs[path.stem] = data
    return runs


def graph_stats(path):
    g = json.loads(Path(path).read_text())
    proofs = g['provenance']
    return dict(build_id=g['build_id'], complete=g['complete'], model=g['manifest']['recipe']['model'],
                recipe=g['manifest']['recipe'].get('prompt_version'),
                entities=len(g['entities']), relations=len(g['relations']),
                entity_types=dict(Counter(e['type'] for e in g['entities'])),
                relation_types=dict(Counter(r['relation'] for r in g['relations'])),
                merges=sum(d['merged'] for d in g['merge_decisions']),
                merge_kinds=dict(Counter(d['kind'] for d in g['merge_decisions'] if d['merged'])),
                multi_name_entities=sum(len(e['names']) > 1 for e in g['entities']),
                heading_anchored_proofs=sum(bool(p.get('context_heading')) for p in proofs),
                chunks_with_relations=len({p['chunk_id'] for p in proofs}), total_chunks=g['coverage']['total_chunks'],
                coverage=g['coverage'], build_stats=g['build_stats'])


def main():
    base = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent
    root = Path(__file__).resolve().parents[4]
    runs = load(base)
    summary, comparison, by_type, per_q = dict(runs={}), [], [], []
    for name, data in runs.items():
        rows = data['results']
        times = [r['retrieval_seconds']*1000 for r in rows]
        entry = dict(corpus=data['corpus'], retrievers=data['retrieval']['retrievers'],
                     candidate_depth=data['retrieval']['candidate_depth'], overall=data['overall'], by_type=data['by_type'],
                     latency_ms=dict(mean=statistics.mean(times), median=statistics.median(times), max=max(times)),
                     llm_calls_per_question=0, tokens_per_question=0)
        if any('graph_fusion' in r for r in rows):
            g = [r['graph_fusion'] for r in rows if 'graph_fusion' in r]
            entry['graph_fusion'] = {k: dict(graph_chunks_in_top_k=sum(x['found_in_fused_at_k'][k] for x in g),
                                             questions_with_graph_chunk=sum(x['found_in_fused_at_k'][k] > 0 for x in g))
                                     for k in KS}
            entry['graph_candidates_total'] = sum(x['graph_candidate_count'] for x in g)
            entry['graph_build_id'] = rows[0]['graph_trace']['build_id']
        summary['runs'][name] = entry
        for k in KS:
            m = data['overall'][k]
            comparison.append([name, data['corpus'], k, m['answerable'], m['hit_rate'], m['quote_recall'],
                               round(entry['latency_ms']['median'], 2)])
            for t, values in data['by_type'].items():
                v = values[k]
                by_type.append([name, data['corpus'], t, k, v['answerable'], v['hit_rate'], v['quote_recall']])
        for r in rows:
            per_q.append([name, data['corpus'], r['id'], r['type'], r['answerable'],
                          *[r['quote_recall'][k] for k in KS], round(r['retrieval_seconds']*1000, 2),
                          (r.get('graph_fusion') or {}).get('graph_candidate_count')])
    bundle = root/'concepts/kestrel_graph_v2/graph.json'
    if bundle.exists():
        summary['graph_v2'] = graph_stats(bundle)
    old = root/'concepts/kestrel_graph/graph.json'
    if old.exists():
        summary['graph_v1'] = graph_stats(old)
    # Regressions: questions whose Recall@5 drops when a retriever is added.
    pairs = [('kestrel-dense', 'kestrel-dense-bm25'), ('kestrel-dense-bm25', 'kestrel-dense-bm25-graph'),
             ('kestrel-dense', 'kestrel-dense-graph'), ('kestrel-dense', 'kestrel-dense-bm25-graph'),
             ('vellora-dense', 'vellora-dense-bm25'), ('kestrel-dense-bm25-graph-v1', 'kestrel-dense-bm25-graph')]
    summary['changes_at_5'] = {}
    for a, b in pairs:
        if a in runs and b in runs:
            ra = {r['id']: r for r in runs[a]['results']}
            changes = [dict(id=r['id'], type=r['type'], before=ra[r['id']]['quote_recall']['5'], after=r['quote_recall']['5'])
                       for r in runs[b]['results'] if r['answerable'] and r['quote_recall']['5'] != ra[r['id']]['quote_recall']['5']]
            summary['changes_at_5'][f'{a} -> {b}'] = changes
    (base/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    for fname, header, data in (('comparison.csv', ['run', 'corpus', 'k', 'answerable', 'hit_rate', 'recall', 'median_latency_ms'], comparison),
                                ('by_type.csv', ['run', 'corpus', 'type', 'k', 'answerable', 'hit_rate', 'recall'], by_type),
                                ('per_question.csv', ['run', 'corpus', 'id', 'type', 'answerable', 'recall@1', 'recall@3', 'recall@5', 'recall@10', 'latency_ms', 'graph_candidates'], per_q)):
        with (base/fname).open('w', newline='') as stream:
            w = csv.writer(stream); w.writerow(header); w.writerows(data)
    # Markdown tables for REPORT.md
    f = lambda x: '–' if x is None else f'{x:.2f}'
    lines = ['| Run | Corpus | Type | n | Hit@1 | Hit@3 | Hit@5 | Hit@10 | R@1 | R@3 | R@5 | R@10 |', '|'+'---|'*12]
    for name, data in runs.items():
        for t in ('overall',)+TYPES:
            v = data['overall'] if t == 'overall' else data['by_type'].get(t)
            if not v or not v['5']['answerable']:
                continue
            lines.append(f"| {name} | {data['corpus']} | {t} | {v['5']['answerable']} | "+' | '.join(f(v[k]['hit_rate']) for k in KS)+' | '+' | '.join(f(v[k]['quote_recall']) for k in KS)+' |')
    (base/'tables.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({n: dict(R5=e['overall']['5']['quote_recall'], H5=e['overall']['5']['hit_rate'],
                              two_hop_R5=(e['by_type'].get('two_hop') or {}).get('5', {}).get('quote_recall'),
                              fusion5=(e.get('graph_fusion') or {}).get('5')) for n, e in summary['runs'].items()}, indent=1))


if __name__ == '__main__':
    main()
