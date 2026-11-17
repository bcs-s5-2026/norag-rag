"""Compare the V4 re-run of the V3 retrieval evaluation with the committed V3 runs.

    python evaluation/results/v4/retrieval_regression_2026-11-12/compare.py

For every question the ranked list of retrieved chunk ids must be identical.
"""
import json
import statistics
from pathlib import Path

HERE = Path(__file__).parent
V3 = HERE.parents[1] / 'v3'
BASELINES = {  # V4 file -> committed V3 run (the final V3 numbers reported in REPORT.md)
    'kestrel-dense': V3 / 'graph_v2_seedfix_2026-11-08/kestrel-dense.json',
    'kestrel-dense-bm25': V3 / 'graph_v2_seedfix_2026-11-08/kestrel-dense-bm25.json',
    'kestrel-graph': V3 / 'graph_v2_seedfix_2026-11-08/kestrel-graph.json',
    'kestrel-dense-bm25-graph': V3 / 'graph_v2_seedfix_2026-11-08/kestrel-dense-bm25-graph.json',
    'vellora-dense': V3 / 'graph_v2_final_2026-11-08/vellora-dense.json',
    'vellora-bm25': V3 / 'graph_v2_final_2026-11-08/vellora-bm25.json',
    'vellora-dense-bm25': V3 / 'graph_v2_final_2026-11-08/vellora-dense-bm25.json',
}


def median_ms(run):
    return round(statistics.median(r['retrieval_seconds'] for r in run['results']) * 1000, 1)


rows = []
for name, baseline_path in BASELINES.items():
    new = json.loads((HERE / f'{name}.json').read_text())
    old = json.loads(baseline_path.read_text())
    same = sum([c['id'] for c in a['retrieved']] == [c['id'] for c in b['retrieved']]
               for a, b in zip(new['results'], old['results']))
    rows.append(dict(run=name, questions=len(new['results']), identical_rankings=same,
                     recall_at_5_v3=old['overall']['5']['quote_recall'], recall_at_5_v4=new['overall']['5']['quote_recall'],
                     hit_at_5_v3=old['overall']['5']['hit_rate'], hit_at_5_v4=new['overall']['5']['hit_rate'],
                     same_metrics=new['overall'] == old['overall'] and new['by_type'] == old['by_type'],
                     median_ms_v3=median_ms(old), median_ms_v4=median_ms(new)))
(HERE / 'comparison.json').write_text(json.dumps(rows, indent=2) + '\n')
for row in rows:
    print(row)
