# V3 final integration and measured results

> **Historical scope:** this document records an earlier V3 phase or the first graph. For the current recipe-v2 graph, completed 10-of-39 review, final metrics, existing release tag and latest checks, use [V3_SUBMISSION_AUDIT.md](V3_SUBMISSION_AUDIT.md) and the “V3 final” section of [REPORT.md](../REPORT.md). Earlier pending or incomplete statements below are historical, not the current submission status.

> **Superseded (8 Nov 2026, afternoon).** This file describes the first, partial v1 graph (gemini-3.5-flash-lite, 10 relations). The submitted V3 results, rebuilt graph (`concepts/kestrel_graph_v2/`) and the extraction-quality review (`evaluation/graph_review/kestrel-v2-10-triples.json`) are in REPORT.md, section "V3 final". The v1 grades below were AI-drafted reasons confirmed in chat, not an independent review.


Date: 8 November 2026. All changes are local and uncommitted. Earlier phase reports preserve their historical state; this report records the approved extraction and final integration.

## Extraction and scope

Only the five allowlisted `docs/kestrel/*.md` files and extraction instructions/schema, filenames, content/chunk hashes, offsets and line metadata were used as model inputs. Credentials were used solely for API authentication; no credentials, original evaluation questions, Vellora files, reports or unrelated local files were prompt inputs. Provider/model remained Google Gemini Developer API / `gemini-3.5-flash-lite`. The explicit approval and original build identity are preserved in `reports/V3_EXTRACTION_APPROVAL.json` and `V3_PHASE3_APPROVAL_PLAN.json`.

Exactly **43 request attempts across all resumes**, one per canonical chunk, exhausted the hard lifetime budget. The durable ledger reserves before dispatch; SDK retries are disabled, and provider errors halt dispatch rather than falling back or automatically changing models. Controlled resumes retained the identity/ledger and prioritized untouched chunks. The final verification confirms 43 ledger records and zero remaining requests. No evaluation or integration generation calls were made.

Actual outcomes: **29 strict-valid responses, 27 of them empty; 10 validation rejections; 4 provider failures** (two timeouts, one server error, one rate-limit error). Strict raw output contains two relations. There were 19 raw candidate triples including quarantined output. Cumulative measured build-body latency was **237.465 seconds**. Known usage is **50,239 input / 1,845 output tokens**; usage for four failed calls is unknown. Known-usage estimated cost is **$0.0196842** at the approved $0.30/M input and $2.50/M output rates. This is neither the invoice total nor a complete spend estimate. Exact total tokens/cost are **unavailable**.

The earlier ~44k output-token estimate was 43 × 1,024 assumed tokens, not observed output or a minimum. The configured per-response cap was 4,096. Actual known output was much lower, largely because 27 strict-valid outputs were empty. The partial graph cannot be described as full successful extraction.

## Raw graph, offline derivative and integrity

Raw graph, rejected output, attempt records and original valid extraction cache are preserved under `concepts/kestrel_graph/`. The published `graph.json` is a disclosed offline derivative, not an unmodified successful model output. `rag_app/graph_context.py` recovered nine existing subject/relation/object proposals from six quarantined responses by expanding literal quotations within the same explicit subject heading and validating the predicate. Subject, object and relation were never changed; original quotes, attempt IDs, model response hashes and expansion annotations remain attached. No LLM calls were used for repair.

One strict-accepted `KST-3012 → ESCALATE_TO → Analytics Eng` relation was excluded because its object ended inside a continuing source word at a chunk boundary. No fuzzy rename was applied. A reversed `postroom → REPLACED_BY → mailman` candidate remains quarantined: the source says postroom replaced the older mailman. Quote membership alone cannot guarantee relation direction; validation plus review is necessary.

