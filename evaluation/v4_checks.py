"""V4 checks: concept map explorer (Part B) and personal data redaction (Part C).

    python -m evaluation.v4_checks offline --output evaluation/results/v4/offline.json
    python -m evaluation.v4_checks live --approve-external --output evaluation/results/v4/live.json

"offline" makes no LLM call. "live" asks a few fixed questions with the real
Gemini model (one call each) and saves what the traces recorded.
"""
import argparse
import json
import statistics
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from rag_app.models import RetrievalConfig, Settings
from rag_app.redaction import Redactor
from rag_app.service import ROOT, RagService

KESTREL = sorted((ROOT / 'docs' / 'kestrel').glob('*.md'))

# (text, expected number of e-mails, expected number of phones). The last rows are
# known limits of pattern matching and are expected to be MISSED.
REDACTION_CASES = [
    ('Write to jane.doe@example.org please.', 1, 0),
    ('Two people: a@x.io and b@y.co.uk, then a@x.io again.', 2, 0),
    ('Call +33 6 12 34 56 78.', 0, 1),
    ('Call 06 12 34 56 78 or 06.12.34.56.78', 0, 2),
    ('US number (555) 123-4567 ext 12', 0, 1),
    ('Allow the IP 203.0.113.10 on the firewall.', 0, 0),
    ('Effective 2026-01-01, error KST-5031, 1,200 EUR.', 0, 0),
    ('My name is Sam Martin and I live in Paris.', 0, 0),          # names are not detected
    ('Mail me at sam (at) example (dot) org', 0, 0),               # obfuscated address: missed
    ('My number is zero six, twelve, thirty-four.', 0, 0),         # spelled-out phone: missed
    ('Short number 0612 3456', 0, 0),                              # 8 digits: below the 9-digit rule
]

LIVE_QUESTIONS = [
    ('two_hop', 'Error KST-5031 happened on the last two scheduled reports. Which team should support contact, and where?'),
    ('corpus_email', 'How do I request a refund, and where do I send the request?'),
    ('plain', 'Can I get a refund on my annual plan 45 days after it renewed?'),
    ('same_with_personal_data', 'My name is Sam Martin, my email is sam.martin@example.org and my phone is +33 6 12 34 56 78. '
                                'Can I get a refund on my annual plan 45 days after it renewed?'),
    ('not_in_corpus', 'Is there a Kestrel mobile app for iPhone?'),
    ('from_concept_service', 'What do the documents say about ledger?'),
    ('from_concept_hub', 'What do the documents say about Enterprise?'),
    ('from_concept_channel', 'What do the documents say about #oncall-payments?'),
]


def offline():
    with tempfile.TemporaryDirectory(prefix='rag-v4-') as directory:
        service = RagService(directory)
        sources = {path.name: path.read_text(encoding='utf-8') for path in KESTREL}
        concepts = service.concepts()
        rows, wrong_quotes = [], 0
        for concept in concepts:
            data = service.concept(concept['id'])
            proofs = data['mentions'] + [e for link in data['links'] for e in link['evidence']]
            # A quote is correct when the course document has exactly this text at these offsets.
            bad = sum(sources[p['document']][p['quote_start']:p['quote_end']] != p['quote'] for p in proofs)
            wrong_quotes += bad
            rows.append(dict(label=concept['label'], type=concept['type'], links=len(data['links']),
                             links_with_condition=sum(link['condition'] is not None for link in data['links']),
                             mentions=len(data['mentions']), quotes_checked=len(proofs), quotes_wrong=bad))
        lookups = [t for t in service.traces.all() if t['kind'] == 'concept']
        durations = sorted(t['duration_ms'] for t in lookups)
        concept_map = dict(concepts=len(concepts), links_seen_from_both_ends=sum(r['links'] for r in rows),
                           quotes_checked=sum(r['quotes_checked'] for r in rows), quotes_wrong=wrong_quotes,
                           most_links=max(rows, key=lambda r: r['links']),
                           fewest_links=min(rows, key=lambda r: r['links']),
                           links_with_condition=sum(r['links_with_condition'] for r in rows) // 2,
                           lookup_ms_median=statistics.median(durations), lookup_ms_max=durations[-1],
                           llm_calls=sum(t['llm_calls'] for t in lookups), per_concept=rows)
    cases = []
    for text, emails, phones in REDACTION_CASES:
        redactor = Redactor()
        redacted = redactor.redact(text)
        cases.append(dict(text=text, redacted=redacted, found=redactor.counts(),
                          expected=dict(emails=emails, phones=phones),
                          as_expected=redactor.counts() == dict(emails=emails, phones=phones)))
    corpus = {}
    for path in KESTREL + [ROOT / 'docs' / 'vellora-duo-espresso-machine.txt']:
        redactor = Redactor()
        redactor.redact(path.read_text(encoding='utf-8'))
        corpus[path.name] = dict(redactor.counts(), values=sorted(redactor.placeholders))
    return dict(kind='v4-offline-checks', measured_at=datetime.now(timezone.utc).isoformat(),
                concept_map=concept_map, redaction_cases=cases, redaction_on_corpora=corpus)


