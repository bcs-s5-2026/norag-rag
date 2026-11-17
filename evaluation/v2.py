"""C7 evaluation, shared by CLI and HTTP. V1 evaluator and results stay intact."""
import argparse
import hashlib
import json
import os
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from rag_app.models import Settings
from rag_app.service import ROOT, EMBEDDING_MODEL, RagService, PipelineError

KS = (1, 3, 5, 10)
GRADING_RULES = {
    'correct': 'All expected facts supported by cited chunks; unanswerable question explicitly abstains.',
    'partial': 'Some expected facts supported, others omitted; no unsupported factual claims.',
    'wrong': 'Incorrect answer, or abstention on an answerable question; answering an unanswerable question is wrong.',
    'unsupported': 'An answerable response asserts facts that its cited chunks do not support.',
    'diagnosis': 'For an incorrect answer, all expected quotes retrieved => generation failure; missing quotes => retrieval failure (generation may also contribute).',
    'no_context': 'Flag true only if the no-context response supplies the expected factual answer. An abstention is not evidence of prior knowledge. Human review required.'}


def questions(corpus):
    if corpus not in ('kestrel', 'vellora'):
        raise PipelineError('Unknown evaluation corpus.', 400)
    return [json.loads(line) for line in (ROOT/'evaluation'/f'{corpus}.jsonl').read_text().splitlines() if line.strip()]


def corpus_dir(corpus):
    return ROOT/'docs'/'kestrel' if corpus == 'kestrel' else ROOT/'docs'


def no_context(question):
    load_dotenv(ROOT/'.env')
    key = os.getenv('GOOGLE_API_KEY', '')
    if not key or key == 'your_google_api_key_here':
        raise PipelineError('Set GOOGLE_API_KEY in .env for no-context checks.')
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key, base_url='https://generativelanguage.googleapis.com/v1beta/openai/', timeout=45, max_retries=0)
        response = client.chat.completions.create(model=os.getenv('GOOGLE_MODEL', 'gemini-3.5-flash-lite'),
            temperature=0, messages=[{'role':'system','content':'Answer the question from your own knowledge. If you do not know, say so. Do not invent facts.'},
                                     {'role':'user','content':question}])
        return response.choices[0].message.content
    except Exception as exc:
        raise PipelineError('No-context LLM unavailable (credentials, quota, model or network).') from exc


def metrics(rows, k):
    eligible = [r for r in rows if r['answerable']]
    return dict(answerable=len(eligible), hits=sum(r['hits'][str(k)] for r in eligible),
                hit_rate=sum(r['hits'][str(k)] for r in eligible)/len(eligible) if eligible else None,
                quote_recall=sum(r['quote_recall'][str(k)] for r in eligible)/len(eligible) if eligible else None)


def evaluate(service, corpus, settings, answers=False, check_no_context=False, no_context_fn=None, request_interval=0):
    dataset = questions(corpus)
    ids, hashes = {}, {}
    names = sorted(p.name for p in corpus_dir(corpus).glob('*.md')) if corpus == 'kestrel' else ['vellora-duo-espresso-machine.txt']
    for name in names:
        content = (corpus_dir(corpus)/name).read_bytes()
        ids[name] = service.upload(name, content)['id']
        hashes[name] = hashlib.sha256(content).hexdigest()
    rows = []
    retrieve_settings = settings.model_copy(update={'top_k':10})
    for q in dataset:
        evidence = service.retrieve(q['question'], list(ids.values()), retrieve_settings)
        row = dict(**q, retrieved=evidence, hits={}, quote_recall={}, grade=None, grade_notes=None,
                   no_context_correct=None)
        for k in KS:
            found = [any(p['document_id'] == ids[e['source']] and e['quote'] in p['text'] for p in evidence[:k]) for e in q['evidence']]
            row['hits'][str(k)] = any(found) if q['answerable'] else None
            row['quote_recall'][str(k)] = sum(found)/len(found) if found else None
        if answers:
            try:
                # Uses actual configured top-k; the saved ranking contains at least that many.
                row['response'] = service.ask(q['question'], list(ids.values()), settings)
            except PipelineError as exc:
                row['generation_error'] = str(exc)
            if request_interval:
                time.sleep(request_interval)
        if check_no_context:
            try:
                row['no_context_answer'] = (no_context_fn or no_context)(q['question'])
            except PipelineError as exc:
                row['no_context_error'] = str(exc)
            if request_interval:
                time.sleep(request_interval)
        rows.append(row)
    return dict(version=2, corpus=corpus, measured_at=datetime.now(timezone.utc).isoformat(),
                embedding_model=EMBEDDING_MODEL, generation_model=os.getenv('GOOGLE_MODEL', 'gemini-3.5-flash-lite') if answers or check_no_context else None,
                settings=settings.model_dump(), request_interval_seconds=request_interval, retrieval_depth=10, answers=answers, no_context=check_no_context,
                corpus_sha256=hashes, dataset_sha256=hashlib.sha256((ROOT/'evaluation'/f'{corpus}.jsonl').read_bytes()).hexdigest(),
                metric='HitRate@k: any expected source/quote found. Quote recall: fraction of expected source/quotes found, macro-averaged over answerable questions.',
                unanswerable_excluded=sum(not q['answerable'] for q in dataset), grading_rules=GRADING_RULES,
                overall={str(k):metrics(rows,k) for k in KS},
                by_type={t:{str(k):metrics([r for r in rows if r['type']==t],k) for k in KS} for t in sorted({r['type'] for r in rows})},
                results=rows)


def run(corpus, settings, answers=False, check_no_context=False):
    with tempfile.TemporaryDirectory(prefix='rag-v2-') as directory:
        return evaluate(RagService(directory), corpus, settings, answers, check_no_context, request_interval=6)


def save(result, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex
    path = directory/f'{run_id}.json'
    path.write_text(json.dumps(result, indent=2)+'\n')
    return run_id


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus', choices=['kestrel','vellora'], required=True)
    parser.add_argument('--chunk-size', type=int, default=800)
    parser.add_argument('--chunk-overlap', type=int, default=80)
    parser.add_argument('--top-k', type=int, default=5, help='Generation evidence depth; metrics always use 1/3/5/10.')
    parser.add_argument('--answers', action='store_true')
    parser.add_argument('--no-context', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    # Never overwrite frozen V1 evidence or an existing experiment silently.
    if args.output.exists():
        parser.error('Output already exists; choose a new result path.')
    result = run(args.corpus, Settings(chunk_size=args.chunk_size, chunk_overlap=args.chunk_overlap, top_k=args.top_k), args.answers, args.no_context)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result['overall'], indent=2))
    print(f'Saved {args.output}')


if __name__ == '__main__':
    main()