Published graph: **17 entities, 10 relations, complete=false**. Source offsets and quotations, graph/manifest checksums, endpoint typing, unique IDs, node/edge evidence references, and source-document IDs were verified. Published build ID: `529ee6bf820a7554a5d0352d10d92e39d6df992e0ae81f99c9a584c34e797794`. Raw approved build ID: `87e963bbdbd3d9f8ee9aa8954d7b6d9dbdd272eacc8e5cd20dc3af4221500ecb`.

Fixed entity/relation types and typed endpoints are defined in `rag_app/graph_schema.py`, with the rationale in the Phase 3 report. Conservative NFKC/case/whitespace and trivial punctuation normalization merges exact typed names; explicit evidence-backed aliases are supported. Three real merge decisions concern Platform, postroom and Analytics Engine. The cross-document postroom merge is supported by catalog/runbook evidence. The truncated Analytics Eng label demonstrates a deliberately unresolved identity, excluded rather than weakly merged. No real semantic-alias merge is claimed; alias behavior is covered by mocked tests.

Runtime construction storage is `data/graphs/`; exported graph retrieval defaults to `concepts/kestrel_graph/graph.json`. Restarting the application does not rebuild the graph. BM25 snapshots are `data/bm25/<fingerprint>.json` (or under `RAG_DATA_DIR`); valid snapshots load without re-tokenization. Missing/corrupt BM25 snapshots rebuild locally and expose that status. Content/settings/tokenizer-version changes select a fresh snapshot; deletion/selection filters prevent cross-corpus retrieval. No automatic model-based graph refresh occurs.

## Human review

Feras M explicitly supplied all ten grades and reasons: **10 correct, 0 wrong, 0 unsupported**. `evaluation/graph_review/kestrel-10-triples.json` and `.md` record the grades, reviewer and source evidence. The ungraded JSON is archived separately. Seed 20261108 selected ten relations without replacement from the ten-relation published graph; the order is random but the sample covers the entire retained population. This is **not raw extraction precision** or proof of coverage: invalid, empty, excluded and quarantined candidates are outside this population. Historical `human_reviewed:false` in repair metadata records derivation-time status; subsequent human judgment is recorded in the review artifact. Neither that metadata nor original quotations were rewritten.

## Architecture and decisions

| Files | Responsibility |
|---|---|
| `rag_app/graph_retrieval.py` | Frozen graph validation, entity/descriptor seeding, bounded traversal, canonical chunk ranking and traces. |
| `rag_app/graph_context.py`, `graph_review.py` | Auditable offline quotation-context repair and seeded human-review preparation. |
| `rag_app/fusion.py`, `models.py`, `service.py` | Any nonempty subset of dense/BM25/graph, validated settings, provenance and shared evidence-grounded answer path. |
| `rag_app/api.py` | Optional configured ask, retrieval-only V3 evaluation, measured-run discovery; legacy API retained. |
| `rag_app/static/{index.html,app.js,style.css}` | Retriever/settings controls, citation origins, graph path and full source inspection. |
| `evaluation/v3.py`, `v3_questions.py` | V2/V3 question selection, zero-LLM metrics, graph survival, source/dataset hashes. |
| `evaluation/kestrel-v3-additions.jsonl`, `kestrel-v3.jsonl` | Two append-only two-hop questions and combined submission view. |
| `tests/test_graph_retrieval.py`, `test_rrf.py` | Graph/integration/validation/fusion/legacy regression coverage. |

Graph traversal starts with exact word-boundary entity/alias matches (exact error codes take priority). If none exist, local IDF lexical scoring over entity labels and evidence supplies at most three seeds. Walks retain original edge direction and conditions, may follow an edge in reverse for connectivity, avoid cycles, stop at three edges, twelve neighbors per expansion and 200 expansions. Candidate scores sum unique path contributions `seed_score/(1+path_length)`; canonical chunk-ID ties are deterministic. Paths expose source chunks/quotations and final fused ranks. No gold labels or question-specific hand rules are used by retrieval.

