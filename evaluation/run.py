"""Run with python -m evaluation.run; no LLM call or credentials required."""
import argparse
import hashlib
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from rag_app.models import Settings
from rag_app.service import EMBEDDING_MODEL, ROOT, RagService


def evaluate(service, settings, dataset):
    ids = {}
    hashes = {}
    for name in sorted({q['source'] for q in dataset if q['source']}):
        content = (ROOT / 'docs' / name).read_bytes()
        hashes[name] = hashlib.sha256(content).hexdigest()
        ids[name] = service.upload(name, content)['id']
    rows = []
    for q in dataset:
        evidence = service.retrieve(q['question'], list(ids.values()), settings)
        # Matching a verbatim source span survives changes to chunk boundaries.
        hit = any(e['document_id'] == ids.get(q['source']) and q['passage'] in e['text'] for e in evidence) if q['answerable'] else None
        rows.append(dict(**q, hit=hit, retrieved=[dict(id=e['id'], similarity=e['similarity']) for e in evidence]))
    answerable = sum(q['answerable'] for q in dataset)
    hits = sum(row['hit'] is True for row in rows)
    return dict(dataset_version=1, measured_at=datetime.now(timezone.utc).isoformat(),
                embedding_model=EMBEDDING_MODEL, settings=settings.model_dump(), corpus_sha256=hashes,
                dataset_sha256=hashlib.sha256(json.dumps(dataset, sort_keys=True).encode()).hexdigest(),
                metric='Hit@k: fraction of answerable questions with the full expected verbatim span in a retrieved chunk from the expected document',
                hits=hits, answerable_count=answerable, unanswerable_count=len(dataset)-answerable,
                hit_at_k=hits/answerable, results=rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--top-k', type=int, default=5)
    parser.add_argument('--chunk-size', type=int, default=800)
    parser.add_argument('--chunk-overlap', type=int, default=80)
    parser.add_argument('--output', type=Path, default=ROOT / 'evaluation' / 'baseline.json')
    args = parser.parse_args()
    settings = Settings(chunk_size=args.chunk_size, chunk_overlap=args.chunk_overlap, top_k=args.top_k)
    dataset = json.loads((ROOT / 'evaluation' / 'questions.json').read_text())
    with tempfile.TemporaryDirectory(prefix='rag-evaluation-') as directory:
        result = evaluate(RagService(directory), settings, dataset)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(f"Hit@{settings.top_k}: {result['hits']}/{result['answerable_count']} = {result['hit_at_k']:.3f}")
    print(f"Unanswerable questions (excluded): {result['unanswerable_count']}")


if __name__ == '__main__':
    main()
