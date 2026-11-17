"""Verify immutable CLI runs against sources and derive Phase 2.5 benchmark tables.

Standard library only. Does not import application/model code or invoke retrieval.
Use --output-dir to reproduce derived tables without overwriting saved evidence.
"""
import argparse
import csv
import hashlib
import json
import math
import statistics
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[4]
KS = (1, 3, 5, 10)
TYPES = ('exact_identifier', 'split_answer', 'vocabulary', 'not_in_corpus', 'versions', 'two_hop', 'other')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def metrics(rows, k):
    eligible = [r for r in rows if r['answerable']]
    return dict(answerable=len(eligible), hits=sum(r['hits'][str(k)] for r in eligible),
                hit_rate=statistics.mean(int(r['hits'][str(k)]) for r in eligible) if eligible else None,
                quote_recall=statistics.mean(r['quote_recall'][str(k)] for r in eligible) if eligible else None)


def latency(rows):
    times = [r['retrieval_seconds'] for r in rows]
    if not times:
        return dict(n=0, mean_seconds=None, median_seconds=None, p95_seconds=None)
    return dict(n=len(times), mean_seconds=statistics.mean(times), median_seconds=statistics.median(times),
                p95_seconds=sorted(times)[math.ceil(.95*len(times))-1])


def canonical(corpus, hashes):
    rows = {}
    for name, expected in hashes.items():
        path = ROOT/'docs'/('kestrel' if corpus == 'kestrel' else '')/name
        assert sha(path) == expected
        text = path.read_text(encoding='utf-8-sig')
        doc_id = hashlib.sha256(text.encode()).hexdigest()
        for start in range(0, len(text), 720):
            end = min(start+800, len(text))
            if text[start:end].strip():
                identifier = f'{doc_id}:{start}:{end}'
                rows[identifier] = dict(id=identifier, document_id=doc_id, name=name, text=text[start:end],
                                        start=start, end=end, line=text.count('\n', 0, start)+1)
            if end == len(text):
                break
    return rows