Standard equal-weight RRF is `Σ 1/(k+rank)` for 1-based per-retriever ranks, default k=60. Canonical stable chunk IDs deduplicate votes and break ties. Candidate depth 20 and final top-k 5 are independent of metric prefixes 1/3/5/10. Dense, BM25 and graph remain independent components; unavailable enabled retrievers fail explicitly, never silently substitute another configuration. Partial graph coverage is exposed in the response and UI. Graph requires the original Kestrel source selection and frozen 800/80 settings; Vellora graph requests fail explicitly.

BM25 retains Unicode words, casefolds, preserves internal hyphens/apostrophes (including error codes), splits other punctuation, and applies no stemming or stopword removal. Snapshot fingerprints include source content, settings and tokenizer version; both corpora use the same canonical chunks as dense. Legacy dense requests/evaluation remain intact. No new dependencies or optional weighted fusion/path-context generation were introduced.

## Final measured retrieval

Nine final CLI runs succeeded: eight main corpus/configuration combinations plus one candidate-depth sensitivity run. Commands and raw-file checksums are in `evaluation/results/v3/submission_2026-11-08/run_manifest.json`. The local analyzer independently recomputed every literal evidence metric and verified question fields, corpus hashes, chunk IDs/offsets and zero evaluation LLM calls. Its `summary.json` contains overall, by-type, original-V2 slices, timing and per-question detail; `comparison.csv` contains every K. All runs have zero retrieval execution failures. Graph-enabled runs explicitly report partial graph status on all twelve Kestrel questions.

Kestrel V3 uses 12 questions (10 answerable), including appended q11/q12; Vellora uses the original 15 (12 answerable). Original q01–q10 and all original evidence are untouched. Unanswerable questions are excluded from hit/recall denominators. HitRate means any annotated quote is present; Recall is macro average of the fraction of annotated source/quote pairs retrieved, preserving V2 semantics. It is **annotation recall**, not exhaustive relevant-chunk recall. Alternate support and incomplete annotations can underestimate relevance; fixed character boundaries can split a gold quotation. Added same-file multi-hop questions are easier than cross-file q08 and do not prove broad graph reasoning.

Table entries are HitRate / Recall (percent). Mean latency includes first-use dense model loading; median is more representative of these sequential warm requests. Cold means across different processes are not a controlled speed comparison.

| Corpus / configuration | @1 | @3 | @5 | @10 | Mean / median ms | Failures |
|---|---:|---:|---:|---:|---:|---:|
| kestrel / dense | 60.0 / 35.8 | 80.0 / 71.7 | 90.0 / 75.0 | 100.0 / 95.0 | 535.44 / 12.96 | 0 |
| kestrel / bm25 | 50.0 / 25.0 | 80.0 / 55.8 | 80.0 / 55.8 | 90.0 / 77.5 | 2.92 / 2.42 | 0 |
| kestrel / dense-bm25 | 50.0 / 20.8 | 70.0 / 54.2 | 90.0 / 74.2 | 100.0 / 95.0 | 373.99 / 15.35 | 0 |
| kestrel / graph | 20.0 / 11.7 | 20.0 / 11.7 | 20.0 / 11.7 | 20.0 / 11.7 | 2.00 / 1.43 | 0 |
| kestrel / dense-bm25-graph | 30.0 / 14.2 | 70.0 / 42.5 | 90.0 / 70.8 | 100.0 / 95.0 | 373.97 / 16.92 | 0 |
| vellora / dense | 50.0 / 50.0 | 50.0 / 50.0 | 58.3 / 58.3 | 83.3 / 83.3 | 295.75 / 10.59 | 0 |
| vellora / bm25 | 66.7 / 66.7 | 91.7 / 91.7 | 91.7 / 91.7 | 91.7 / 91.7 | 2.55 / 2.17 | 0 |
| vellora / dense-bm25 | 58.3 / 58.3 | 75.0 / 75.0 | 91.7 / 91.7 | 91.7 / 91.7 | 303.26 / 13.20 | 0 |
| kestrel / dense-bm25-graph-depth40 | 30.0 / 14.2 | 60.0 / 32.5 | 70.0 / 50.8 | 100.0 / 95.0 | 436.24 / 18.38 | 0 |

