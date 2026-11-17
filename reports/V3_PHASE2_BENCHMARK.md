# RAG V3 Phase 2.5: retrieval benchmark

Date: 7 November 2026 (Europe/Paris). Repository HEAD: `8e86a027eb45d528eba5a153fe9804015fda8fa8`, with the existing uncommitted Phase 1/2 implementation. This benchmark adds result artifacts and this report; it makes no application, dataset, corpus or existing evaluation-artifact edits.

## Findings and provisional default

All six required corpus/configuration combinations completed: **75 question/configuration executions, zero retrieval failures, zero LLM calls**. The original V2 sets were used exactly: Kestrel 10 questions (8 answerable), Vellora 15 (12 answerable). Regression tests after generating the benchmark: **94 passed in 13.94 seconds**.

For the current, explicitly selected corpora, the provisional recommendation is **dense for Kestrel; BM25 for Vellora**, at 800-character chunks, overlap 80 and final k=5. Kestrel dense and RRF both hit 7/8 questions, but dense has better Recall@5 (81.25% versus 71.875%), better all-annotated-evidence coverage (6/8 versus 5/8), and lower observed post-first-query latency. Vellora BM25 and RRF both hit 11/12, with equal 91.667% Recall@5; BM25 reaches 11/12 by k=3 versus RRF's 9/12 and is substantially cheaper in observed local latency.

If **one shared configuration** must be chosen before the graph, use **dense+BM25 RRF provisionally**: pooled over the 20 answerable questions it achieves Hit@5 18/20 (90%) and Recall@5 83.75%, versus dense 14/20 (70%) / 67.5% and BM25 17/20 (85%) / 76.25%. These are question-weighted pooled summaries, not an extra dataset or out-of-sample evidence. Selecting dense for Kestrel and BM25 for Vellora gives the same 18/20 hits and 87.5% pooled annotated Recall@5, but this corpus-specific policy is selected on these small benchmark sets and can overfit.

These are recommendations only. No application default, automatic routing, frontend or answer-generation behavior was changed. RRF is not a universal improvement: Kestrel q05 loses its top-5 evidence and q03 loses most of its top-5 annotated facts. No Concept Graph work was started.

## Inputs, protocol and artifacts

Read before executing: the professor's complete local V3 assignment PDF, `reports/V3_READINESS_AUDIT.md`, `reports/V3_PHASE1_BM25.md`, and `reports/V3_PHASE2_RRF.md`. The assignment's same-question comparison and k/type requirements guide this benchmark; its graph/submission instructions are not actions executed here.

Fixed settings: chunk size 800, overlap 80, candidate depth 20 per enabled retriever, RRF rank constant 60, final selected top-k 5, metric ranking depth 10. No parameter tuning, question additions, paraphrasing or evidence edits. Kestrel uses all five files including both policy versions; Vellora uses the one original manual. Both canonical corpora contain 43 chunks at these settings.

Each CLI run used a fresh process and isolated temporary index directory. Runs were sequential, in the order shown below, to avoid competing benchmark CPU workloads. All local dense embeddings used CPU `all-MiniLM-L6-v2` and an existing cache with Hugging Face/Transformers offline flags; no model downloads or hosted generation were requested. The first question includes on-demand initialization/index construction. App-level BM25 persistence is unchanged, but benchmark runs do not reuse another run's temporary index.

Machine-readable artifacts are under `evaluation/results/v3/phase2_5_2026-11-07/`:

- Six original CLI JSON files, retaining every question, literal gold evidence, retrieved/selected chunks, origin ranks/scores, metrics, source/dataset hashes, per-question times and zero LLM counts.
- `manifest.json`: exact commands, environment overrides, timestamps, process exit/wall times, package/model-cache identity, evaluated source hashes, raw-output hashes and captured diagnostics.
- `summary.json`: independently verified metrics, full type grid, latency statistics, per-question comparisons/deltas, gold-quote checks and canonical-ID checks.
- `comparison.csv`: overall metrics at each K, with latency and failure counts.
- `by_type.csv`: every requested type plus preserved Vellora `other`, at every K; absent/unanswerable denominators are unavailable.
- `per_question.csv`: all 75 executions, times, per-K hit/recall and first rank for each gold quote within the saved top 10.
- `analyze.py`: standard-library-only verification/derivation script; it does not import application/model code or run retrieval.
- `verification.json`: actual post-benchmark regression result and preservation checks.