def analyze():
    manifest = json.loads((BASE/'manifest.json').read_text())
    runs, grouped, annotations, per_question = [], {}, [], []
    for entry in manifest['runs']:
        assert entry['status'] == 'complete' and entry['exit_code'] == 0
        path = ROOT/entry['output']
        assert sha(path) == entry['output_sha256']
        raw = json.loads(path.read_text())
        corpus, label = raw['corpus'], entry['configuration']
        dataset_path = ROOT/'evaluation'/f'{corpus}.jsonl'
        dataset = [json.loads(x) for x in dataset_path.read_text().splitlines() if x.strip()]
        assert raw['dataset_sha256'] == sha(dataset_path)
        assert raw['settings'] == dict(chunk_size=800, chunk_overlap=80, top_k=5)
        assert raw['retrieval']['candidate_depth'] == 20 and raw['retrieval']['rrf_k'] == 60
        assert raw['retrieval_depth'] == 10 and raw['llm_calls'] == 0 and raw['answers'] is False
        assert [q['id'] for q in dataset] == [q['id'] for q in raw['results']]
        universe = canonical(corpus, raw['corpus_sha256'])
        assert len(universe) == 43
        returned = 0
        for gold, row in zip(dataset, raw['results']):
            assert all(row[key] == value for key, value in gold.items())
            assert row['llm_calls'] == 0 and math.isfinite(row['retrieval_seconds']) and row['retrieval_seconds'] >= 0
            assert set(row['retrievers']) == set(raw['retrieval']['retrievers'])
            for status in row['retrievers'].values():
                assert status['status'] in ('ok', 'empty') and 0 <= status['candidate_count'] <= 20
                assert (status['status'] == 'empty') == (status['candidate_count'] == 0)
            evidence = row['retrieved']
            assert row['selected'] == evidence[:5]
            assert len({p['id'] for p in evidence}) == len(evidence)
            assert [p['fused_rank'] for p in evidence] == list(range(1, len(evidence)+1))
            assert evidence == sorted(evidence, key=lambda p: (-p['rrf_score'], p['id']))
            origin_ranks = {}
            for p in evidence:
                returned += 1
                expected = universe[p['id']]
                assert all(p[key] == value for key, value in expected.items())
                assert p['origins'] and set(p['origins']) <= set(raw['retrieval']['retrievers'])
                for origin, info in p['origins'].items():
                    assert 1 <= info['rank'] <= row['retrievers'][origin]['candidate_count']
                    assert info['rank'] not in origin_ranks.setdefault(origin, set())
                    origin_ranks[origin].add(info['rank'])
                    assert math.isfinite(info['raw_score'])
                score = math.fsum(1/(60+x['rank']) for x in p['origins'].values())
                assert math.isclose(p['rrf_score'], score, rel_tol=0, abs_tol=1e-15)
            first_ranks = [next((p['fused_rank'] for p in evidence if p['name'] == e['source'] and e['quote'] in p['text']), None)
                           for e in gold['evidence']]
            for k in KS:
                found = [r is not None and r <= k for r in first_ranks]
                assert row['hits'][str(k)] == (any(found) if gold['answerable'] else None)
                assert row['quote_recall'][str(k)] == (sum(found)/len(found) if found else None)
            per_question.append(dict(corpus=corpus, configuration=label, id=gold['id'], question=gold['question'],
                                     type=gold['type'], answerable=gold['answerable'], hits=row['hits'],
                                     recall=row['quote_recall'], evidence_first_ranks_within_10=first_ranks,
                                     latency_seconds=row['retrieval_seconds'], retrieval_failures=0,
                                     empty_retrievers=[n for n, s in row['retrievers'].items() if s['status'] == 'empty']))
        rows = raw['results']
        for k in KS:
            assert metrics(rows, k) == raw['overall'][str(k)]
        for typ, values in raw['by_type'].items():
            for k in KS:
                assert metrics([r for r in rows if r['type'] == typ], k) == values[str(k)]
        if label == 'dense':
            baseline = json.loads((ROOT/'evaluation/results'/f'{corpus}-800-80.json').read_text())
            assert raw['overall'] == baseline['overall'] and raw['by_type'] == baseline['by_type']
            assert [(r['hits'], r['quote_recall']) for r in rows] == [(r['hits'], r['quote_recall']) for r in baseline['results']]
        all_rates = {str(k): statistics.mean(int(r['quote_recall'][str(k)] == 1) for r in rows if r['answerable']) for k in KS}
        run = dict(corpus=corpus, configuration=label, output=entry['output'], output_sha256=entry['output_sha256'],
                   questions=len(rows), answerable=sum(r['answerable'] for r in rows),
                   retrieval_failures=0, overall=raw['overall'], by_type={},
                   all_annotated_evidence_rate=all_rates, latency=latency(rows),
                   first_question_seconds=rows[0]['retrieval_seconds'], post_first_latency=latency(rows[1:]),
                   process_wall_seconds=entry['process_wall_seconds'], llm_calls=0,
                   empty_retriever_counts={n: sum(r['retrievers'][n]['status'] == 'empty' for r in rows) for n in raw['retrieval']['retrievers']},
                   verification=dict(dataset_exact=True, canonical_chunks=len(universe), returned_chunks_verified=returned,
                                     canonical_id_set_sha256=hashlib.sha256('\n'.join(sorted(universe)).encode()).hexdigest(),
                                     metrics_recomputed=True, rrf_scores_recomputed=True))
        for typ in TYPES:
            subset = [r for r in rows if r['type'] == typ]
            run['by_type'][typ] = dict(questions=len(subset), overall={str(k): metrics(subset, k) for k in KS}, latency=latency(subset))
        runs.append(run)
        grouped.setdefault(corpus, {})[label] = raw
    comparisons = []
    for corpus, configs in grouped.items():
        reference = configs['dense']
        assert all(c['dataset_sha256'] == reference['dataset_sha256'] and c['corpus_sha256'] == reference['corpus_sha256'] for c in configs.values())
        universes = [r['verification']['canonical_id_set_sha256'] for r in runs if r['corpus'] == corpus]
        assert len(set(universes)) == 1
        dataset = reference['results']
        for i, q in enumerate(dataset):
            values = {label: next(p for p in per_question if p['corpus'] == corpus and p['configuration'] == label and p['id'] == q['id']) for label in configs}
            deltas = {}
            for challenger, baseline in [('bm25', 'dense'), ('dense-bm25-rrf', 'dense'), ('dense-bm25-rrf', 'bm25')]:
                deltas[challenger+'_vs_'+baseline] = {str(k): dict(
                    hit=(int(values[challenger]['hits'][str(k)])-int(values[baseline]['hits'][str(k)])) if q['answerable'] else None,
                    recall=(values[challenger]['recall'][str(k)]-values[baseline]['recall'][str(k)]) if q['answerable'] else None) for k in KS}
            comparisons.append(dict(corpus=corpus, id=q['id'], question=q['question'], type=q['type'],
                                    answerable=q['answerable'], configurations=values, deltas=deltas))
            for e in q['evidence']:
                source = ROOT/'docs'/('kestrel' if corpus == 'kestrel' else '')/e['source']
                text = source.read_text(encoding='utf-8-sig')
                assert e['quote'] in text
                annotations.append(dict(corpus=corpus, question_id=q['id'], source=e['source'], quote=e['quote'],
                                        source_occurrences=text.count(e['quote']),
                                        wholly_contained_in_canonical_chunk=any(p['name'] == e['source'] and e['quote'] in p['text'] for p in canonical(corpus, reference['corpus_sha256']).values())))
    assert all(e['wholly_contained_in_canonical_chunk'] for e in annotations)
    return dict(schema_version=1, benchmark='V3 Phase 2.5', ks=list(KS),
                definitions=dict(hit_rate='Macro fraction of answerable questions with any annotated (source, literal quote) in the ranked prefix.',
                                 recall='Macro fraction of annotated gold source/quote pairs retrieved per answerable question. This is evidence-annotation recall, not answer completeness.',
                                 latency='Observed per-question retrieval_seconds, including on-demand indexing/loading; one observation per question/configuration.',
                                 p95='Nearest-rank percentile: sorted times[ceil(0.95*n)-1].',
                                 failures='Infrastructure/retriever exceptions, distinct from gold-evidence misses. All six CLI runs completed every expected question with ok/empty statuses.',
                                 unavailable='null: no answerable gold evidence, absent question type, or unavailable measurement; never fabricated as zero accuracy.'),
                verification=dict(expected_runs=6, completed_runs=len(runs), question_executions=len(per_question),
                                  exact_original_question_sets=True, compatible_canonical_ids=True,
                                  source_hashes_match=True, all_saved_metrics_recomputed=True,
                                  all_llm_calls_zero=True, all_gold_quotes_source_valid=True),
                runs=runs, questions=comparisons, annotation_checks=annotations)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=BASE)
    args = parser.parse_args()
    names = ['summary.json', 'comparison.csv', 'by_type.csv', 'per_question.csv']
    if any((args.output_dir/n).exists() for n in names):
        parser.error('Refusing to overwrite derived benchmark artifacts; use a new --output-dir.')
    summary = analyze()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir/'summary.json').open('x') as stream:
        json.dump(summary, stream, indent=2); stream.write('\n')
    fields = ['corpus', 'configuration', 'k', 'answerable', 'hits', 'hit_rate', 'recall', 'mean_latency_seconds', 'median_latency_seconds', 'retrieval_failures']
    with (args.output_dir/'comparison.csv').open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fields); writer.writeheader()
        for r in summary['runs']:
            for k in KS:
                m = r['overall'][str(k)]
                writer.writerow(dict(corpus=r['corpus'], configuration=r['configuration'], k=k, answerable=m['answerable'], hits=m['hits'], hit_rate=m['hit_rate'], recall=m['quote_recall'], mean_latency_seconds=r['latency']['mean_seconds'], median_latency_seconds=r['latency']['median_seconds'], retrieval_failures=r['retrieval_failures']))
    with (args.output_dir/'by_type.csv').open('x', newline='') as stream:
        writer = csv.writer(stream); writer.writerow(['corpus', 'configuration', 'type', 'questions', 'answerable', 'k', 'hit_rate', 'recall', 'mean_latency_seconds'])
        for r in summary['runs']:
            for typ, values in r['by_type'].items():
                for k in KS:
                    m = values['overall'][str(k)]
                    writer.writerow([r['corpus'], r['configuration'], typ, values['questions'], m['answerable'], k, m['hit_rate'], m['quote_recall'], values['latency']['mean_seconds']])
    with (args.output_dir/'per_question.csv').open('x', newline='') as stream:
        writer = csv.writer(stream); writer.writerow(['corpus', 'question_id', 'type', 'answerable', 'configuration', 'latency_seconds', *[f'hit@{k}' for k in KS], *[f'recall@{k}' for k in KS], 'evidence_first_ranks_within_10', 'retrieval_failures'])
        for q in summary['questions']:
            for label, p in q['configurations'].items():
                writer.writerow([q['corpus'], q['id'], q['type'], q['answerable'], label, p['latency_seconds'], *[p['hits'][str(k)] for k in KS], *[p['recall'][str(k)] for k in KS], json.dumps(p['evidence_first_ranks_within_10']), p['retrieval_failures']])
    print('Verified', summary['verification'])
    for r in summary['runs']:
        print(r['corpus'], r['configuration'], 'latency:', r['latency'], 'first:', r['first_question_seconds'], 'post-first:', r['post_first_latency'], 'empty:', r['empty_retriever_counts'])
    for q in summary['questions']:
        if q['answerable']:
            print(q['corpus'], q['id'], 'H@5/R@5:', {k: (v['hits']['5'], v['recall']['5']) for k, v in q['configurations'].items()})


if __name__ == '__main__':
    main()
