"""Append-only V3 question loading. Frozen V2 JSONL is never rewritten."""
import hashlib
import json
from pathlib import Path

from evaluation.v2 import questions
from rag_app.service import ROOT


def load(corpus, question_set='v2'):
    if question_set not in ('v2', 'v3'):
        raise ValueError('Unknown question set version.')
    rows = questions(corpus)
    paths = [ROOT/'evaluation'/f'{corpus}.jsonl']
    if question_set == 'v3' and corpus == 'kestrel':
        paths.append(ROOT/'evaluation/kestrel-v3-additions.jsonl')
        rows += [json.loads(x) for x in paths[-1].read_text().splitlines() if x.strip()]
    if len({q['id'] for q in rows}) != len(rows):
        raise ValueError('Duplicate question IDs in augmented set.')
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    fingerprint = (next(iter(hashes.values())) if len(paths) == 1 else
                   hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest())
    return rows, hashes, fingerprint