The summary script independently reconstructs exact source windows, validates IDs/text/offsets/lines, verifies original question fields and hashes, recomputes each hit/recall and aggregate, checks selected-prefix consistency, and recomputes every returned RRF score from its origin ranks. It fails on discrepancies rather than adjusting results.

## Exact executed commands

Run from the repository root. These are the six commands as recorded in the manifest; both exported flags applied to every run. The files now exist, so reproductions must choose fresh output names/directories: the CLI refuses overwrites.

```bash
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
.venv/bin/python -m evaluation.v3 --corpus kestrel --retrievers dense --chunk-size 800 --chunk-overlap 80 --candidate-depth 20 --rrf-k 60 --top-k 5 --output evaluation/results/v3/phase2_5_2026-11-07/kestrel-dense-800-80.json
.venv/bin/python -m evaluation.v3 --corpus kestrel --retrievers bm25 --chunk-size 800 --chunk-overlap 80 --candidate-depth 20 --rrf-k 60 --top-k 5 --output evaluation/results/v3/phase2_5_2026-11-07/kestrel-bm25-800-80.json
.venv/bin/python -m evaluation.v3 --corpus kestrel --retrievers dense bm25 --chunk-size 800 --chunk-overlap 80 --candidate-depth 20 --rrf-k 60 --top-k 5 --output evaluation/results/v3/phase2_5_2026-11-07/kestrel-dense-bm25-rrf-800-80.json
.venv/bin/python -m evaluation.v3 --corpus vellora --retrievers dense --chunk-size 800 --chunk-overlap 80 --candidate-depth 20 --rrf-k 60 --top-k 5 --output evaluation/results/v3/phase2_5_2026-11-07/vellora-dense-800-80.json
.venv/bin/python -m evaluation.v3 --corpus vellora --retrievers bm25 --chunk-size 800 --chunk-overlap 80 --candidate-depth 20 --rrf-k 60 --top-k 5 --output evaluation/results/v3/phase2_5_2026-11-07/vellora-bm25-800-80.json
.venv/bin/python -m evaluation.v3 --corpus vellora --retrievers dense bm25 --chunk-size 800 --chunk-overlap 80 --candidate-depth 20 --rrf-k 60 --top-k 5 --output evaluation/results/v3/phase2_5_2026-11-07/vellora-dense-bm25-rrf-800-80.json
```

Derived tables were generated with:

```bash
python3 evaluation/results/v3/phase2_5_2026-11-07/analyze.py
```

For a repeat derivation, add `--output-dir /tmp/v3-benchmark-analysis-NEW` with a new directory; saved tables are protected from overwriting. This verifies/analyzes existing raw runs without re-timing them. Six raw outputs were written directly by the V3 CLI, not synthesized from earlier report numbers.

## Metric definitions and reliability

For each answerable question, an annotated item is an exact `(source, literal quote)` pair. A hit at K requires any such item in the first K retrieved chunks; Recall@K is the fraction of that question's annotated items found. Overall/per-type results macro-average over answerable questions. A quote must occur wholly in a chunk from the correct source. This exactly preserves V2's `quote_recall` definition; it is not a count of every semantically relevant chunk.

`not_in_corpus` questions have no gold evidence, so HitRate/Recall are **N/A**. Absent types are also N/A; neither is scored as zero accuracy. Retrieval failures mean infrastructure/retriever errors, not a missing gold quote. Every expected question completed with successful retriever statuses in all six runs; therefore the observed failure count is reliably zero, not an assumed zero for an aborted run.

