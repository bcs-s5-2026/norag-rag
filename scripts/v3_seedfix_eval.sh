#!/usr/bin/env bash
# Re-run the Kestrel evaluation after the case-sensitive seed fix (no LLM calls, ~1 min).
set -uo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
OUT=evaluation/results/v3/graph_v2_seedfix_2026-11-08
mkdir -p "$OUT"; cp evaluation/results/v3/graph_v2_final_2026-11-08/analyze.py "$OUT/"
G=(--graph-path concepts/kestrel_graph_v2/graph.json)
run() { local name=$1; shift
  [ -f "$OUT/$name.json" ] || $PY -m evaluation.v3 --question-set v3 --top-k 5 --rrf-k 60 --output "$OUT/$name.json" "$@" > /dev/null 2>&1 \
    && echo "ok $name" || echo "FAILED $name"; }
run kestrel-dense                --corpus kestrel --retrievers dense --candidate-depth 20
run kestrel-dense-bm25           --corpus kestrel --retrievers dense bm25 --candidate-depth 20
run kestrel-graph                --corpus kestrel --retrievers graph --candidate-depth 20 "${G[@]}"
run kestrel-dense-graph          --corpus kestrel --retrievers dense graph --candidate-depth 20 "${G[@]}"
run kestrel-dense-bm25-graph     --corpus kestrel --retrievers dense bm25 graph --candidate-depth 20 "${G[@]}"
run kestrel-dense-bm25-graph-d40 --corpus kestrel --retrievers dense bm25 graph --candidate-depth 40 "${G[@]}"
$PY -m pytest -q 2>&1 | tail -2
echo "=== seedfix done ==="
