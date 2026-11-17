"""Exact lexical inspection of selected chunks; no embedding/model calls."""
from collections import Counter

from .lexical import tokens
from .service import chunks


def analyze(service, ids, settings, question='', word=''):
    vocabulary = {}
    passages = []
    with service.lock:
        for doc_id in dict.fromkeys(ids):
            doc = service.read(doc_id)
            for start, end, text in chunks(doc['text'], settings):
                counts = Counter(tokens(text))
                passage = dict(id=f'{doc_id}:{start}:{end}', document_id=doc_id,
                               name=doc['name'], start=start, end=end,
                               line=doc['text'].count('\n', 0, start)+1, text=text)
                passages.append((passage, counts))
                for token, count in counts.items():
                    entry = vocabulary.setdefault(token, dict(word=token, occurrences=0, chunks=0))
                    entry['occurrences'] += count
                    entry['chunks'] += 1
    selected = list(dict.fromkeys(tokens(question)))
    if word:
        selected = list(dict.fromkeys(tokens(word)))
    matches = []
    for token in selected:
        matches.append(dict(word=token, present=token in vocabulary,
                            **{k: vocabulary.get(token, {}).get(k, 0) for k in ('occurrences', 'chunks')},
                            passages=[dict(**p, count=c[token]) for p, c in passages if c[token]]))
    return dict(chunk_count=len(passages), vocabulary=sorted(vocabulary.values(), key=lambda r: (-r['occurrences'], r['word'])),
                words=matches, counting='Occurrences in indexed windows; overlaps count again. No stemming or stopword removal.')