The evaluator scores k=1,3,5,10 from one saved ranking. `selected` is that ranking's first 5 chunks, while `retrieved` contains up to 10 for metric computation. No second search or LLM generation was used for selection. Full-answer completeness, answer accuracy, abstention quality and graph metrics are unavailable because this run does not measure them.

## Overall comparison

Each H/R column is **HitRate / annotated Recall**, both percentages. Mean latency covers all questions, including unanswerable ones and the first on-demand build; it is repeated for all K in the CSV because K values are prefixes of one retrieval, not independently timed searches.

| Corpus | Configuration | Answerable n | H/R@1 | H/R@3 | H/R@5 | H/R@10 | Mean ms/question | Retrieval failures |
|---|---|---:|---|---|---|---|---:|---:|
| Kestrel | Dense | 8 | 62.500% / 40.625% | 87.500% / 81.250% | 87.500% / 81.250% | 100.000% / 93.750% | 599.651 | 0 |
| Kestrel | BM25 | 8 | 37.500% / 18.750% | 75.000% / 53.125% | 75.000% / 53.125% | 87.500% / 71.875% | 3.036 | 0 |
| Kestrel | Dense + BM25 RRF | 8 | 50.000% / 21.875% | 75.000% / 59.375% | 87.500% / 71.875% | 100.000% / 93.750% | 479.811 | 0 |
| Vellora | Dense | 12 | 50.000% / 50.000% | 50.000% / 50.000% | 58.333% / 58.333% | 83.333% / 83.333% | 372.504 | 0 |
| Vellora | BM25 | 12 | 66.667% / 66.667% | 91.667% / 91.667% | 91.667% / 91.667% | 91.667% / 91.667% | 2.580 | 0 |
| Vellora | Dense + BM25 RRF | 12 | 58.333% / 58.333% | 75.000% / 75.000% | 91.667% / 91.667% | 91.667% / 91.667% | 299.012 | 0 |

## Latency interpretation

Milliseconds below are observed per-question retrieval timers. Mean/median/p95 include every question in the run (n=10 or 15). First-query time includes model loading, Chroma setup, source indexing and/or BM25 build. Post-first statistics omit q01 only (n=9 or 14); they describe subsequent queries in this sequence, not a repeated same-query warm-cache microbenchmark. p95 uses the nearest-rank rule and is especially unstable at these sample sizes.

| Corpus | Configuration | Mean all ms | Median all ms | p95 all ms | First query ms | Post-first mean ms | Post-first median ms | CLI process wall s |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Kestrel | Dense | 599.651 | 13.045 | 5877.653 | 5877.653 | 13.206 | 12.996 | 6.643 |
| Kestrel | BM25 | 3.036 | 2.447 | 8.282 | 8.282 | 2.453 | 2.444 | 0.152 |
| Kestrel | Dense + BM25 RRF | 479.811 | 19.152 | 4626.143 | 4626.143 | 19.107 | 19.122 | 5.447 |
| Vellora | Dense | 372.504 | 10.855 | 5436.026 | 5436.026 | 10.824 | 10.775 | 6.169 |
| Vellora | BM25 | 2.580 | 2.194 | 7.911 | 7.911 | 2.199 | 2.192 | 0.162 |
| Vellora | Dense + BM25 RRF | 299.012 | 13.045 | 4302.824 | 4302.824 | 13.025 | 13.027 | 5.073 |

The cold-including means happen to favor RRF over dense in both corpora because those separate processes initialized faster; that is **not** evidence that fusion is faster than dense retrieval. Post-first means show the additional local fusion/BM25 work: Kestrel dense 13.206 ms versus RRF 19.107 ms; Vellora dense 10.824 ms versus RRF 13.025 ms. BM25-only post-first means were 2.453 ms and 2.199 ms. No repetitions/confidence intervals or isolated component/index-build timings are available, so production latency/SLO claims would be unsupported. CLI process wall time additionally includes interpreter/startup/upload/JSON/cleanup overhead outside the per-question timer.

## Full comparison by question type

