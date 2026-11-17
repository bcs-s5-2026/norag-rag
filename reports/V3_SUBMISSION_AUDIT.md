# Final V3 submission audit

Audit date: 9 November 2026 (Europe/Paris). Scope: the professor’s 12-page `C8 - Session 3 - Part IV - RAG - V3.pdf` in the local `../Versions/` directory, current implementation, preserved evaluation artifacts and submission documentation. PDF page numbers below are physical pages, including the title page. The tiny extra `/bm25` instruction on page 5 was included in the audit.

**PASS: all mandatory technical requirements are implemented and supported by the current artifacts. No failed tests or remaining mandatory technical implementation items were found. WARNING: full interactive/responsive browser verification and the V3 submission email are not verified. Documentation corrections from this audit remain local and are not included in the existing release tag.**

## Requirements against the PDF

| PDF pages | Requirement | Verdict and current evidence |
|---|---|---|
| 4–5 | BM25 on both corpora; index construction/storage and choices documented | PASS — persistent snapshots, shared canonical chunks, tokenization, invalidation and restart behavior in `rag_app/bm25.py`, `bm25/README.md`, REPORT; BM25 regression tests pass. |
| 5 | Hidden `/bm25`, exact large “Watch your sources!”, no frontend reference | PASS — `rag_app/api.py` serves the exact text at 3rem; route and frontend checks pass. |
| 6 | Indexing-time LLM extraction on Kestrel; typed schema and rationale; node/edge chunk provenance; output validation and invalid-output policy | PASS — recipe v2 in `graph_build.py` / `graph_schema.py`; `concepts/kestrel_graph_v2/graph.json` has 43 validated chunk extractions, 42 entities, 39 relations. GraphIndex validates checksums, endpoint types, references, literal quotes and offsets. Complete extraction processing does not mean complete factual coverage: 26 extractions are empty. |
| 6 | Entity resolution; right merge and wrong/missed example; graph build calls/tokens/time | PASS — REPORT documents Analytics Engine merging, missed single-sign-on merge, preserved policy versions and the truncated Analytics Eng triple. Both attempt ledgers preserve 47 calls, 81,455 known input / 5,830 known output tokens and build timing. Four failed calls lack usage; total tokens/billing remain unknown. |
| 6–7 | Research, retrieval strategy, alternatives; question → ranked chunks | PASS — local entity seeding and bounded traversal in `graph_retrieval.py`; choices and alternatives in REPORT; GraphRAG/LightRAG sources and comparison in the research section of `V3_READINESS_AUDIT.md`. No new external research or provider call was needed for this audit. |
| 8 | UI and evaluation CLI toggles; RRF of enabled lists; per-reference retriever/rank; graph entities, edges and source chunks | PASS automated/source verification — `models.py`, `fusion.py`, `service.py`, `api.py`, `static/app.js`, `evaluation/v3.py`; tests cover all-three fusion, reference/path provenance and API controls. Full interactive/responsive browser verification remains a disclosed warning. |
| 9 | Dense and dense+BM25 on both corpora; dense+BM25+graph on Kestrel; HitRate/Recall at 1/3/5/10 overall/by type; per-question calls/tokens/latency | PASS — five mandatory configuration/corpus combinations freshly reproduced with identical rankings and metrics. Seventeen preserved current/comparison runs independently checked for source/dataset integrity, RRF scores, per-question and overall/by-type metrics. Retrieval-only hosted calls and tokens are zero; each row records measured latency. These costs exclude answer generation and local embedding token/CPU accounting. |
| 9 | Preserve V2 questions; add two Kestrel two_hop questions with evidence per hop | PASS — original ten Kestrel records unchanged; q11/q12 appended; three total two_hop questions; every annotated quote matches its source. Vellora questions remain unchanged. Missing question types and unanswerable evidence metrics are N/A, not invented scores. |
| 9 | Random sample of ten graph triples, source-supported grades and counts, preserved file; discuss graph evaluation | PASS — current `kestrel-v2-10-triples.json`, population 39, seed 20261108, Feras M: 10 correct / 0 wrong / 0 unsupported. Full verification below. REPORT discusses sampling precision, recall, resolution and downstream metrics. |
| 10 | Results by configuration/corpus/type, justified defaults, graph survival and measured change, a regression, graph/merge/build numbers and bad triple impact | PASS — final REPORT section, CSV/JSON tables, q05/q12 regressions, seed/depth experiments and truncated triple. Corrected strict top-5 survival versus any graph-origin presence; unchanged-V2-slice comparison added to avoid overstating hybrid gains. |
| 11 | Additional measured feature for teams of three | N/A — repository identifies Feras M as sole developer. No optional team-of-three feature implemented by this audit. Any individual-participation approval is a course administration matter not established here. |
| 12 | Updated question sets/results, ten grades, README commands, REPORT decisions/failures, Git tag v3 | PASS for technical artifacts and local/remote tag. README now lists all five mandatory evaluation combinations, current review artifacts and safe fresh-output commands. REPORT and current submission draft point to the rebuilt graph. Local and origin `v3` dereference to `2664b6f2b80cef4c710f30ffb32a2ae7ebe2c857`. Audit documentation changes are not yet published. |
| 2 | Email with team GitHub link, teammate CCs where applicable; deadline 9 November, 11:59 a.m. | WARNING — current unsent draft available; no email evidence inspected and no email sent. No teammates are listed in this sole-developer repository. |

## Current graph review and preserved history

Authoritative artifacts:

- `concepts/kestrel_graph_v2/graph.json` — build `f54cf5635cdf079b0efa5eab815e79c73dc73e349dea3d4971635326aa0e8481`, graph checksum `d67d06bace8ba373c9684351de28b667115d7a822839b4c568df43f775892b07`.
- `evaluation/graph_review/kestrel-v2-10-triples-ungraded.json` — original ungraded sample, all grades/reviewers/reasons null.
- `evaluation/graph_review/kestrel-v2-10-triples-ungraded.md` — exact supporting quotations, heading context where applicable, and full source chunks.
- `evaluation/graph_review/kestrel-v2-10-triples-ungraded-GRADES.csv` — ten filled grades and reasons, reviewer Feras M.
- `evaluation/graph_review/kestrel-v2-10-triples.json` — `human_review_complete`, counts 10/0/0; collection timestamp `2026-11-08T14:13:17.209020+00:00`. Its method records grades/reasons typed in the CSV and collected verbatim.

Verified that `random.Random(20261108).sample(sorted(relations, key=id), 10)` reproduces the ten distinct selected relation IDs from the current 39-relation graph. Build IDs and graph checksums match in both sample JSON files. Every non-grading sample field is unchanged between ungraded and graded artifacts. Every collected grade, reason, reviewer, subject, relation and object matches the CSV; evidence matches graph provenance, Markdown and exact document offsets. The preserved sample, CSV and collection record form the review trail; no new review event, grade, identity or timestamp was invented. The audit verifies record consistency, not independent proof of the human’s off-computer review process.

The older `concepts/kestrel_graph/` and `kestrel-10-triples*` sample are the first, superseded 10-relation graph and its AI-drafted, chat-confirmed reasons. They are historical comparison evidence, **not the current V3 extraction-quality result**. The `_superseded/` recipe-v2 partial-build samples are likewise not the current sample. All remain unchanged.

V2 provenance remains intact: initial Codex assessments followed by Feras M’s completed confirmation of all 15 Vellora no-context judgments, as clarified in the earlier documentation correction. No evaluation history was rewritten.

## Checks performed

- `.venv/bin/python -m pytest -q`: **150 passed in 12.94 seconds**, zero failures.
- Fresh retrieval-only evaluation of Kestrel dense, dense+BM25 and dense+BM25+graph; Vellora dense and dense+BM25. All rankings, per-question hits/recall, overall and by-type metrics matched saved artifacts. Indexes used temporary directories; no saved run was overwritten. No hosted answer/extraction call was made.
- Independently recomputed all K=1/3/5/10 metrics in 17 saved runs across `graph_v2_seedfix_2026-11-08/` and `graph_v2_final_2026-11-08/`, checked original dataset fields/hashes, source text/offsets, selected prefixes, standard RRF and graph build identity. Every check passed.
- Graph review random sampling, source evidence, original/graded equality outside review fields, CSV correspondence and recorded counts passed.
- `node --check rag_app/static/app.js` and `git diff --check` passed.
- Read-only `git ls-remote origin` verified origin/main and origin/v3 target. No commit, tag change, push or email was performed.
- SHA-256 comparison against the start-of-audit inventory verifies that all tracked `evaluation/` and `concepts/` artifacts remain byte-for-byte unchanged. Earlier V2 documentation corrections are retained. Historical JSON manifests/check records are unchanged and describe their original first-graph scope, not a checksum manifest for this audit.

## Documentation corrections and remaining warnings

Corrected README’s current-review pointer and evaluation commands; REPORT’s omitted Vellora `other` category, ambiguous graph-survival denominator, known-versus-total build usage and historical pending-tag statement; and the UI’s stale measured-default text (0.79 overall / 0.89 two_hop Recall@5). Marked earlier V3 reports as historical and redirected their current-status readers here. Replaced the obsolete submission email draft’s old graph/review/results references with current ones. No retrieval logic or optional feature was changed.

Strict survival of the graph’s own top five is **28/42** in the final depth-20 run; **31** fused top-five chunks have any graph origin, including graph ranks beyond five. At depth 40 these counts are 37/42 and 40. Historical `found_in_fused_at_k` fields retain their original any-origin semantics.

On the original ten Kestrel V2 questions, final Recall@5 is dense 0.8125, dense+BM25 0.71875, three-way 0.78125. On the augmented V3 set it is 0.7500, 0.7417 and 0.7917. The default’s aggregate gain applies to the augmented set, not the original V2 slice. Graph coverage gaps, q12 seeding regression, q05 fusion regression, failed-call usage unknowns and sample-size limitations remain reported; they are not missing mandatory features.

Remaining actions/warnings: publish the reviewed documentation changes through the user’s chosen Git workflow if they should accompany the submission; confirm/send the V3 email separately; full interactive/responsive UI verification is not claimed. No remaining mandatory technical implementation or documentation content gap was found after these corrections. No automatic push or history rewrite is required or performed.

## Git publication preparation — 9 November 2026

Verified branch `main`; initial HEAD and local/remote v3 target `2664b6f2b80cef4c710f30ffb32a2ae7ebe2c857`. Origin/main also pointed to that commit. The existing annotated v3 tag already contains the final implementation, current rebuilt graph, current 10-of-39 review and evaluation artifacts. Its tag object is `ce76444d15d493c886a35774e1628e23d5e568f4`.

The verified Markdown corrections, including V2 human-verification clarifications, are prepared in a separate documentation-only follow-up commit. The one-line UI status-text correction in `rag_app/static/app.js` remains uncommitted and is not included. No evaluation/graph artifact, application logic or existing tag is changed. A normal `git push origin main`, only after owner approval, will publish the corrected documentation; no tag push or tag movement is needed. Until that push, GitHub main still shows the original release documentation.

Submission URL after the approved push: https://github.com/Ferasmich/norag-rag/tree/main. Original implementation snapshot: https://github.com/Ferasmich/norag-rag/tree/v3. The audit’s test result above remains the recorded 150-test run; publication preparation adds no implementation changes.
