"""Small metrics page: numbers computed from the saved traces (data/traces/traces.jsonl).

Nothing new is recorded. Traces hold counts, timings, tokens and cost, never text,
so the page cannot show a question, an answer or a document.
"""
from collections import Counter, defaultdict


def percentile(values, share):
    if not values:
        return None
    ordered = sorted(values)
    return round(ordered[min(len(ordered) - 1, int(share * len(ordered)))], 1)


def average(values):
    return round(sum(values) / len(values), 1) if values else None


def summarize(traces):
    questions = [t for t in traces if t['kind'] == 'question']
    outcomes = Counter(t['outcome'] for t in questions)
    answered, abstained = outcomes['answered'], outcomes['abstained']
    steps = defaultdict(list)
    retrievers, unavailable, redactions = Counter(), 0, 0
    for trace in questions:
        for span in trace['spans']:
            steps[span['name']].append(span['duration_ms'])
            attrs = span['attributes']
            if span['name'] == 'redact':
                redactions += sum(v for v in attrs.values() if isinstance(v, int) and not isinstance(v, bool))
            if span['name'] == 'graph' and attrs.get('status') == 'unavailable':
                unavailable += 1
        for name in trace['attributes'].get('retrievers', []):
            retrievers[name] += 1
    graph_builds = [t for t in traces if t['kind'] == 'graph']
    days = Counter(t['started_at'][:10] for t in questions)

    def total(rows, key):
        values = [r[key] for r in rows if r.get(key) is not None]
        return sum(values) if values else 0
    durations = [t['duration_ms'] for t in questions]
    return dict(
        traces=len(traces), kinds=dict(Counter(t['kind'] for t in traces)),
        since=min((t['started_at'] for t in traces), default=None),
        questions=dict(total=len(questions), answered=answered, abstained=abstained,
                       invalid=outcomes['invalid'], errors=outcomes['error'],
                       abstention_rate=round(abstained / (answered + abstained), 3) if answered + abstained else None),
        latency_ms=dict(average=average(durations), p50=percentile(durations, 0.5), p95=percentile(durations, 0.95)),
        steps_ms={name: average(values) for name, values in steps.items()},
        retrievers=dict(retrievers), graph_unavailable=unavailable, redactions=redactions,
        llm=dict(calls=total(traces, 'llm_calls'), input_tokens=total(traces, 'input_tokens'),
                 output_tokens=total(traces, 'output_tokens'),
                 cost_usd=round(total(traces, 'cost_usd'), 6),
                 cost_questions_usd=round(total(questions, 'cost_usd'), 6),
                 cost_graphs_usd=round(total(graph_builds, 'cost_usd'), 6),
                 per_question_usd=round(total(questions, 'cost_usd') / len(questions), 6) if questions else None),
        graph_builds=dict(total=len(graph_builds), built=sum(t['outcome'] == 'built' for t in graph_builds),
                          partial=sum(t['outcome'] == 'partial' for t in graph_builds),
                          failed=sum(t['outcome'] == 'error' for t in graph_builds)),
        questions_per_day=dict(sorted(days.items())[-14:]),
        recent=[dict(duration_ms=t['duration_ms'], outcome=t['outcome']) for t in questions[-30:]])