Each cell is HitRate / annotated Recall. Type latency is the mean for all questions in that type, including the first build if q01 belongs to it; it is not a warmed type-specific timing. The `not_in_corpus` type's latency can be measured although its retrieval accuracy cannot. Original `other` labels are retained. Missing types are stated explicitly after the tables and included with null metrics in the machine-readable grid.

### Kestrel by type

| Configuration | Type | Questions / answerable | H/R@1 | H/R@3 | H/R@5 | H/R@10 | Mean ms/question |
|---|---|---:|---|---|---|---|---:|
| Dense | exact_identifier | 2 / 2 | 50.000% / 25.000% | 50.000% / 50.000% | 50.000% / 50.000% | 100.000% / 100.000% | 2945.319 |
| Dense | split_answer | 2 / 2 | 100.000% / 62.500% | 100.000% / 100.000% | 100.000% / 100.000% | 100.000% / 100.000% | 13.160 |
| Dense | vocabulary | 1 / 1 | 100.000% / 100.000% | 100.000% / 100.000% | 100.000% / 100.000% | 100.000% / 100.000% | 12.996 |
| Dense | not_in_corpus | 2 / 0 | N/A / N/A | N/A / N/A | N/A / N/A | N/A / N/A | 12.879 |
| Dense | versions | 2 / 2 | 0.000% / 0.000% | 100.000% / 100.000% | 100.000% / 100.000% | 100.000% / 100.000% | 13.998 |
| Dense | two_hop | 1 / 1 | 100.000% / 50.000% | 100.000% / 50.000% | 100.000% / 50.000% | 100.000% / 50.000% | 12.803 |
| BM25 | exact_identifier | 2 / 2 | 50.000% / 25.000% | 50.000% / 25.000% | 50.000% / 25.000% | 100.000% / 100.000% | 5.435 |
| BM25 | split_answer | 2 / 2 | 50.000% / 25.000% | 100.000% / 62.500% | 100.000% / 62.500% | 100.000% / 62.500% | 2.441 |
| BM25 | vocabulary | 1 / 1 | 0.000% / 0.000% | 0.000% / 0.000% | 0.000% / 0.000% | 0.000% / 0.000% | 2.475 |
| BM25 | not_in_corpus | 2 / 0 | N/A / N/A | N/A / N/A | N/A / N/A | N/A / N/A | 2.413 |
| BM25 | versions | 2 / 2 | 0.000% / 0.000% | 100.000% / 100.000% | 100.000% / 100.000% | 100.000% / 100.000% | 2.426 |
| BM25 | two_hop | 1 / 1 | 100.000% / 50.000% | 100.000% / 50.000% | 100.000% / 50.000% | 100.000% / 50.000% | 2.452 |
| Dense + BM25 RRF | exact_identifier | 2 / 2 | 50.000% / 25.000% | 50.000% / 50.000% | 100.000% / 100.000% | 100.000% / 100.000% | 2323.141 |
| Dense + BM25 RRF | split_answer | 2 / 2 | 100.000% / 37.500% | 100.000% / 62.500% | 100.000% / 62.500% | 100.000% / 100.000% | 19.428 |
| Dense + BM25 RRF | vocabulary | 1 / 1 | 0.000% / 0.000% | 0.000% / 0.000% | 0.000% / 0.000% | 100.000% / 100.000% | 18.659 |
| Dense + BM25 RRF | not_in_corpus | 2 / 0 | N/A / N/A | N/A / N/A | N/A / N/A | N/A / N/A | 18.539 |
| Dense + BM25 RRF | versions | 2 / 2 | 0.000% / 0.000% | 100.000% / 100.000% | 100.000% / 100.000% | 100.000% / 100.000% | 18.591 |
| Dense + BM25 RRF | two_hop | 1 / 1 | 100.000% / 50.000% | 100.000% / 50.000% | 100.000% / 50.000% | 100.000% / 50.000% | 20.052 |

### Vellora by type