### Results by question type

| Corpus / configuration / type | Answerable | @1 H/R % | @3 H/R % | @5 H/R % | @10 H/R % |
|---|---:|---:|---:|---:|---:|
| kestrel / dense / exact_identifier | 2 | 50.0 / 25.0 | 50.0 / 50.0 | 50.0 / 50.0 | 100.0 / 100.0 |
| kestrel / dense / not_in_corpus | 0 | unavailable (no answerable items) | unavailable (no answerable items) | unavailable (no answerable items) | unavailable (no answerable items) |
| kestrel / dense / split_answer | 2 | 100.0 / 62.5 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 |
| kestrel / dense / two_hop | 3 | 66.7 / 27.8 | 66.7 / 38.9 | 100.0 / 50.0 | 100.0 / 83.3 |
| kestrel / dense / versions | 2 | 0.0 / 0.0 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 |
| kestrel / dense / vocabulary | 1 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 |
| kestrel / bm25 / exact_identifier | 2 | 50.0 / 25.0 | 50.0 / 25.0 | 50.0 / 25.0 | 100.0 / 100.0 |
| kestrel / bm25 / not_in_corpus | 0 | unavailable (no answerable items) | unavailable (no answerable items) | unavailable (no answerable items) | unavailable (no answerable items) |
| kestrel / bm25 / split_answer | 2 | 50.0 / 25.0 | 100.0 / 62.5 | 100.0 / 62.5 | 100.0 / 62.5 |
| kestrel / bm25 / two_hop | 3 | 100.0 / 50.0 | 100.0 / 61.1 | 100.0 / 61.1 | 100.0 / 83.3 |
| kestrel / bm25 / versions | 2 | 0.0 / 0.0 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 |
| kestrel / bm25 / vocabulary | 1 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| kestrel / dense-bm25 / exact_identifier | 2 | 50.0 / 25.0 | 50.0 / 50.0 | 100.0 / 100.0 | 100.0 / 100.0 |
| kestrel / dense-bm25 / not_in_corpus | 0 | unavailable (no answerable items) | unavailable (no answerable items) | unavailable (no answerable items) | unavailable (no answerable items) |
| kestrel / dense-bm25 / split_answer | 2 | 100.0 / 37.5 | 100.0 / 62.5 | 100.0 / 62.5 | 100.0 / 100.0 |
| kestrel / dense-bm25 / two_hop | 3 | 66.7 / 27.8 | 66.7 / 38.9 | 100.0 / 72.2 | 100.0 / 83.3 |
| kestrel / dense-bm25 / versions | 2 | 0.0 / 0.0 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 |
| kestrel / dense-bm25 / vocabulary | 1 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 100.0 / 100.0 |
| kestrel / graph / exact_identifier | 2 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| kestrel / graph / not_in_corpus | 0 | unavailable (no answerable items) | unavailable (no answerable items) | unavailable (no answerable items) | unavailable (no answerable items) |
| kestrel / graph / split_answer | 2 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| kestrel / graph / two_hop | 3 | 66.7 / 38.9 | 66.7 / 38.9 | 66.7 / 38.9 | 66.7 / 38.9 |
| kestrel / graph / versions | 2 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| kestrel / graph / vocabulary | 1 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| kestrel / dense-bm25-graph / exact_identifier | 2 | 0.0 / 0.0 | 50.0 / 50.0 | 100.0 / 100.0 | 100.0 / 100.0 |
| kestrel / dense-bm25-graph / not_in_corpus | 0 | unavailable (no answerable items) | unavailable (no answerable items) | unavailable (no answerable items) | unavailable (no answerable items) |
| kestrel / dense-bm25-graph / split_answer | 2 | 50.0 / 12.5 | 100.0 / 37.5 | 100.0 / 62.5 | 100.0 / 100.0 |
| kestrel / dense-bm25-graph / two_hop | 3 | 66.7 / 38.9 | 100.0 / 50.0 | 100.0 / 61.1 | 100.0 / 83.3 |
| kestrel / dense-bm25-graph / versions | 2 | 0.0 / 0.0 | 50.0 / 50.0 | 100.0 / 100.0 | 100.0 / 100.0 |
| kestrel / dense-bm25-graph / vocabulary | 1 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 100.0 / 100.0 |
| vellora / dense / exact_identifier | 4 | 50.0 / 50.0 | 50.0 / 50.0 | 50.0 / 50.0 | 75.0 / 75.0 |
| vellora / dense / not_in_corpus | 0 | unavailable (no answerable items) | unavailable (no answerable items) | unavailable (no answerable items) | unavailable (no answerable items) |
| vellora / dense / other | 4 | 75.0 / 75.0 | 75.0 / 75.0 | 75.0 / 75.0 | 75.0 / 75.0 |
| vellora / dense / vocabulary | 4 | 25.0 / 25.0 | 25.0 / 25.0 | 50.0 / 50.0 | 100.0 / 100.0 |
| vellora / bm25 / exact_identifier | 4 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 |
| vellora / bm25 / not_in_corpus | 0 | unavailable (no answerable items) | unavailable (no answerable items) | unavailable (no answerable items) | unavailable (no answerable items) |
| vellora / bm25 / other | 4 | 50.0 / 50.0 | 75.0 / 75.0 | 75.0 / 75.0 | 75.0 / 75.0 |
| vellora / bm25 / vocabulary | 4 | 50.0 / 50.0 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 |
| vellora / dense-bm25 / exact_identifier | 4 | 75.0 / 75.0 | 75.0 / 75.0 | 100.0 / 100.0 | 100.0 / 100.0 |
| vellora / dense-bm25 / not_in_corpus | 0 | unavailable (no answerable items) | unavailable (no answerable items) | unavailable (no answerable items) | unavailable (no answerable items) |
| vellora / dense-bm25 / other | 4 | 50.0 / 50.0 | 75.0 / 75.0 | 75.0 / 75.0 | 75.0 / 75.0 |
| vellora / dense-bm25 / vocabulary | 4 | 50.0 / 50.0 | 75.0 / 75.0 | 100.0 / 100.0 | 100.0 / 100.0 |
| kestrel / dense-bm25-graph-depth40 / exact_identifier | 2 | 0.0 / 0.0 | 0.0 / 0.0 | 50.0 / 50.0 | 100.0 / 100.0 |
| kestrel / dense-bm25-graph-depth40 / not_in_corpus | 0 | unavailable (no answerable items) | unavailable (no answerable items) | unavailable (no answerable items) | unavailable (no answerable items) |
| kestrel / dense-bm25-graph-depth40 / split_answer | 2 | 50.0 / 12.5 | 100.0 / 37.5 | 100.0 / 62.5 | 100.0 / 100.0 |
| kestrel / dense-bm25-graph-depth40 / two_hop | 3 | 66.7 / 38.9 | 100.0 / 50.0 | 100.0 / 61.1 | 100.0 / 83.3 |
| kestrel / dense-bm25-graph-depth40 / versions | 2 | 0.0 / 0.0 | 50.0 / 50.0 | 50.0 / 50.0 | 100.0 / 100.0 |
| kestrel / dense-bm25-graph-depth40 / vocabulary | 1 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 100.0 / 100.0 |

