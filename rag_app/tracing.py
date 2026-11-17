"""V4 Part A: one trace per question, indexing run or concept lookup.

A trace is a small dictionary with one span per pipeline step. Traces are
appended to a local JSON-lines file (data/traces/traces.jsonl) and never leave
the machine. They hold chunk ids, counts, timings, tokens and cost; they never
hold API keys, chunk text or answers. The question is stored after redaction.
"""
import json
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock

KEEP_DAYS = 30


def llm_cost(model, input_tokens, output_tokens):
    """USD cost of one LLM call, or None when the price or the usage is unknown."""
    from .graph_build import PRICES  # same price table as the V3 graph build
    prices = PRICES.get(model)
    if prices is None or input_tokens is None or output_tokens is None:
        return None
    return round((input_tokens * prices[0] + output_tokens * prices[1]) / 1e6, 8)


class Trace:
    def __init__(self, kind, **attributes):
        self.id = uuid.uuid4().hex
        self.kind = kind  # 'question', 'indexing' or 'concept'
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.attributes = attributes
        self.spans = []
        self.outcome = 'error'  # replaced when the request completes
        self.error = None
        self._clock = time.perf_counter()

    @contextmanager
    def span(self, name, **attributes):
        """Time one step. The caller adds what happened to the yielded dict."""
        started = time.perf_counter()
        span = dict(name=name, offset_ms=round((started - self._clock) * 1000, 2),
                    status='ok', attributes=attributes)
        self.spans.append(span)
        try:
            yield attributes
        except Exception as exc:
            # Only the exception type: a library message could quote document text.
            span['status'] = 'error'
            span['error'] = type(exc).__name__
            raise
        finally:
            span['duration_ms'] = round((time.perf_counter() - started) * 1000, 2)

    def to_dict(self):
        def total(key):
            values = [s['attributes'][key] for s in self.spans if s['attributes'].get(key) is not None]
            return sum(values) if values else None
        return dict(id=self.id, kind=self.kind, started_at=self.started_at,
                    duration_ms=round((time.perf_counter() - self._clock) * 1000, 2),
                    outcome=self.outcome, error=self.error, attributes=self.attributes,
                    llm_calls=total('llm_calls') or 0, input_tokens=total('input_tokens'),
                    output_tokens=total('output_tokens'), cost_usd=total('cost_usd'),
                    spans=self.spans)


class TraceStore:
    def __init__(self, directory):
        self.path = Path(directory) / 'traces.jsonl'
        self.lock = Lock()

    def save(self, trace):
        line = json.dumps(trace.to_dict(), ensure_ascii=False)
        with self.lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open('a', encoding='utf-8') as stream:
                stream.write(line + '\n')

    def all(self):
        if not self.path.exists():
            return []
        with self.lock:
            lines = self.path.read_text(encoding='utf-8').splitlines()
        return [json.loads(line) for line in lines if line.strip()]

    def get(self, trace_id):
        return next((t for t in self.all() if t['id'] == trace_id), None)

    def recent(self, limit=20, kind=None):
        """Newest first, without the spans (a short list for the UI)."""
        rows = [t for t in self.all() if kind is None or t['kind'] == kind]
        return [{k: v for k, v in t.items() if k != 'spans'} for t in reversed(rows[-limit:])]

    def prune(self, keep_days=KEEP_DAYS):
        """Drop traces older than keep_days. Called once when the app starts."""
        traces = self.all()
        limit = (datetime.now(timezone.utc) - timedelta(days=keep_days)).isoformat()
        kept = [t for t in traces if t['started_at'] >= limit]
        if len(kept) != len(traces):
            with self.lock:
                temporary = self.path.with_suffix('.tmp')
                temporary.write_text(''.join(json.dumps(t, ensure_ascii=False) + '\n' for t in kept),
                                     encoding='utf-8')
                temporary.replace(self.path)
        return len(traces) - len(kept)