| Configuration | Type | Questions / answerable | H/R@1 | H/R@3 | H/R@5 | H/R@10 | Mean ms/question |
|---|---|---:|---|---|---|---|---:|
| Dense | exact_identifier | 4 / 4 | 50.000% / 50.000% | 50.000% / 50.000% | 50.000% / 50.000% | 75.000% / 75.000% | 10.583 |
| Dense | vocabulary | 4 / 4 | 25.000% / 25.000% | 25.000% / 25.000% | 50.000% / 50.000% | 100.000% / 100.000% | 11.189 |
| Dense | not_in_corpus | 3 / 0 | N/A / N/A | N/A / N/A | N/A / N/A | N/A / N/A | 10.742 |
| Dense | other | 4 / 4 | 75.000% / 75.000% | 75.000% / 75.000% | 75.000% / 75.000% | 75.000% / 75.000% | 1367.062 |
| BM25 | exact_identifier | 4 / 4 | 100.000% / 100.000% | 100.000% / 100.000% | 100.000% / 100.000% | 100.000% / 100.000% | 2.195 |
| BM25 | vocabulary | 4 / 4 | 50.000% / 50.000% | 100.000% / 100.000% | 100.000% / 100.000% | 100.000% / 100.000% | 2.199 |
| BM25 | not_in_corpus | 3 / 0 | N/A / N/A | N/A / N/A | N/A / N/A | N/A / N/A | 2.173 |
| BM25 | other | 4 / 4 | 50.000% / 50.000% | 75.000% / 75.000% | 75.000% / 75.000% | 75.000% / 75.000% | 3.650 |
| Dense + BM25 RRF | exact_identifier | 4 / 4 | 75.000% / 75.000% | 75.000% / 75.000% | 100.000% / 100.000% | 100.000% / 100.000% | 12.909 |
| Dense + BM25 RRF | vocabulary | 4 / 4 | 50.000% / 50.000% | 75.000% / 75.000% | 100.000% / 100.000% | 100.000% / 100.000% | 13.079 |
| Dense + BM25 RRF | not_in_corpus | 3 / 0 | N/A / N/A | N/A / N/A | N/A / N/A | N/A / N/A | 12.995 |
| Dense + BM25 RRF | other | 4 / 4 | 50.000% / 50.000% | 75.000% / 75.000% | 75.000% / 75.000% | 75.000% / 75.000% | 1085.559 |

Vellora has no `split_answer`, `versions` or `two_hop` questions; metrics/latencies for those types are N/A. Kestrel has no `other` questions. No extra questions or type reassignment were introduced to fill those cells. All represented types had zero retrieval errors; failures are recorded per configuration in the overall table and per execution in the CSV.

## Per-question findings

The following tables show **Recall@5** for every original question, plus first observed rank of each annotated quote within top 10. `>10` means not present in the saved top 10; it does not claim an exact rank outside that window. Rows with no gold evidence are N/A. All per-K values and individual latency observations are in `per_question.csv`/`summary.json` and the raw JSONs.

### Kestrel original questions

| ID | Type | Dense Recall@5; quote ranks | BM25 Recall@5; quote ranks | RRF Recall@5; quote ranks |
|---|---|---|---|---|
| q01 | exact_identifier | 0.000%; 7, 7 | 0.000%; 7, 7 | 100.000%; 5, 5 |
| q02 | exact_identifier | 100.000%; 2, 1 | 50.000%; 1, 6 | 100.000%; 1, 2 |
| q03 | split_answer | 100.000%; 2, 1, 1, 1 | 25.000%; 2, >10, >10, >10 | 25.000%; 1, 7, 7, 7 |
| q04 | split_answer | 100.000%; 3, 1 | 100.000%; 3, 1 | 100.000%; 3, 1 |
| q05 | vocabulary | 100.000%; 1, 1 | 0.000%; >10, >10 | 0.000%; 8, 8 |
| q06 | versions | 100.000%; 3, 3 | 100.000%; 2, 2 | 100.000%; 3, 3 |
| q07 | versions | 100.000%; 2 | 100.000%; 3 | 100.000%; 3 |
| q08 | two_hop | 50.000%; 1, >10 | 50.000%; 1, >10 | 50.000%; 1, >10 |
| q09 | not_in_corpus | N/A; no gold | N/A; no gold | N/A; no gold |
| q10 | not_in_corpus | N/A; no gold | N/A; no gold | N/A; no gold |

