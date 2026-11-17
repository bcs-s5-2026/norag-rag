"""Kestrel graph build/resume/inspection CLI. No retrieval or fusion."""
import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from .graph_build import GraphBuilder, GraphConfig, GraphError, atomic_json
from .models import Settings


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['plan', 'build', 'resume', 'inspect', 'export'])
    parser.add_argument('--data-dir', type=Path)
    parser.add_argument('--chunk-size', type=int, default=800)
    parser.add_argument('--chunk-overlap', type=int, default=80)
    parser.add_argument('--model', default='gemini-3.5-flash-lite')
    parser.add_argument('--max-output-tokens', type=int, default=4096)
    parser.add_argument('--recipe', choices=['v1', 'v2'], default='v1', help='v2: heading context, few-shot prompt, per-triple validation (separate build/cache).')
    parser.add_argument('--pace', type=float, default=0.0, help='Seconds to wait between provider calls (rate limits).')
    parser.add_argument('--backoff', type=float, default=0.0, help='On rate-limit/5xx errors wait backoff*n seconds and continue (max 3 in a row) instead of halting.')
    parser.add_argument('--out', type=Path, help='export: directory for the portable graph bundle.')
    parser.add_argument('--aliases', type=Path, help='Local evidence-backed alias declarations (JSON array).')
    parser.add_argument('--max-calls', type=int, default=43, help='Lifetime reserved call budget for this build ID, hard maximum 43.')
    parser.add_argument('--max-attempts', type=int, default=2, help='Lifetime attempts per chunk for this build ID.')
    parser.add_argument('--dry-run', action='store_true', help='Plan only: no provider, directory creation or calls.')
    parser.add_argument('--approve-external', action='store_true', help='Explicitly authorize the displayed Google model/payload and call budget. Never inferred from an API key.')
    parser.add_argument('--cache-only', action='store_true', help='Assemble valid cached extractions without external calls.')
    parser.add_argument('--estimate-output', type=Path, help='Save the local dry-run estimate as JSON.')
    parser.add_argument('--build-id', help='Inspect a specific stored graph build.')
    parser.add_argument('--graph-path', type=Path, help='Inspect an exported local graph snapshot (inspect only).')
    parser.add_argument('--full', action='store_true', help='Inspect the complete stored graph including provenance.')
    args = parser.parse_args(argv)
    try:
        if args.graph_path is not None:
            if args.command != 'inspect':
                raise GraphError('--graph-path is for offline inspection only.')
            from .graph_retrieval import GraphIndex
            graph = GraphIndex.load(args.graph_path).graph
            print(json.dumps(graph if args.full else dict(build_id=graph['build_id'], complete=graph['complete'],
                             coverage=graph['coverage'], entities=len(graph['entities']), relations=len(graph['relations']),
                             build_stats=graph['build_stats']), indent=2, ensure_ascii=False))
            return 0
        aliases = json.loads(args.aliases.read_text()) if args.aliases else []
        builder = GraphBuilder(data_dir=args.data_dir,
                     config=GraphConfig(model=args.model, max_output_tokens=args.max_output_tokens, recipe=args.recipe),
                     settings=Settings(chunk_size=args.chunk_size, chunk_overlap=args.chunk_overlap), aliases=aliases)
        if args.command == 'export':
            if args.out is None:
                raise GraphError('export needs --out DIRECTORY.')
            print(json.dumps(export(builder, args.out), indent=2)); return 0
        if args.command == 'inspect' and not args.dry_run:
            graph = builder.inspect(args.build_id)
            result = graph if args.full else dict(build_id=graph['build_id'], complete=graph['complete'],
                      entities=len(graph['entities']), relations=len(graph['relations']),
                      provenance=len(graph['provenance']), merge_decisions=len(graph['merge_decisions']),
                      pending=graph['pending'], build_stats=graph['build_stats'], last_run=graph['last_run'])
            print(json.dumps(result, indent=2, ensure_ascii=False)); return 0
        plan = builder.plan(args.max_calls, args.max_attempts)
        if args.estimate_output:
            if args.estimate_output.exists():
                raise GraphError('Estimate output exists; choose a new filename.')
            atomic_json(args.estimate_output, plan)
        print(json.dumps(plan, indent=2, ensure_ascii=False))
        if args.command == 'plan' or args.dry_run:
            return 0
        graph = builder.build(approved=args.approve_external, max_calls=args.max_calls,
                              max_attempts=args.max_attempts, cache_only=args.cache_only, pace=args.pace, backoff=args.backoff)
        print(json.dumps(dict(build_id=graph['build_id'], complete=graph['complete'],
                              entities=len(graph['entities']), relations=len(graph['relations']),
                              pending=graph['pending'], build_stats=graph['build_stats']), indent=2))
        return 0 if graph['complete'] else 2
    except (GraphError, ValidationError, OSError, ValueError, KeyError, TypeError) as exc:
        parser.error(str(exc))


def export(builder, out):
    """Copy the stored build (graph, manifest, attempts, cache entries, quarantine) into a
    portable, committable bundle. Local only: no provider call."""
    from .graph_build import read_json
    graph = builder.inspect()
    out = Path(out)
    atomic_json(out/'graph.json', graph)
    attempts = builder.attempts()
    atomic_json(out/'attempts.json', sorted(attempts, key=lambda a: a['started_at']))
    keys = {builder.cache_key(row) for row in builder.rows}
    for path in sorted((builder.root/'cache').glob('*.json')):
        if path.stem in keys:
            atomic_json(out/'extraction_cache'/path.name, read_json(path))
    ids = {a['id'] for a in attempts}
    rejected = [read_json(p) for p in sorted((builder.root/'quarantine').glob('*.json')) if p.stem in ids]
    atomic_json(out/'validation_rejections.json', rejected)
    dropped = [dict(chunk_id=e['chunk']['id'], items=e['dropped_items'])
               for e in (read_json(p) for p in sorted((out/'extraction_cache').glob('*.json'))) if e.get('dropped_items')]
    atomic_json(out/'dropped_items.json', dropped)
    return dict(out=str(out), build_id=graph['build_id'], complete=graph['complete'], entities=len(graph['entities']),
                relations=len(graph['relations']), attempts=len(attempts), rejected_responses=len(rejected),
                chunks_with_dropped_items=len(dropped))


if __name__ == '__main__':
    raise SystemExit(main())
