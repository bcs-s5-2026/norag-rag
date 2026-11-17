"""Local BM25 retrieval with canonical chunks and atomic, portable JSON snapshots.

No embedding, database, credential, network or LLM dependency. Callers serialize
document mutations and builds (RagService uses its existing single-process lock).
"""
import hashlib
import json
import math
import os
import tempfile
from collections import Counter
from pathlib import Path

from .lexical import TOKENIZER_VERSION, tokens

INDEX_VERSION = 'bm25-canonical-v1'
K1 = 1.5
B = 0.75


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':')).encode('utf-8')).hexdigest()


class BM25Index:
    """Scores are local to this selected set of chunks, not global probabilities."""

    def __init__(self, rows, counts=None):
        self.rows = sorted(rows, key=lambda row: row['id'])
        if len({row['id'] for row in self.rows}) != len(self.rows):
            raise ValueError('Duplicate chunk IDs.')
        # Persisted counts are keyed by canonical ID, independent of input ordering.
        self.counts = ([Counter(tokens(row['text'])) for row in self.rows] if counts is None
                       else [Counter(counts[row['id']]) for row in self.rows])
        self.lengths = [sum(count.values()) for count in self.counts]
        self.average_length = sum(self.lengths) / len(self.rows) if self.rows else 0
        self.frequency = Counter()
        for count in self.counts:
            self.frequency.update(count.keys())

    def search(self, question, top_k):
        if type(top_k) is not int or top_k < 1:
            raise ValueError('top_k must be a positive integer.')
        terms = sorted(set(tokens(question)))
        if not terms or not self.average_length:
            return []
        n = len(self.rows)
        idfs = {term: math.log1p((n-self.frequency[term]+0.5) /
                                (self.frequency[term]+0.5)) for term in terms}
        scored = []
        for row, count, length in zip(self.rows, self.counts, self.lengths):
            normalizer = K1 * (1-B+B*length/self.average_length)
            score = sum(idfs[term]*count[term]*(K1+1)/(count[term]+normalizer)
                        for term in terms if count[term])
            if score > 0:
                scored.append((score, row))
        scored.sort(key=lambda item: (-item[0], item[1]['id']))
        return [dict(row, retriever='bm25', score=score, rank=rank)
                for rank, (score, row) in enumerate(scored[:top_k], 1)]

    def payload(self):
        return dict(rows=self.rows, counts={row['id']: dict(count)
                    for row, count in zip(self.rows, self.counts)})


def load_or_build(directory, document_ids, settings, rows, rebuild=False):
    """Load validated counts without retokenizing; rebuild absent/stale/corrupt files.

    Source IDs are hashes of decoded content. Comparing canonical source rows also
    detects changed metadata or mismatched snapshots. A payload digest detects disk
    corruption; it is an integrity check, not authentication against a local writer.
    """
    manifest = dict(version=INDEX_VERSION, tokenizer=TOKENIZER_VERSION, k1=K1, b=B,
                    documents=sorted(set(document_ids)), chunk_size=settings.chunk_size,
                    chunk_overlap=settings.chunk_overlap)
    fingerprint = digest(manifest)
    directory = Path(directory)
    path = directory / f'{fingerprint}.json'
    canonical = sorted(rows, key=lambda row: row['id'])
    index = None
    if not rebuild:
        try:
            saved = json.loads(path.read_text(encoding='utf-8'))
            payload = saved['payload']
            counts = payload['counts']
            if (saved['manifest'] == manifest and saved['sha256'] == digest(payload)
                    and payload['rows'] == canonical
                    and set(counts) == {row['id'] for row in canonical}
                    and all(isinstance(count, dict) and
                            all(isinstance(term, str) and term and type(n) is int and n > 0
                                for term, n in count.items()) for count in counts.values())):
                index = BM25Index(canonical, counts)
        except (FileNotFoundError, ValueError, KeyError, TypeError, AttributeError):
            # Missing or malformed snapshots are disposable; storage I/O errors
            # propagate to the service rather than pretending a build succeeded.
            pass
    built = index is None
    if built:
        index = BM25Index(canonical)
        payload = index.payload()
        saved = dict(manifest=manifest, payload=payload, sha256=digest(payload))
        directory.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=directory,
                                             suffix='.tmp', delete=False) as stream:
                temporary = Path(stream.name)
                json.dump(saved, stream, ensure_ascii=False, sort_keys=True)
                stream.write('\n')
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    return index, dict(index=fingerprint, documents=len(manifest['documents']),
                       chunks=len(index.rows), rebuilt=built)