### Vellora original questions

| ID | Type | Dense Recall@5; quote ranks | BM25 Recall@5; quote ranks | RRF Recall@5; quote ranks |
|---|---|---|---|---|
| q01 | other | 0.000%; >10 | 0.000%; >10 | 0.000%; >10 |
| q02 | other | 100.000%; 1 | 100.000%; 1 | 100.000%; 1 |
| q03 | other | 100.000%; 1 | 100.000%; 1 | 100.000%; 1 |
| q04 | other | 100.000%; 1 | 100.000%; 2 | 100.000%; 2 |
| q05 | exact_identifier | 0.000%; 7 | 100.000%; 1 | 100.000%; 1 |
| q06 | exact_identifier | 100.000%; 1 | 100.000%; 1 | 100.000%; 1 |
| q07 | exact_identifier | 0.000%; >10 | 100.000%; 1 | 100.000%; 4 |
| q08 | exact_identifier | 100.000%; 1 | 100.000%; 1 | 100.000%; 1 |
| q09 | vocabulary | 0.000%; 9 | 100.000%; 2 | 100.000%; 5 |
| q10 | vocabulary | 100.000%; 1 | 100.000%; 1 | 100.000%; 1 |
| q11 | vocabulary | 0.000%; 6 | 100.000%; 2 | 100.000%; 1 |
| q12 | vocabulary | 100.000%; 5 | 100.000%; 1 | 100.000%; 3 |
| q13 | not_in_corpus | N/A; no gold | N/A; no gold | N/A; no gold |
| q14 | not_in_corpus | N/A; no gold | N/A; no gold | N/A; no gold |
| q15 | not_in_corpus | N/A; no gold | N/A; no gold | N/A; no gold |

### Where BM25 helps

On Vellora, BM25 changes Hit@5/Recall@5 from 0 to 1 for **q05 (E47), q07 (E86), q09 (grounds counter), q11 (three weeks unused)**. Their first-gold ranks change from dense 7, >10, 9, 6 to BM25 1, 1, 2, 2. q12 (limescale/warranty) improves from rank 5 to rank 1, helping at k=1/3 even though both hit at k=5. This is measured improvement on identifiers and some lexical queries, not a universal synonym capability.

At the requested K thresholds, BM25 has no HitRate/Recall improvement over dense on Kestrel in this run. It moves q06's refund evidence from rank 3 to 2, but both fall between the evaluated k=1 and k=3 thresholds, so reported metrics are unchanged.

### Where dense is better

- Kestrel **q02**, invitation/no-seat: dense retrieves both quotes by k=3; BM25 has only half at k=5 (second quote rank 6).
- Kestrel **q03**, failed-payment sequence: dense has all four annotated facts by k=3; BM25 has only the retry quote through k=10 (Recall=25%). Both can still have a Hit@5, illustrating why any-quote hit is insufficient.
- Kestrel **q05**, lost phone: dense retrieves both recovery quotes at rank 1; BM25 retrieves neither within top 10.
- Vellora **q04**, filter replacement: dense rank 1 versus BM25 rank 2, so dense is better at k=1; both succeed at larger evaluated K.

### Where RRF helps and hurts

- **Kestrel q01 improves:** the KST-2044 gold chunk is rank 7 in both independent retrievers and becomes fused rank 5. Shared moderate evidence crosses the selected-context boundary, improving Hit@5 and Recall@5.
- **Vellora q05/q07/q09/q11 improve versus dense at k=5**, recovering the same four misses as BM25. q11's gold chunk becomes fused rank 1, beating BM25 rank 2 and dense rank 6 at k=1.
- **Kestrel q05 gets worse versus dense:** its semantic-only recovery chunk is dense rank 1 but fused rank 8; Hit@5 and Recall@5 both fall from 1 to 0. Origin metadata shows no BM25 vote within depth 20, while multiple competing chunks receive two votes.
- **Kestrel q03 loses evidence completeness:** the grace-period/read-only/suspension chunk moves from dense rank 1 to fused rank 7; Recall@5 drops from 100% to 25%, despite Hit@5 staying true. The retry quote becomes rank 1. More agreement on a partial answer can displace the rest of a sequence.
- **Vellora q04 gets worse versus dense at k=1** (rank 1→2). Relative to BM25, hybrid worsens q07 at k=1/3 (rank 1→4), q09 at k=3 (2→5), and q12 at k=1 (1→3). Thus hybrid may dilute a strong lexical result too.