def live():
    settings = Settings()
    retrieval = RetrievalConfig(retrievers=['dense', 'bm25', 'graph'])
    rows = []
    with tempfile.TemporaryDirectory(prefix='rag-v4-') as directory:
        service = RagService(directory)
        ids = [service.upload(path.name, path.read_bytes())['id'] for path in KESTREL]
        service.index_run(ids, settings)  # so that question timings exclude indexing
        for label, question in LIVE_QUESTIONS:
            row = dict(case=label)
            try:
                answer = service.ask_configured(question, ids, settings, retrieval)
                row.update(answer=answer['answer'], citations=answer['citations'])
            except Exception as exc:
                row['error'] = str(exc)
            trace = service.traces.recent(1, 'question')[0]
            trace = service.traces.get(trace['id'])
            spans = {s['name']: s for s in trace['spans']}
            row.update(question_as_traced=trace['attributes']['question'], outcome=trace['outcome'],
                       duration_ms=trace['duration_ms'], llm_calls=trace['llm_calls'],
                       input_tokens=trace['input_tokens'], output_tokens=trace['output_tokens'],
                       cost_usd=trace['cost_usd'],
                       redacted=spans['redact']['attributes'] if 'redact' in spans else None,
                       invented_contacts_removed=spans.get('validate', {}).get('attributes', {}).get('invented_contacts_removed'),
                       step_ms={name: span['duration_ms'] for name, span in spans.items()})
            rows.append(row)
        stored = (Path(directory) / 'traces' / 'traces.jsonl').read_text(encoding='utf-8')
        indexing = [t for t in service.traces.all() if t['kind'] == 'indexing']
    known = [r for r in rows if r['cost_usd'] is not None]
    return dict(kind='v4-live-checks', measured_at=datetime.now(timezone.utc).isoformat(),
                settings=settings.model_dump(), retrieval=retrieval.model_dump(),
                totals=dict(questions=len(rows), llm_calls=sum(r['llm_calls'] for r in rows),
                            input_tokens=sum(r['input_tokens'] for r in known),
                            output_tokens=sum(r['output_tokens'] for r in known),
                            cost_usd=round(sum(r['cost_usd'] for r in known), 6)),
                personal_data_found_in_trace_file=[v for v in ('sam.martin@example.org', '+33 6 12 34 56 78',
                                                               'billing@kestrel.example') if v in stored],
                indexing_run=dict(duration_ms=indexing[0]['duration_ms'], attributes=indexing[0]['attributes'],
                                  llm_calls=indexing[0]['llm_calls']),
                results=rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('mode', choices=['offline', 'live'])
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--approve-external', action='store_true',
                        help='Required for "live": sends 8 questions and Kestrel chunks to Gemini.')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output already exists; choose a new result path.')
    if args.mode == 'live' and not args.approve_external:
        parser.error('"live" calls the hosted LLM. Add --approve-external to confirm.')
    result = offline() if args.mode == 'offline' else live()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    print(f'Saved {args.output}')


if __name__ == '__main__':
    main()
