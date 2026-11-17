#!/usr/bin/env bash
# V3 graph rebuild (recipe v2) + evaluation. Run from the repo root on your machine:
#   bash scripts/v3_graph_v2.sh
# Sends the 43 Kestrel chunks to the Gemini API (approved by Feras M, 2026-11-08), at most 90 calls.
set -uo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
OUT=evaluation/results/v3/graph_v2_final_2026-11-08
BUNDLE=concepts/kestrel_graph_v2
LOG=reports/V3_GRAPH_V2_RUN.log
mkdir -p reports "$OUT"
exec > >(tee -a "$LOG") 2>&1
echo "=== $(date -u +%FT%TZ) V3 graph v2 run ==="

# 1. Pick the model (metadata GET only, no generation).
if [ -n "${GRAPH_MODEL:-}" ]; then MODEL=$GRAPH_MODEL; else
MODEL=$($PY - <<'PYEOF'
import os, requests
from dotenv import load_dotenv
load_dotenv('.env')
key = os.environ['GOOGLE_API_KEY']
for name in ('gemini-3.6-flash', 'gemini-3.5-flash', 'gemini-3.5-flash-lite'):
    r = requests.get(f'https://generativelanguage.googleapis.com/v1beta/models/{name}', params={'key': key}, timeout=20)
    if r.status_code == 200:
        print(name); break
else:
    raise SystemExit('No Gemini flash model available for this key')
PYEOF
) || { echo "Model check failed (key or network)"; exit 1; }
fi
echo "Model: $MODEL"

COMMON=(--recipe v2 --model "$MODEL" --max-output-tokens 8192 --max-calls 90 --max-attempts 3)
# 2. Dry-run plan (no calls), saved for the report.
[ -f reports/V3_GRAPH_V2_PLAN.json ] || $PY -m rag_app.graph plan "${COMMON[@]}" --estimate-output reports/V3_GRAPH_V2_PLAN.json > /dev/null

# 3. Build; resume up to 3 times after rate-limit/timeouts (cache is reused, budget is lifetime).
for attempt in 1 2 3 4; do
  $PY -m rag_app.graph build "${COMMON[@]}" --approve-external --pace 8 --backoff 30 | tail -25
  code=${PIPESTATUS[0]}
  [ "$code" = 0 ] && break
  echo "Build returned $code (partial). Waiting 90s then resuming ($attempt/3)..."; sleep 90
done

# 4. Export a portable, committable bundle.
$PY -m rag_app.graph export "${COMMON[@]}" --out "$BUNDLE" || exit 1

# 4b. Random 10-triple sample for YOUR manual grading (blank sheet, nothing pre-filled).
REVIEW=evaluation/graph_review/kestrel-v2-10-triples-ungraded.json
[ -f "$REVIEW" ] || $PY -m rag_app.graph_review prepare --graph-path "$BUNDLE/graph.json" --output "$REVIEW"

# 5. Evaluation (retrieval only, no LLM calls). Same v3 question set as the submission run.
run() { local name=$1; shift
  [ -f "$OUT/$name.json" ] || $PY -m evaluation.v3 --question-set v3 --top-k 5 --rrf-k 60 --output "$OUT/$name.json" "$@" > /dev/null \
    && echo "ok $name" || echo "FAILED $name"; }
G=(--graph-path "$BUNDLE/graph.json")
run kestrel-dense                --corpus kestrel --retrievers dense --candidate-depth 20
run kestrel-bm25                 --corpus kestrel --retrievers bm25 --candidate-depth 20
run kestrel-dense-bm25           --corpus kestrel --retrievers dense bm25 --candidate-depth 20
run kestrel-graph                --corpus kestrel --retrievers graph --candidate-depth 20 "${G[@]}"
run kestrel-dense-graph          --corpus kestrel --retrievers dense graph --candidate-depth 20 "${G[@]}"
run kestrel-dense-bm25-graph     --corpus kestrel --retrievers dense bm25 graph --candidate-depth 20 "${G[@]}"
run kestrel-dense-bm25-graph-d40 --corpus kestrel --retrievers dense bm25 graph --candidate-depth 40 "${G[@]}"
run kestrel-dense-bm25-graph-v1  --corpus kestrel --retrievers dense bm25 graph --candidate-depth 20 --graph-path concepts/kestrel_graph/graph.json
run vellora-dense                --corpus vellora --retrievers dense --candidate-depth 20
run vellora-bm25                 --corpus vellora --retrievers bm25 --candidate-depth 20
run vellora-dense-bm25           --corpus vellora --retrievers dense bm25 --candidate-depth 20

# 6. Tests.
$PY -m pytest -q 2>&1 | tail -3
echo "=== done. Tell Claude it finished. ==="