Kestrel q08 remains a partial-evidence failure in all three configurations: the runbook quote is rank 1, but the Messaging/channel quote is outside top 10. Its two-hop type reports HitRate=100% and Recall=50% at every K. Vellora q01 (water-tank capacity) remains a miss through k=10 in all configurations. No recovery or hybrid improvement is invented for these cases.

## Same-set and chunk-compatibility verification

All configurations use dataset SHA-256 values:

- Kestrel: `6c00d42de872482820a4ddc4fca21bf5207bc7c6749f1e0a60e8586bd2c94d75`.
- Vellora: `81f02e4b28216d456e589cf04338d941e9a9c90c09e8c536ec8f73abd8d495fd`.

Every copied question field (question, type, answerability, evidence, expected answer, notes and ID) was checked against the original JSONL, including order. Corpus-file hashes match across the three configurations for each corpus and match current source bytes. All 750 returned top-10 chunk snapshots were validated against reconstructed canonical windows, with no duplicate IDs per ranking, incorrect source text, offsets/lines, or foreign-corpus IDs.

IDs have the common `sha256(decoded_source):start:end` form. Each configuration's 43-chunk candidate universe is defined by the same source hashes and 800/80 windows. Canonical ID-set digests are Kestrel `6cde183054200506265228f811b20abad62914b53ae096c8807c5b49f0b72526` and Vellora `700c91f93c7816bde39a5fcf8472c81744fa8db119825704faefe16d75d48a43`. Origin ranks/RRF scores for each returned chunk were also checked. Raw files retain top-10 fused output, not the full two 20-candidate lists; a complete offline reconstruction of every discarded candidate requires rerunning retrieval.

The dense benchmark's overall/per-type/per-question metrics exactly match each frozen 800/80 V2 baseline. Post-benchmark regression tests also reproduced all four frozen 800/80 and 500/100 baselines through both legacy and configured dense-only paths. This verifies unchanged V2 metric behavior; timestamps, new schema/provenance and latency naturally differ.

## Evidence annotation limitations

All **29** gold quote entries are literal substrings of their named source, occur once there, and fit wholly inside at least one canonical 800/80 chunk. There are no broken gold-source references or unavoidable split-quote ceilings at these settings. Therefore the reported annotation-based metrics are computable. The annotations are nevertheless incomplete representations of some expected answers:

| Example | Expected facts not explicitly required by the existing gold-quote list | Source reference |
|---|---|---|
| Kestrel q02 | Invitation can still work only if <7 days old. | `evaluation/kestrel.jsonl:2`; `docs/kestrel/support-runbook-errors.md:90` |
| Kestrel q03 | Immediate email to Owner/billing contact, everything works during grace, and suspension does not delete the workspace. | `evaluation/kestrel.jsonl:3`; `docs/kestrel/billing-policy-2026.md:45,49,53` |
| Kestrel q04 | Table column headings binding SAML availability to plan names; setup/register/paste/test/enforce steps beyond the one metadata-download phrase. | `evaluation/kestrel.jsonl:4`; `docs/kestrel/product-guide.md:15,58` |
| Kestrel q05 | Sole Admin/Owner support contact and up-to-two-business-day identity verification. | `evaluation/kestrel.jsonl:5`; `docs/kestrel/product-guide.md:66` |
| Kestrel q06/q07 | Historical 2025 30-day refund and 15% discount comparison; quoted evidence requires only current-policy facts. | `evaluation/kestrel.jsonl:6-7`; `docs/kestrel/billing-policy-2025.md:13,35` |
| Kestrel q08 | Explicit postroom→Messaging ownership, SEV-2 condition, and Platform fallback outside working hours. | `evaluation/kestrel.jsonl:8`; `docs/kestrel/service-catalog.md:34-39,67,74`; `docs/kestrel/support-runbook-errors.md:107` |
| Vellora q05/q06/q08 | Full E47 unplug/empty-hopper/key procedure; E22 cause and persistent-error descaling; E70 fresh water. Only a short action phrase is gold for each. | `evaluation/vellora.jsonl:5-8`; manual lines 162,112,208 |
| Vellora q09/q10 | Machine must be on for counter reset; dishwasher removes necessary grease. The gold phrases omit these qualifiers/reasons. | `evaluation/vellora.jsonl:9-10`; manual lines 47,49 |