### Per-question findings and fusion survival

Kestrel q01: dense and BM25 rank the gold support at 7; two-way fusion moves it to 5, an observed improvement. q05: dense places the lost-phone backup evidence first, but two-way fusion pushes it to 8, a hybrid regression. q08 remains at Recall@5=0.5 and Recall@10=0.5 because the Messaging on-call fact is missing from retrieved support and absent from this partial graph. No recovered q08 answer is claimed.

Added q11: Recall@5 is dense 1/3, BM25 2/3, two-way 2/3, graph 2/3 and three-way 2/3. Added q12: dense/BM25 2/3, two-way 1, graph 0 and three-way 2/3. Here descriptor fallback matches scheduler/query-engine report/PDF context rather than ledger; the graph vote promotes an unrelated catalog chunk and pushes the ledger support from fused rank 5 to 6. This is a concrete graph-fusion failure, not evidence that more retrievers always improve quality.

Vellora q05/E47, q07/E86, q09/counter and q11/unused-time evidence benefit from BM25 over dense. q01/water capacity remains missed at all measured prefixes for every configuration. BM25 and two-way both reach 11/12 HitRate/Recall@5; BM25 has better @3 and lower local latency, so BM25 is the provisional Vellora default. Dense remains the Kestrel default because its aggregate Recall@5 is highest, despite specific lexical gains elsewhere.

