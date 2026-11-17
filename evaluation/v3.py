"""Retrieval-only V3 evaluation: dense, BM25 or plain RRF. Never calls an LLM."""
import argparse
import hashlib
import json
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

from evaluation.v2 import KS, corpus_dir, metrics, questions
from rag_app.models import RetrievalConfig, Settings
from rag_app.service import EMBEDDING_MODEL, ROOT, PipelineError, RagService


def evaluate(service, corpus, settings, retrieval, question_set='v2'):
    from evaluation.v3_questions import load
    dataset, dataset_files, dataset_hash = load(corpus, question_set)
    if 'graph' in retrieval.retrievers and corpus != 'kestrel':
        raise ValueError('Graph evaluation is available only for Kestrel.')
    depth = max(max(KS), settings.top_k)
    if retrieval.candidate_depth < depth:
        raise ValueError('Evaluation candidate depth must be at least max(10, final top-k).')
    ids, hashes = {}, {}
    paths = (sorted(corpus_dir(corpus).glob('*.md')) if corpus == 'kestrel'
             else [corpus_dir(corpus)/'vellora-duo-espresso-machine.txt'])
    for path in paths:
        content = path.read_bytes()
        ids[path.name] = service.upload(path.name, content)['id']
        hashes[path.name] = hashlib.sha256(content).hexdigest()
    rows = []
    for q in dataset:
        started = time.perf_counter()
        # One ranked snapshot supplies BOTH metrics and the final selected prefix.
        response = service.retrieve_configured(q['question'], list(ids.values()),
                     settings.model_copy(update={'top_k': depth}), retrieval)
        elapsed = time.perf_counter()-started
        evidence = response['results']
        row = dict(**q, retrieved=evidence, selected=evidence[:settings.top_k],
                   retrievers=response['retrievers'], hits={}, quote_recall={},
                   retrieval_seconds=elapsed, llm_calls=0, input_tokens=0, output_tokens=0)
        if 'graph_trace' in response:
            row['graph_trace'] = response['graph_trace']
            graph_ids = {p['id'] for p in evidence if 'graph' in p['origins']}
            row['graph_fusion'] = dict(graph_candidate_count=response['retrievers']['graph']['candidate_count'],
                                      found_in_fused_at_k={str(k): sum(p['id'] in graph_ids for p in evidence[:k]) for k in KS})
        for k in KS:
            found = [any(p['document_id'] == ids[e['source']] and e['quote'] in p['text']
                         for p in evidence[:k]) for e in q['evidence']]
            row['hits'][str(k)] = any(found) if q['answerable'] else None
            row['quote_recall'][str(k)] = sum(found)/len(found) if found else None
        rows.append(row)
    return dict(version=3, phase=2, corpus=corpus, measured_at=datetime.now(timezone.utc).isoformat(),
                embedding_model=EMBEDDING_MODEL if 'dense' in retrieval.retrievers else None,
                settings=settings.model_dump(), retrieval=retrieval.model_dump(), question_set=question_set,
                retrieval_depth=depth, answers=False, llm_calls=0,
                corpus_sha256=hashes,
                dataset_sha256=dataset_hash, dataset_files_sha256=dataset_files,
                metric='HitRate@k: any expected source/quote found. Recall@k: macro fraction of expected source/quotes found (quote_recall, unchanged V2 definition).',
                unanswerable_excluded=sum(not q['answerable'] for q in dataset),
                overall={str(k): metrics(rows, k) for k in KS},
                by_type={t: {str(k): metrics([r for r in rows if r['type'] == t], k) for k in KS}
                         for t in sorted({r['type'] for r in rows})}, results=rows)


def run(corpus, settings, retrieval, question_set='v2', graph_path=None):
    with tempfile.TemporaryDirectory(prefix='rag-v3-') as directory:
        return evaluate(RagService(directory, graph_path=graph_path), corpus, settings, retrieval, question_set)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus', choices=['kestrel', 'vellora'], required=True)
    parser.add_argument('--chunk-size', type=int, default=800)
    parser.add_argument('--chunk-overlap', type=int, default=80)
    parser.add_argument('--top-k', type=int, default=5,
                        help='Final selected prefix; metrics always retrieve at least 10, as in V2.')
    parser.add_argument('--retrievers', nargs='+', choices=['dense', 'bm25', 'graph'], default=['dense'])
    parser.add_argument('--question-set', choices=['v2', 'v3'], default='v2', help='V3 appends two Kestrel questions; V2 files remain frozen.')
    parser.add_argument('--graph-path', type=Path, help='Frozen local graph snapshot; never triggers extraction.')
    parser.add_argument('--candidate-depth', type=int, default=20, help='Candidates per enabled retriever.')
    parser.add_argument('--rrf-k', type=int, default=60, help='RRF rank constant (not final top-k).')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output.exists():
        parser.error('Output already exists; choose a new result path.')
    try:
        settings = Settings(chunk_size=args.chunk_size, chunk_overlap=args.chunk_overlap, top_k=args.top_k)
        retrieval = RetrievalConfig(retrievers=args.retrievers, candidate_depth=args.candidate_depth, rrf_k=args.rrf_k)
        if retrieval.candidate_depth < max(10, settings.top_k):
            raise ValueError('Evaluation candidate depth must be at least max(10, final top-k).')
        if args.question_set == 'v2' and args.graph_path is None:
            result = run(args.corpus, settings, retrieval)
        else:
            result = run(args.corpus, settings, retrieval, args.question_set, args.graph_path)
    except (ValidationError, ValueError, PipelineError, OSError) as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation also protects against a concurrent run choosing this name.
    with args.output.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result['overall'], indent=2))
    print(f'Saved {args.output}')


if __name__ == '__main__':
    main()