An unannotated fact may happen to be present in the retrieved whole chunk; this table does not claim it was absent. It means the metric never checks it. In particular, even Recall=100% on q08 would not independently verify every link/condition of the expected answer. **Complete factual answer recall is unavailable**, not equal to the reported annotation recall. No annotations were repaired or silently strengthened during this benchmark.

All Vellora answerable questions have one annotated quote, so their HitRate and Recall are numerically identical. Kestrel multi-quote questions distinguish partial from complete annotated evidence; the extra `all_annotated_evidence_rate` in `summary.json` counts questions whose annotated Recall=1, without claiming semantic answer completeness.

## Other limits and cost

- One deterministic run per configuration, 8/12 answerable questions and only one original Kestrel two-hop question. No independent held-out test set, repeated latency trial, confidence interval or broad-domain conclusion.
- All five unanswerable questions completed retrieval, often yielding common-word matches; no LLM or relevance grader was run. Abstention accuracy, hallucination rate and answer correctness are unavailable.
- Both historical/current billing policies remain indexed. Retrieval of current gold evidence does not prove the downstream answer selects the right policy or rejects conflicting old chunks.
- Dense candidates in the new configured path query all selected chunks before stable tie truncation. That guarantees deterministic cutoff membership at this scale but is not a scalable ANN throughput benchmark.
- No graph, new two-hop questions, triple extraction/grades, graph cost or graph path metrics. These belong to later phases after review.
- LLM calls and hosted input/output tokens are zero by construction of the retrieval-only evaluator. Local embedding token counts, component-specific CPU/energy cost and monetary infrastructure cost were not instrumented and are unavailable. Retrieval latency is measured; no paid API pricing assumptions are used.
- Offline model-cache revision and package versions are recorded for reproducibility, but a cached `refs/main` identity is not a complete exported model artifact or a cross-platform reproducibility guarantee. No fresh installation was performed.

## Regression and preservation checks

Executed **after** raw runs and summary/CSV generation:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/python -m pytest -q
```

Result: **94 passed in 13.94 seconds**. This includes the four frozen V2-baseline reproduction tests, original V1/V2 behavior, Phase 1 storage/indexing tests, and Phase 2 fusion/provenance/failure tests. Hosted generation is mocked in existing tests; no live LLM call was made. `git diff --check` and `node --check rag_app/static/app.js` also passed.

Checksums confirm all **29 pre-existing evaluation and corpus files** unchanged, excluding Python caches. No existing application code, question set, evidence, result, report, Git tag or commit was changed by this benchmark. Only the new benchmark directory and this report were created. Existing uncommitted Phase 1/2 work remains in place.

Stop point: Phase 2.5 is complete. Review these measured retrieval/evidence trade-offs before Phase 3; no Concept Graph implementation or release action has begun.

## Recorded environment

Python 3.12.3; macOS-27.0.1-arm64-arm-64bit; CPU embeddings. Cached MiniLM `refs/main`: `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`.

`chromadb==1.5.9`, `sentence-transformers==6.2.0`, `torch==2.14.1`, `transformers==5.20.2`, `numpy==2.5.4`, `pydantic==2.14.1`. Exact source hashes and process diagnostics are in `manifest.json`.