Across the twelve Kestrel questions, **12/18 graph chunk candidates survive at fused top-5 with depth 20**. Increasing candidate depth to 40 yields **17/18 survival**, but drops three-way Recall@5 from 70.8% to 50.8% (HitRate from 90% to 70%). More graph survival is not necessarily useful evidence. Retain depth 20; do not add weights or force graph output into the answer context. Raw graph scores are never compared to dense cosine or BM25 scores.

## Reproduction and regression

Exact nine CLI commands appear in `run_manifest.json`; all use the existing local MiniLM cache with `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1`. Example (choose a new output file; existing results are refused):

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/python -m evaluation.v3 \
  --corpus kestrel --question-set v3 --retrievers dense bm25 graph \
  --candidate-depth 20 --rrf-k 60 --top-k 5 \
  --output evaluation/results/v3/kestrel-review-new.json
.venv/bin/python evaluation/results/v3/submission_2026-11-08/analyze.py
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/python -m pytest -q
node --check rag_app/static/app.js
git diff --check
```

The analyzer is write-once: the shown command produced the saved summary; rerun `analyze()` via import for nonwriting verification when that summary exists. Final complete suite: **144 passed in 11.96 seconds**. This includes all four V2 dense baselines (Kestrel/Vellora × 800/80 and 500/100), recomputed with the original evaluator and configured dense evaluator and compared against frozen overall/by-type/per-question values and dataset/corpus hashes. New tests cover graph traversal/descriptor seeds/corpus isolation/corrupt or missing proof, standard fusion/provenance, configured answer single-snapshot behavior with mocked generation, API validation, append-only questions and conservative offline repairs. No live answer generation was tested.

Original document/question/result preservation was checked against the 42-file pre-task hash inventory: only the intentionally extended `evaluation/v3.py` differs; the other 41 files, including all original V1/V2 datasets/results and Phase 2.5 benchmark artifacts, are byte-identical. JavaScript syntax and Git whitespace checks passed. Automated HTTP/DOM-template checks cover controls and the hidden `/bm25` route; the exact required text remains unlinked from frontend pages. Interactive browser/responsive verification is **unavailable** because the computer-use host could not start and no browser runner is installed. No browser success is claimed.

## Submission boundary and limitations

Mandatory local implementation, graph human review and retrieval evaluation are complete within the approved extraction budget. Graph coverage remains partial, aggregate graph benefit is not demonstrated, four failed-call usage totals are unknown, and generated-answer quality for new hybrid modes has not been paid-evaluated. Existing V2 answer reviews remain historical evidence only. The JSON evaluator field `phase:2` is a retained historical label; version, explicit retriever list, question-set label and graph build ID identify these final integrated runs.

Do not claim 100% graph extraction accuracy or complete corpus coverage from the retained ten correct relations. Improving extraction would need a separately reviewed model/prompt/build and fresh explicit spending authorization; none is initiated. No extra graph features are required now. Tag `v3`, commit/push and the final submission email are pending explicit user approval. `reports/V3_SUBMISSION_DRAFT.md` is a local draft only.
