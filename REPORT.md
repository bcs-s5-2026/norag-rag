# RAG V1 — team and engineering report

## Team details

**Updated for the final release (12 November 2026).** Team: **Feras Michael** (GitHub: Ferasmich) and **Makuochukwu Okoene**. A possible third member was not confirmed when this report was written, so the project follows the handout's requirements for a team of two (Part A, one Part B feature, one Part C feature).

Contribution record, kept factual: every commit in this repository was made by Feras Michael. The repository was developed separately, with the intention of consolidating the team's work into it; it contains no code committed by another team member, and this report does not attribute any part of the implementation to anyone else.

AI assistance: the implementation was written with AI coding assistants (Codex for V1–V3, Claude Code for V4), directed and reviewed by Feras. Measurements come from the saved result files named in each section. Human grades are recorded only where a named person entered them; unreviewed results are labelled as such.

*V1 note, kept for history:* Feras was the sole developer at V1, with implementation assistance from Codex.

## Decision log

| Decision | Options | Choice and reason | Trade-off |
|---|---|---|---|
| Web stack | FastAPI + static JS; React/Next; Streamlit | FastAPI + static HTML/CSS/JS keeps the existing Python stack and uses one startup command | Manual browser state management; less component tooling |
| Pipeline reuse | Import demo directly; adapt its steps | Keep demos unchanged and implement the same MiniLM/Chroma/Gemini pipeline in a reusable service; demo import performs interactive/global initialization | Small duplication, but isolated application lifecycle and tests |
| Embeddings | Local MiniLM; hosted embeddings | Same local all-MiniLM-L6-v2 for chunks/questions, as in the course | 256-wordpiece limit; poor exact-code matching |
| Chunking | Fixed windows; paragraph/token-aware chunks | Naive 800-character windows, 80-character overlap by default; retain all source characters | Split words/facts and repeated passages; provides a measurable V1 baseline |
| Vector store | Chroma; in-memory vectors; hosted service | Local persistent Chroma cosine collections | Local disk dependency, one-process scope |
| Index identity | Filename; content hash | SHA-256 decoded content IDs; collection fingerprint includes model, algorithm, size and overlap; top-k excluded | Identical documents keep first filename; unused settings consume disk |
| Index recovery | Assume add succeeds; completion marker | Only complete per-document builds get a marker; interrupted builds are cleared and retried | Filesystem and Chroma are not a single transaction; managed application storage must stay together |
| Generation | Preserve streaming free text; validated JSON | Existing Gemini-compatible endpoint with non-streaming JSON, Pydantic validation and exact retrieved-ID membership checks | Wait for whole answer; malformed output is rejected; semantic grounding still needs human review |
| No answer | Always answer; score cutoff; model abstention | Explicit model abstention, empty citations, canonical no-evidence text | No calibrated score threshold; LLM may still misjudge relevance |
| References | Filename only; chunk IDs and offsets | Exact retrieved chunk snapshot with filename, start line and character range | Snapshot remains in prior responses even if a source later changes/deletes; UI clears displayed answer on deletion |
| Corpus | Whole novel; novel subsets; Vellora manual | Existing course manual: 31,036 characters, verifiable facts, many confusable error codes | Narrow fictional domain; not evidence of broad-domain quality |
| Evaluation | LLM grading; exact chunk IDs; source-span Hit@k | Fixed expected verbatim spans, source identity and Hit@5, isolated real retrieval | Small dataset; a split evidence span counts as miss; does not measure answer quality |
| Frontend safety | Render Markdown/HTML; plain text | Render all model/source/filename data through textContent | No rich formatting, but uploaded text cannot inject HTML into the page |
| Deployment | Hosted/multi-user; local | Loopback single-user process for V1 | No authentication or multi-worker synchronization |

## Retrieval baseline

`evaluation/questions.json` version 1 contains 15 questions: 12 answerable (four easy, four precise, four hard) and three unanswerable. Each contains expected answer and source passage/location, or explicit unanswerability. Run `python -m evaluation.run`. The evaluator uploads the unchanged course manual to an isolated temporary Chroma store, indexes once and queries all questions with the same model.

For each answerable question, a hit means at least one of the top-k chunks from the expected document contains the full expected literal evidence span. Hit@k = hit questions / answerable questions. Default settings: size 800 characters, overlap 80, k=5, MiniLM, cosine search. Actual measured **7/12 = 58.3% Hit@5**. Raw individual results and corpus/dataset hashes are in `evaluation/baseline.json`. The five misses are q01, q05, q07, q09 and q11. Unanswerable queries are excluded from this retrieval metric; their returned chunks are recorded, not labeled as correct evidence.

Keep the dataset and corpus unchanged for V2 and write new results to a separate file. Report all changed parameters. This small, manually selected dataset is a regression baseline, not a general accuracy estimate. No answer-accuracy percentage is claimed.

## Observed failures

| Test question | Expected | Observed | Possible cause | Potential V2 experiment |
|---|---|---|---|---|
| How large is the Vellora Duo water tank? | Retrieve section 2, 1.8 litres | q01 misses expected span in top 5. Live Gemini abstains, despite fact existing in the corpus | Generic water-tank passages outrank the parts list; chunk boundaries dilute the fact | Sentence/paragraph-aware chunks, compare same dataset |
| What should I do for error E47? | Retrieve the upper-burr/foreign-object procedure | q05 misses the expected span | Dense embeddings do not distinguish short exact codes reliably | Hybrid lexical/dense retrieval in V2 |
| How do I clear error E86? | Hold menu for five seconds | q07 misses expected span | Similar error-code passages and weak representation of exact digits | Measure lexical retrieval on precise-code subset |
| The grounds container was emptied but the counter has not reset. Why? | Remove for five seconds with machine on | q09 misses expected span | Long indirect query and boundary/context effects | Evaluate chunk strategy and retrieval depth |
| What preparation is needed after the machine sits unused for three weeks? | Fill water circuit after more than two weeks unused | q11 misses expected span | Temporal paraphrase and fixed-window retrieval | Query wording and chunking experiments |

Additional observed checks: the live Wi-Fi-password question correctly abstained, while the warranty question returned two years with a valid retrieved citation. Invalid generated JSON and fabricated citation IDs produced handled 502 responses in tests. These injected failures verify error handling; they are not claims that the real Gemini model exhibited those failures.

Browser visual QA was attempted: the browser inventory was empty and Safari inspection timed out. Consequently no visual or responsive-browser pass is claimed. Static routes, JS syntax and live HTTP workflow passed. No general hallucination-resistance claim follows from the two abstention samples. The exact returned evidence is retained in `reports/live_smoke.json`.

## Understanding the implementation

`rag_app/service.py` owns upload/index/retrieve/generate/validate. `rag_app/models.py` defines input and output rules. `rag_app/api.py` maps HTTP requests to service calls and safe errors. The static frontend sends selected IDs and numeric settings; it never receives API credentials. The same embedding function is attached to the Chroma collection for both add and query. At answer time, metadata filters exclude every unselected document before top-k selection. Returned references are assembled from the actual retrieval lookup rather than model-supplied source text.

A schema-valid citation is an integrity check: the cited passage was retrieved. It is not proof that the passage supports every generated claim. Opening and reading references is part of using V1 responsibly. The goal of V2 is to improve these measured retrieval misses one component at a time.


## V2 — C7 implementation and evaluation (review draft)

Authoritative scope: C7, Session 3, Part III, “RAG Project - V2”, 14 pages. Deadline **November 3, 2026 at 11:59 a.m.**, superseding the C6 schedule. This section is an implementation-assistant draft based on actual code and measured runs; Feras remains responsible for reviewing and personalizing the decision log. Required Kestrel hand grades and human verification of all 15 Vellora no-context judgments have been completed and recorded by Feras M. It does not claim student-authored observations or decisions. C7 page 3 asks for a student-written report; AI assistance is disclosed rather than presented as that personal work.

### Requirements and implementation evidence

| C7 page | Requirement | Implementation / verification |
|---|---|---|
| 2 | Deadline; repo submission and team details | Deadline corrected here and in README; sole developer recorded above. Submission email remains the owner’s responsibility. |
| 3 | Preserve V1 web app, references, validation, management and settings | Core service unchanged; original 30 tests retained and pass in the expanded suite; `v1` unchanged. |
| 4–5 | Two corpora, Kestrel starter 10 and own >=10 questions | Five Kestrel documents and starter JSONL copied unchanged; 15 fixed Vellora questions converted losslessly to JSONL. |
| 6 | No-context tests for both sets; flag correct answers | Exact questions sent without evidence/expected answers; real responses/errors saved. Kestrel human flags verified; all 15 Vellora judgments initially AI-assessed, then personally verified and confirmed by Feras M, with both stages recorded. Retain flagged questions to preserve baseline comparability. |
| 7–8 | Verification distinct from evaluation; file output, CLI + frontend; k=1/3/5/10, per type; two configurations | Shared evaluator, real MiniLM/Chroma runs, structured saved evidence and API/frontend controls; tables below. Unanswerable excluded. |
| 9 | Optional answer generation, grading rules before hand grades, best config on one set, diagnose failure stage | Kestrel 800/80 k=10 selected; actual responses saved with references and prior grading rubric. Manual grade/notes/reviewer controls and JSON export; all 10 Kestrel human reviews verified. |
| 10–11 | Words tab, corpus and question modes; choices justified | Case-folded Unicode token counts, chunk frequency, word-to-chunk counts, typed/picked questions, absence detection; exact offsets and selection maintained. |
| 12 | Diagnose two retrieval misses, one per corpus | Same Words analysis function as UI; actual counts and target chunks in `reports/words_diagnoses.json`, discussed below. |
| 13 | Unlinked `/about` page with prescribed large text | Dedicated HTML route; HTTP content and absence of frontend link checked in tests. |
| 14 | JSONL sets + no-context, results + grades, README/REPORT, v2 tag | Sets and real evaluation artifacts provided; Kestrel hand grades verified; all 15 Vellora no-context judgments human-verified and confirmed by Feras M after the initial AI-assisted assessments. Git release status is recorded in the implementation report. |

### V2 decisions for owner review

| Choice | Options considered | Implemented choice and rationale | Limitation |
|---|---|---|---|
| Retrieval experiment | Chunk parameters; hybrid/reranker/new model | Compare 800/80 with 500/100 using existing dense retrieval. C7 requires configuration comparison, not a specific advanced retriever. | Improvement depends on corpus and k. |
| Metric | Any expected quote; require every quote | HitRate uses any source/quote, plus macro quote recall for all quotes; Vellora’s single-quote metric matches V1 exactly. | Partial multi-hop evidence can count as a hit; recall and hand grading expose this. |
| Corpora | Replace Vellora; retain it with Kestrel | Preserve V1 corpus and all 15 questions; add unchanged Kestrel files/questions outside ignored Tasks. | Vellora type labels are mapped from V1 difficulty; not all six challenge types are present, so Kestrel is used for answer grading. |
| Evaluation entry points | Separate implementations; shared app service | CLI and frontend share the evaluator and RagService; no HTTP hop inside the evaluator. Public `/api/search` exposes the identical retrieval path for direct inspection. | Runs synchronously; browser generation may take minutes. |
| Words | Stemmed/stopword-filtered NLP; literal words | Python regex, case folding, internal hyphens/apostrophes; no new dependency or linguistic normalization. | Inflections differ; chunk boundaries can split a word; overlap repeats occurrences. |
| Grading | Automatic LLM judge; human grades | Save expected answers, real responses and references; owner records grades and no-context flags. | No answer-accuracy result until owner completes review. |
| Hosted failure handling | Abort and lose results; save per-question errors | Retain successes and handled errors. A paced rerun spaces calls six seconds apart. | No general retry/rate-limit framework; provider availability remains external. |

### Measurement method and actual configuration comparison

All four retrieval runs use the unchanged `all-MiniLM-L6-v2` CPU embeddings, cosine Chroma search and exact source substrings. Separate temporary indexes avoid cross-corpus contamination. Kestrel includes both billing policies, not just the files with expected quotes. Only chunk size and overlap change: A=800/80 (720-character step), B=500/100 (400-character step). Query once at depth 10, score prefixes 1/3/5/10. The app default answer top-k stays 5; optional Kestrel grading uses 10 because the best measured retrieval completeness is at that depth. Metric and dataset/corpus SHA-256 hashes, settings, timestamps and exact evidence snapshots are stored in each JSON result.

V1 is reproduced: `evaluation/baseline.json` and original dataset/corpus remain byte-for-byte intact, **7/12 Hit@5** at 800/80. V2 Vellora at 800/80 is also **7/12**. At 500/100 it is **8/12**, an increase of one question / 8.3 percentage points. This is an in-dataset comparison, not a general accuracy claim. At k=1, 500/100 is worse on both corpora; Kestrel also becomes worse at k=5. No universal improvement is claimed and no global default is silently changed.

### Kestrel: measured retrieval

| Chunk size / overlap | Type | Answerable | Hit@1 | Hit@3 | Hit@5 | Hit@10 | Quote recall@10 |
|---|---|---:|---:|---:|---:|---:|---:|
| 800 / 80 | overall | 8 | 62.5% | 87.5% | 87.5% | 100.0% | 93.8% |
| 800 / 80 | exact_identifier | 2 | 50.0% | 50.0% | 50.0% | 100.0% | 100.0% |
| 800 / 80 | not_in_corpus | 0 | excluded | excluded | excluded | excluded | excluded |
| 800 / 80 | split_answer | 2 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| 800 / 80 | two_hop | 1 | 100.0% | 100.0% | 100.0% | 100.0% | 50.0% |
| 800 / 80 | versions | 2 | 0.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| 800 / 80 | vocabulary | 1 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| 500 / 100 | overall | 8 | 25.0% | 75.0% | 75.0% | 100.0% | 90.6% |
| 500 / 100 | exact_identifier | 2 | 0.0% | 50.0% | 50.0% | 100.0% | 100.0% |
| 500 / 100 | not_in_corpus | 0 | excluded | excluded | excluded | excluded | excluded |
| 500 / 100 | split_answer | 2 | 50.0% | 100.0% | 100.0% | 100.0% | 87.5% |
| 500 / 100 | two_hop | 1 | 0.0% | 0.0% | 0.0% | 100.0% | 50.0% |
| 500 / 100 | versions | 2 | 0.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| 500 / 100 | vocabulary | 1 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |

Per-question Hit@5 (fixed questions):

| Question | Type | 800/80 | 500/100 | Change |
|---|---|---|---|---|
| q01 | exact_identifier | False | False | unchanged |
| q02 | exact_identifier | True | True | unchanged |
| q03 | split_answer | True | True | unchanged |
| q04 | split_answer | True | True | unchanged |
| q05 | vocabulary | True | True | unchanged |
| q06 | versions | True | True | unchanged |
| q07 | versions | True | True | unchanged |
| q08 | two_hop | True | False | worse |
| q09 | not_in_corpus | None | None | excluded |
| q10 | not_in_corpus | None | None | excluded |

### Vellora: measured retrieval

| Chunk size / overlap | Type | Answerable | Hit@1 | Hit@3 | Hit@5 | Hit@10 | Quote recall@10 |
|---|---|---:|---:|---:|---:|---:|---:|
| 800 / 80 | overall | 12 | 50.0% | 50.0% | 58.3% | 83.3% | 83.3% |
| 800 / 80 | exact_identifier | 4 | 50.0% | 50.0% | 50.0% | 75.0% | 75.0% |
| 800 / 80 | not_in_corpus | 0 | excluded | excluded | excluded | excluded | excluded |
| 800 / 80 | other | 4 | 75.0% | 75.0% | 75.0% | 75.0% | 75.0% |
| 800 / 80 | vocabulary | 4 | 25.0% | 25.0% | 50.0% | 100.0% | 100.0% |
| 500 / 100 | overall | 12 | 16.7% | 50.0% | 66.7% | 83.3% | 83.3% |
| 500 / 100 | exact_identifier | 4 | 0.0% | 25.0% | 50.0% | 50.0% | 50.0% |
| 500 / 100 | not_in_corpus | 0 | excluded | excluded | excluded | excluded | excluded |
| 500 / 100 | other | 4 | 50.0% | 75.0% | 100.0% | 100.0% | 100.0% |
| 500 / 100 | vocabulary | 4 | 0.0% | 50.0% | 50.0% | 100.0% | 100.0% |

Per-question Hit@5 (fixed questions):

| Question | Type | 800/80 | 500/100 | Change |
|---|---|---|---|---|
| q01 | other | False | True | improved |
| q02 | other | True | True | unchanged |
| q03 | other | True | True | unchanged |
| q04 | other | True | True | unchanged |
| q05 | exact_identifier | False | False | unchanged |
| q06 | exact_identifier | True | True | unchanged |
| q07 | exact_identifier | False | False | unchanged |
| q08 | exact_identifier | True | True | unchanged |
| q09 | vocabulary | False | True | improved |
| q10 | vocabulary | True | True | unchanged |
| q11 | vocabulary | False | False | unchanged |
| q12 | vocabulary | True | False | worse |
| q13 | not_in_corpus | None | None | excluded |
| q14 | not_in_corpus | None | None | excluded |
| q15 | not_in_corpus | None | None | excluded |


### Two misses diagnosed through Words

These counts were computed using `rag_app.words.analyze`, the exact function used by the Words UI, on 800/80 windows. Both corpora yield 43 nonempty chunks. Full source excerpts, word counts and exact offsets are in `reports/words_diagnoses.json`.

**Kestrel q01, KST-2044:** no expected quote in top 5; a quote appears by top 10. The identifier `kst-2044` occurs exactly once in one chunk, including the expected answer window (`support-runbook-errors.md`, characters 2880–3680). Generic `error` occurs in nine chunks, `it` in 21 and `and` in all 43. `mean`, `i` and `fix` are absent from the whole corpus. The answer-bearing chunk has the unique identifier but not the generic query terms `what`, `does`, `error`, `how`, `do`. Interpretation for review: the dense model may underweight exact digits and prefer semantically similar error-code neighbors. These counts establish an inspectable lexical distinction; they do not prove the embedding’s internal cause. At 500/100 q01 still misses at k=5.

**Vellora q11, preparation after three weeks unused:** no expected quote in top 5 in either configuration. `sits` and `unused` are absent from the corpus; `machine` occurs in 38/43 chunks, `the` in all 43, and `for` in 26. The expected answer window (characters 2880–3680) contains `three` and `weeks`, but not `preparation`, `needed` or `after`. `weeks` occurs in just one chunk. Interpretation for review: common wording is nondiscriminative while the question’s temporal/paraphrase relation is hard for a single dense query. Lexical presence alone cannot resolve “three weeks” versus the source’s “longer than two weeks” condition. No query rewriting or lexical retrieval is introduced in this assignment.

### Known failures and verification limits

The exact-code q05/q07 and temporal q11 Vellora misses persist at k=5. The smaller windows gain q01/q09 but lose q12; Kestrel loses the q08 two-hop Hit@5. At k=10 all Kestrel answerable questions have at least one quote, but quote recall remains below 100%, so complete evidence is still missing for some questions. Hand grades must distinguish partial answers, wrong answers and unsupported claims. Unanswerable retrieval candidates are not judged relevant and do not enter retrieval denominators.

Hosted generation/no-context errors in initial real runs are preserved, not graded as model mistakes. Real no-context replies can abstain, give generic advice or match parts of an expected answer; only owner review can establish which to flag. Questions will be retained rather than replaced, with flags disclosed. The implementation agent has not supplied fictional manual grades or claimed student review. The completed owner answer-quality evaluation is recorded below.

V1’s limitations still apply: embeddings may truncate inputs, schema-valid references do not prove semantic support, no calibrated relevance threshold, no authentication/multi-user isolation. Words returns all matches for course-sized corpora and can become large. Browser automation reached the V2 page, tab controls and Kestrel load; an evaluation POST returned 200, but final result rendering and Words click-through were not fully observed after browser access timed out. No complete interactive browser pass is claimed. API workflow and deterministic generation validation are covered by the expanded tests; precise test commands/results are recorded in `reports/RAG_V2_IMPLEMENTATION_REPORT.md`.

Future versions may investigate lexical retrieval for exact codes and safer/ measured generation, but hybrid search, reranking, logging/cost dashboards and new guardrails were not implemented here.


### Hosted-run completion and owner review

Paced Kestrel 800/80/k=10 completed with 10/10 validated generated responses and 10/10 no-context responses, no recorded hosted errors (`evaluation/results/kestrel-answers-no-context-paced.json`). Paced Vellora no-context completed 15/15, also without recorded hosted errors (`evaluation/results/vellora-no-context-paced.json`). Earlier incomplete attempts remain in their original result files. The two `*-no-context.jsonl` result sets include the original questions, expected evidence and actual no-context responses. Kestrel correctness flags reflect the verified owner review; Vellora flags reflect the initial separately saved AI assessments followed by Feras M’s completed human verification and confirmation of all 15 judgments; both stages are recorded.

The owner completed Kestrel grades. Reviewable local runs are `1b9aa8d25e274a92ba0079d58cae8ec9` (Kestrel, grade plus prior-knowledge flag) and `b9fecacce5e04d46a1b8388a942dd191` (Vellora, prior-knowledge flags). The verified Kestrel grade table appears below. Final commit/push/v2 tag status is recorded in the submission report.


## Verified Kestrel human review

The owner completed all 10 Kestrel reviews as **Feras M**. The downloaded `kestrel-1b9aa8d25e274a92ba0079d58cae8ec9.json` exactly matches the runtime saved run. Each row has a valid grade, nonblank notes/reviewer, review timestamp and explicit boolean no-context correctness flag. Every non-review field compares unchanged against the original paced run. The reviewed artifact is `evaluation/results/kestrel-reviewed.json`; the Kestrel no-context JSONL also includes these human flags and review metadata.

| Question | Human grade | Human diagnosis / rationale |
|---|---|---|
| q01 | correct | Exact identifier, both allowlist IPs and intermittent-failure explanation supported. |
| q02 | partial | Omits the invitation's seven-day validity condition despite retrieved evidence. |
| q03 | correct | Current-policy retries, grace period, read-only state and suspension supported. |
| q04 | partial | Omits testing with one Admin and enforcing SSO for all members. |
| q05 | partial | Omits identity-verification duration of up to two business days. |
| q06 | correct | Owner accepts the supported comparison of old/current refund policies. |
| q07 | correct | Owner accepts the supported current/old annual discounts. |
| q08 | wrong | Abstains on an answerable question; necessary Messaging team evidence missing from retrieval. |
| q09 | correct | Correctly abstains on unavailable mobile-app information. |
| q10 | correct | Correctly abstains on unavailable seat pricing. |

Totals: **6 correct, 3 partial, 1 wrong, 0 unsupported** across 10 questions. Both unanswerable questions abstain correctly. These are the owner's judgments on this small fixed set, not agent-assigned grades or a general accuracy estimate. All 10 Kestrel no-context flags are false according to the owner. No questions are replaced. The full original notes remain in the reviewed JSON rather than being rewritten by the agent.

Vellora no-context human verification is complete: **Feras M personally verified and confirmed all 15 judgments** after the initial AI-assisted assessments. The reviewed JSON and no-context JSONL record this confirmation while preserving the original AI provenance; see the sections below.


## Final no-context assessment and comparison

At the owner's explicit request, Codex initially assessed all 15 saved Vellora no-context responses against the expected answers and corpus evidence. These initial judgments were **AI-assisted assessments** and are preserved separately in `evaluation/results/vellora-ai-assessed.json`, including their original reasoning, assessor, timestamp and historical `human_reviewed: false` status. **Feras M subsequently personally verified and confirmed all 15 judgments.** Completed human verification is recorded in `evaluation/results/vellora-reviewed.json` and `evaluation/results/vellora-no-context.jsonl`, with verifier, timestamp, rationale and review history. The initial AI assessment and later human confirmation remain distinct events; original responses, results and provenance are unchanged.

Vellora flags: **q09 and q10 true; the other 13 false**. q09 supplies both removal for at least five seconds and machine-on conditions. q10 gives no dishwasher and explains loss of necessary lubricant. q04 offers a generic two-month interval for another filter but not the required 50-litre condition, so it is false. q13–q15 do not provide factual answers; abstentions never count as prior knowledge. All questions are retained, with these flags disclosed rather than silently replaced. Feras M completed human verification of all 15 no-context judgments. This is distinct from grading generated RAG answers: C7 requires hand grading on one set, fulfilled by the existing Kestrel human review.

RAG versus no-context: on Kestrel, the owner rated 6/10 RAG answers correct, 3 partial and 1 wrong (0 unsupported), while none of the 10 no-context responses supplied the expected facts. The wrong q08 is primarily a retrieval failure: team/channel evidence is missing; q02/q04/q05 omit details despite available source information, indicating incomplete generation. The owner's acceptance of q06/q07 is preserved exactly, despite the previously noted version-selection caveat. Vellora has 2/15 no-context expected-fact matches, initially AI-assessed and subsequently verified and confirmed by Feras M; it was evaluated for retrieval at all four k values, but no comprehensive Vellora RAG-answer quality percentage is claimed. Retrieval hits are not answer grades. The small question sets and initial AI-assisted assessment followed by human confirmation limit broader conclusions.

Verification limitations: complete responsive/browser click-through remains unverified; browser smoke and HTTP workflows are recorded above. Student report personalization and the actual submission email remain owner responsibilities. No V3/V4 functionality was added.


## Post-release Vellora human confirmation

Feras M completed human verification and explicitly confirmed all 15 proposed no-context judgments in chat after reviewing the question/expected-answer/response summary table: **Yes for q09 and q10, No for the other 13**. The confirmation concerns the no-context flags, not a new Vellora RAG-answer grading experiment. `evaluation/results/vellora-reviewed.json` and `vellora-no-context.jsonl` now record the verifier, confirmation timestamp, rationale and review history. Original AI assessor metadata remains unchanged, including its historical `human_reviewed: false` value at the time of the AI-only assessment; the subsequent `human_verification` event records the later confirmation. `vellora-ai-assessed.json` remains byte-for-byte intact. All 10 Kestrel human reviews are unchanged. The original v2 release snapshot contains the initial AI-only assessments; the subsequent human confirmation is recorded in the follow-up artifacts. Final V2 documentation reflects completed human verification by Feras M.

This is a follow-up on main, not a new release. The existing annotated v2 tag remains object `07ff1e7d3262b4fbbb589eb97921cfa1803d1d20`, pointing to release commit `2a223476c8df74ae6e0464fada5c277f39aaa984`. Main is expected to advance beyond that tag. No evaluation questions, model responses, retrieval metrics or application code changed.

Follow-up validation: 40 tests passed in 8.26 seconds; all 15 confirmations and original AI/Kestrel artifact integrity checked; git diff whitespace check passed.


## V3 implementation, human review and final retrieval comparison — 8 November 2026

> **Superseded** by "V3 final — rebuilt Concept Graph" below. This section describes the first, partial graph (v1, flash-lite, 10 relations). Its ten grades were AI-drafted reasons confirmed in chat, over the whole 10-relation graph rather than a sample; they are not the submitted extraction-quality review.

V3 now provides persistent BM25 on both corpora, independent dense/BM25/graph retrieval, equal-weight RRF, UI/CLI selection, citation origin/rank and graph-path/source inspection. Fixed typed graph extraction, conservative entity resolution, durable provenance/cache/quarantine, capped resumable builds and costs are documented in [the final integration report](reports/V3_FINAL_INTEGRATION.md). That report includes overall and per-type HitRate/Recall at 1/3/5/10, failures, latency, decisions and exact reproducible commands.

The approved Gemini extraction used exactly 43 attempts, with 29 strict-valid responses (27 empty), 10 validation rejections and four provider failures. The partial published graph has 17 entities / 10 relations: nine relations use explicitly annotated offline source-context expansion of existing model proposals. Feras M graded all ten retained relations correct; the random sample population is only those ten, not the raw outputs. Known usage is 50,239 input / 1,845 output tokens, estimated $0.0196842; full cost is unavailable because four failed requests lack usage. No follow-up calls were made.

Kestrel V3 (12 questions, 10 answerable): HitRate/Recall@5 is dense 90%/75%, BM25 80%/55.8%, dense+BM25 90%/74.2%, graph 20%/11.7%, all three 90%/70.8%. Vellora (original 15, 12 answerable): dense 58.3%/58.3%, BM25 and dense+BM25 91.7%/91.7%. Defaults are therefore dense for Kestrel and BM25 for Vellora. q01 improves with lexical fusion; q05 loses evidence; q12 loses its ledger support with the graph vote. Graph candidate top-5 survival rises from 12/18 at depth20 to 17/18 at depth40, while Recall@5 falls to 50.8%; depth20 is retained. No graph benefit or completeness is invented.

Two append-only Kestrel multi-hop questions are supplied; original datasets/results remain unchanged. Final nine retrieval runs use zero LLM calls and report literal annotation recall rather than exhaustive relevance. All 144 tests passed in 11.96s, including four V2 dense baseline reproductions on both legacy/configured paths. Browser verification remains unavailable; no new hosted answer-quality grading was performed. [Final verification](reports/V3_FINAL_VERIFICATION.md) records the release checks. This supersedes earlier historical statements that no V3 functionality exists. This was the historical pre-release status. The local and origin `v3` tag now identify commit `2664b6f2b80cef4c710f30ffb32a2ae7ebe2c857`; email submission has not been verified by this audit. See `reports/V3_SUBMISSION_AUDIT.md` for current checks.

## V3 final — rebuilt Concept Graph, hybrid retrieval and evaluation (8 November 2026)

This section is the V3 submission report. It supersedes the V3 numbers above. The final audit against the professor’s 12-page C8 PDF is in [V3_SUBMISSION_AUDIT.md](reports/V3_SUBMISSION_AUDIT.md). The `v3` tag already exists locally and on origin at `2664b6f2b80cef4c710f30ffb32a2ae7ebe2c857`; subsequent documentation corrections are prepared as a separate local follow-up commit and require a normal push to make them available on origin/main. The existing v3 tag remains unchanged.

### Results table (Recall@k / HitRate@k)

Retrieval-only evaluation, 800/80 chunks, final top-k 5, candidate depth 20 per retriever, RRF k = 60. Kestrel uses the V3 question set (12 questions, 10 answerable: the 10 original V2 questions plus q11, q12); Vellora uses the unchanged V2 set (15 questions, 12 answerable). Recall@k = fraction of a question's annotated evidence quotes found in the top k (so for two_hop it tells whether *all* hops were retrieved). Zero LLM calls at query time in every configuration. Raw runs: `evaluation/results/v3/graph_v2_seedfix_2026-11-08/` (Kestrel, final graph + seed fix) and `evaluation/results/v3/graph_v2_final_2026-11-08/` (Vellora, BM25, and the before-fix graph runs).

**Overall**

| Corpus | Retrievers on | R@1 | R@3 | R@5 | R@10 | Hit@5 | Hit@10 | Median latency |
|---|---|---|---|---|---|---|---|---|
| Kestrel | dense (V2 baseline) | 0.36 | 0.72 | 0.75 | 0.95 | 0.90 | 1.00 | 12.8 ms |
| Kestrel | BM25 | 0.25 | 0.56 | 0.56 | 0.78 | 0.80 | 0.90 | 2.5 ms |
| Kestrel | dense + BM25 | 0.21 | 0.54 | 0.74 | 0.95 | 0.90 | 1.00 | 15.2 ms |
| Kestrel | graph | 0.17 | 0.38 | 0.38 | 0.42 | 0.50 | 0.50 | 2.2 ms |
| Kestrel | dense + graph | 0.22 | 0.62 | **0.82** | 0.97 | 0.90 | 1.00 | 15.1 ms |
| Kestrel | **dense + BM25 + graph (default)** | 0.25 | 0.49 | **0.79** | **1.00** | 0.90 | 1.00 | 17.6 ms |
| Kestrel | dense + BM25 + graph, depth 40 | 0.25 | 0.52 | 0.64 | 0.90 | 0.80 | 0.90 | 17.7 ms |
| Kestrel | dense + BM25 + *v1 graph* | 0.14 | 0.42 | 0.71 | 0.95 | 0.90 | 1.00 | 17.3 ms |
| Vellora | dense (V2 baseline) | 0.50 | 0.50 | 0.58 | 0.83 | 0.58 | 0.83 | 10.8 ms |
| Vellora | **BM25 (default)** | 0.67 | 0.92 | **0.92** | 0.92 | 0.92 | 0.92 | 2.2 ms |
| Vellora | dense + BM25 | 0.58 | 0.75 | 0.92 | 0.92 | 0.92 | 0.92 | 12.9 ms |

**Recall@5 by question type** (n = answerable questions of that type; not_in_corpus questions have no evidence and are excluded from Recall/Hit, as in V2)

| Corpus | Retrievers | exact_identifier | split_answer | vocabulary | versions | two_hop | other |
|---|---|---|---|---|---|---|---|
| Kestrel (n) | | 2 | 2 | 1 | 2 | 3 | – |
| Kestrel | dense | 0.50 | 1.00 | 1.00 | 1.00 | 0.50 | – |
| Kestrel | BM25 | 0.25 | 0.62 | 0.00 | 1.00 | 0.61 | – |
| Kestrel | dense + BM25 | 1.00 | 0.62 | 0.00 | 1.00 | 0.72 | – |
| Kestrel | graph | 0.25 | 0.50 | 0.00 | 0.00 | 0.78 | – |
| Kestrel | dense + graph | 0.25 | 1.00 | 1.00 | 1.00 | 0.89 | – |
| Kestrel | dense + BM25 + graph | 1.00 | 0.62 | 0.00 | 1.00 | **0.89** | – |
| Vellora (n) | | 4 | – | 4 | – | – | 4 |
| Vellora | dense | 0.50 | – | 0.50 | – | – | 0.75 |
| Vellora | BM25 | 1.00 | – | 1.00 | – | – | 0.75 |
| Vellora | dense + BM25 | 1.00 | – | 1.00 | – | – | 0.75 |

All k (1/3/5/10), HitRate and Recall per type are in each run folder's `tables.md`, `by_type.csv` and `per_question.csv`, and the original run JSON. Vellora retains its four original `other` questions rather than silently relabeling them. Missing types and `not_in_corpus` retrieval metrics are N/A; unanswerable items have no gold evidence denominator.

For a comparison on the unchanged original ten Kestrel V2 questions (8 answerable), the final saved runs give:

| Retrievers | HitRate@5 | Recall@5 |
|---|---:|---:|
| dense | 0.875 | 0.8125 |
| dense + BM25 | 0.875 | 0.71875 |
| dense + BM25 + graph | 0.875 | 0.78125 |

Thus the three-way default improves Recall@5 on the augmented 12-question V3 set, but does not improve overall Recall@5 on the original V2 slice. Dense is evaluated on the same added questions as every other configuration. These are recomputations from preserved per-question records, not new grades or edited results.

### Default configuration, and why

- **Kestrel: dense + BM25 + graph, top-k 5, depth 20, RRF k 60.** On the augmented V3 set, it raises Recall@5 from 0.75 (dense) to 0.79 and Recall@10 to 1.00. The gain is concentrated where it was designed to be: two_hop Recall@5 goes from 0.50 to 0.89, and exact identifiers from 0.50 to 1.00 (BM25). dense + graph has a higher overall Recall@5 (0.82) but drops exact_identifier to 0.25 (q02), which is the "E47" failure the course started from; with 10 answerable questions, that 0.03 difference is less than one question, so I chose the configuration without a hole on a whole question type. Cost per question: 0 LLM calls, 0 tokens, +4.8 ms median retrieval latency over dense. The graph costs one build (below).
- **Trade-off:** Recall@1 (0.25 vs 0.36) and Recall@3 (0.49 vs 0.72) are worse than dense alone; fusion spreads the top ranks over three voters. With a top-k of 3 dense would win; at our top-k of 5 the hybrid wins.
- **Vellora: BM25 alone.** Recall@5 0.92 vs 0.58 for dense; dense + BM25 ties at k = 5 but is worse at k = 1 and 3. No graph on Vellora (not required; the corpus is a single manual).
- The UI selects these defaults when a corpus is loaded; every retriever can still be switched on/off in the UI and with `--retrievers` on the CLI.

### BM25: index, tokenization, updates

Full detail: [Phase 1 BM25 report](reports/V3_PHASE1_BM25.md) and [bm25/README.md](bm25/README.md). Summary:

- **Where it lives:** a persisted JSON snapshot per (selected documents, chunk settings, tokenizer/BM25 version), at `data/bm25/<fingerprint>.json` (or `$RAG_DATA_DIR/bm25/`). It stores canonical chunk rows, per-chunk term counts and a SHA-256; it is written atomically. A restart loads and validates it without re-tokenizing. This replaces the naive in-memory index of the original norag-rag script.
- **Built from:** the *same* canonical chunks and IDs as dense (`document_sha256:start:end`), so RRF can fuse by ID.
- **Tokenization:** Unicode casefold + the existing Words regex; hyphens are kept inside tokens, so `KST-2044` is one token and does not match `KST-2040`. No stemming, stop words or synonyms (this is exactly why BM25 fails on vocabulary questions). BM25 k1 = 1.5, b = 0.75; deterministic tie-break on chunk ID.
- **Updates:** a changed document gets a new content ID, hence a new snapshot; deleting a document invalidates all BM25 snapshots (rebuilt lazily). Explicit rebuild: `POST /api/bm25/index?rebuild=true`.
- **Options considered:** in-memory per request (simplest, but rebuilds every time), Chroma/SQLite full-text search (FTS5), or a search engine (Elasticsearch/OpenSearch). A JSON snapshot was enough for a 43-chunk corpus and keeps the scoring code inspectable; FTS5 would be the next step for larger corpora.
- Hidden page: `GET /bm25` shows "Watch your sources!" in a large font and is not linked anywhere in the front end.

### The Concept Graph

**Build (recipe v2).** `python -m rag_app.graph build --recipe v2 --model gemini-3.6-flash --approve-external …` (full commands in README). All 43 Kestrel chunks (800/80, identical to retrieval chunks) have validated Gemini extractions through the OpenAI-compatible endpoint, with temperature 0 and JSON output. The final build reused 19 cached extractions and made 24 new calls; the earlier build also had four failed calls, so the full recipe-v2 history totals 47 attempts. The chunk is sent together with its **Markdown heading path** (e.g. `## Connectors (KST-2xxx) > ### KST-2040 — Connection timed out`) and, inside tables, the table header row. The heading path is computed locally, without an LLM.

**Schema: fixed, not open.** 10 entity types (ErrorCode, Service, Team, Channel, Feature, Plan, Role, Policy, Rule, Value) and 10 relation types (RAISED_BY, OWNED_BY, CONTACT_CHANNEL, ESCALATE_TO, PROVIDES, AVAILABLE_ON, HAS_RULE, HAS_VALUE, REQUIRES, REPLACED_BY), each with allowed endpoint types and direction (`rag_app/graph_schema.py`). Why fixed: the questions are about support routing (error → service → team → channel) and plans; a fixed schema makes every edge checkable and traversal predictable. An open schema (GraphRAG/LightRAG style) finds more, but produces near-duplicate relation names ("is owned by", "belongs to", "managed by") that then need their own resolution step. The cost of the choice: facts outside the schema are lost — see "where it fails".

**Validation (Pydantic, strict).** Every triple must: parse against the schema; use allowed endpoint types and direction; have an `evidence_quote` that is a literal substring of the chunk; name at least one endpoint in the quote, the other either in the quote or in the heading path *at the quote's position* (not the chunk start: a chunk can end one `###` section and start another); error codes must be complete `KST-0000`. Conditions ("only if…") must be substrings of the quote. **When an item does not validate, only that item is dropped and logged** (v1 rejected the whole chunk response, losing 10 of 43 chunks). Malformed JSON still rejects the response, which is quarantined, and the chunk is retried on resume. In the final build: 0 rejected responses, 0 dropped items.

**Provenance.** Every node and edge lists provenance records: chunk ID, document, exact quote with character offsets, model, response ID, prompt hash, and — when an endpoint came from the heading — the heading path (`context_heading`, 11 edges). Retrieval re-verifies every quote against its chunk at load time and refuses a graph whose checksum does not match.

**Entity resolution.** Conservative: two mentions are the same entity only if they have the same type and the same normalized label (casefold, whitespace, dash variants), or an explicit alias statement in the text ("also known as", "stands for"). Policies and rules are scoped to their document, so the 2025 and 2026 Billing and Refund Policies stay two nodes. No fuzzy or embedding similarity.
- *Merge I got right:* "Analytics Engine" appears in the owner lines of `query-engine` and `scheduler`, the teams table and the KST-3012 runbook section; the 4 mentions merged into one node, which is what lets KST-3012 → Analytics Engine → #oncall-analytics connect across two documents.
- *Right non-merge:* the two Billing and Refund Policy nodes (2025 vs 2026) are kept apart, which a name-only merge would have broken (versions questions).
- *Merge I missed:* "single sign-on" (product guide §5.2) and "Single sign-on (SAML)" (plans table) are the same feature but stay two nodes; exact matching cannot see it. Cost: a question that names "single sign-on" only reaches the §5.2 chunk through the graph, not the plans table.

**The graph in numbers.** 42 entities (10 Service, 8 Team, 6 ErrorCode, 6 Feature, 6 Channel, 4 Plan, 2 Policy), 39 relations (14 AVAILABLE_ON, 11 OWNED_BY, 6 CONTACT_CHANNEL, 6 ESCALATE_TO, 1 RAISED_BY, 1 REPLACED_BY: mailman → postroom), 14 merge decisions (all normalized-exact), 17 of 43 chunks contribute at least one relation. For comparison the v1 graph had 17 entities and 10 relations.

**Build cost.** Model `gemini-3.6-flash` ($0.75 / $3.75 per million input/output tokens, checked 8 Nov 2026).
- Final build: 24 calls, 45,766 input + 3,402 output tokens, $0.047, 406 s (paced 8 s between calls).
- An earlier run of the same recipe stopped on the free-tier limit (5 requests/minute, ~20/day for this model): 23 calls (19 valid, 2 × HTTP 500, 2 × 429), 35,689 + 2,428 tokens, $0.036, 356 s; its 19 valid extractions were reused from the cache by the final build (`attempts_superseded_partial_build_5d6add.json`). Billing was then enabled on the key.
- Total for the v2 graph: **47 LLM calls, 81,455 known input + 5,830 known output tokens, ≈ $0.083 known-usage estimate, ≈ 12.7 min**. Four failed calls have no token usage; exact total tokens and total billed cost are unavailable. The v1 graph had cost 43 calls / $0.020 with flash-lite. Query-time cost of graph retrieval: 0 LLM calls.

**Graph retrieval.** Takes the question and returns ranked chunks like the other retrievers. (1) Seeds: entities whose name appears in the question (word boundaries; error codes take priority). A one-word capitalized name ("Team", "Business") must match with its case, so a common word does not seed a plan (fix described below). If nothing matches, a local lexical match over entity names and their evidence quotes (TF-IDF-like, no LLM). (2) Breadth-first traversal up to 3 edges from at most 3 seeds, both directions, at most 12 edges per node, 200 expansions. (3) Each path votes for the chunks of its edges' provenance and its end node, weighted by seed score / (1 + path length). Chunks are ranked by summed votes. The UI shows the matched entities, the edges followed (with conditions) and the source quotes.
Other options I considered: community summaries (GraphRAG global search) — aimed at "summarize the corpus" questions, not routing; LightRAG-style keyword extraction of the question with an LLM — better seeds (would fix q12) but one LLM call per question; personalized PageRank from the seeds — smoother scores but harder to explain in the UI.

**Extraction quality (manual).** 10 triples drawn with `random.Random(20261108).sample` from the 39 relations, graded by me against the full source chunk: **10 correct / 0 wrong / 0 unsupported**. File: `evaluation/graph_review/kestrel-v2-10-triples.json` (grades and reasons as I wrote them in `kestrel-v2-10-triples-ungraded-GRADES.csv`; the sample with full chunks is in `kestrel-v2-10-triples-ungraded.md`). Limits: 7 of the 10 are table rows or owner lines, which are the easy cases; 10/10 on a sample of 10 still leaves room for errors in the other 29 — and there is one (below).
*How else to evaluate a concept graph:* precision by sampling (done); recall by hand-listing the facts of a few chunks and checking how many are in the graph (the 26 empty chunks show recall is the weak side); entity-resolution precision/recall on name pairs; and the task metric — does the graph move two_hop Recall (it does).

**One bad triple, and what it cost.** `KST-3012 → ESCALATE_TO → "Analytics Eng"`: the chunk ends at character 4400 in the middle of "Analytics Eng|ine". The model copied the truncated name, and my validator accepted it because the label is literally in the quote. It created a separate Team node with no channel, so a path from KST-3012 through it is a dead end (the correct edge to "Analytics Engine" also exists, from the overlapping next chunk). Measured cost on the question set: none, because no question asks about KST-3012; on a real support question about KST-3012 it adds a useless path. Fix: reject labels ending exactly at a chunk boundary inside a word (v1 had this filter in `graph_context.py`; I did not port it to v2).

**Where the graph fails.**
- *Low recall on policies:* 26 of 43 chunks produced no relation, mostly the billing policies. The schema can express them (Policy → HAS_RULE → Rule → HAS_VALUE → Value), but the model did not use these types, so versions questions get nothing from the graph (graph-alone Recall@5 = 0 on versions).
- *Few error codes:* only 6 of the 14 runbook codes are in the graph and only 1 RAISED_BY edge; most runbook sections describe the service in prose ("the connector could not…") without the catalog name.
- *Seeding without a name* (q12, below).
- *Optional features:* conditions on edges (`condition_quote`, e.g. "only if the customer shows that the bank approved the payment"), REPLACED_BY for service history, explicit-alias support (no alias statements in the corpus), and heading context. Not done: time validity (valid from/until), a graph of the Vellora corpus.

### What happened to the graph's chunks after fusion

| Run | Graph own top-5 candidates (sum over 12 questions) | Of those, surviving in fused top 5 | Any graph-origin candidates in fused top 5 | Kestrel R@5 |
|---|---:|---:|---:|---:|
| v1 graph, depth 20 | 18 | 12 | 12 | 0.71 |
| v2 graph, depth 20, before seed fix | 41 | 23 | 25 | 0.76 |
| v2 graph, depth 20, seed fix (default) | 42 | **28** | **31** | **0.79** |
| v2 graph, depth 40, seed fix | 42 | 37 | 40 | 0.64 |

With the v1 graph, few graph chunks reached the top 5 because the graph had almost nothing to say (10 relations). The saved `found_in_fused_at_k` field counts any graph-origin candidate, including graph ranks below 5; it is not restricted to the graph’s own top 5. The strict survival column above additionally requires graph origin rank ≤5. What I changed, and measured: (1) the rebuild increases any-graph presence from 12 to 25 (strict survivors 12 → 23, R@5 0.71 → 0.76); (2) the seed fix increases presence 25 → 31 (strict survivors 23 → 28, R@5 0.76 → 0.79, two_hop 0.78 → 0.89); (3) depth 20 → 40 increases presence 31 → 40 (strict survivors 28 → 37) but R@5 falls to 0.64, because dense and BM25 also contribute their ranks 21–40 and RRF then rewards chunks that are mediocre in all lists. I kept depth 20 and plain (equal-weight) RRF. Historical evaluator fields and result files are unchanged.

Clearest success: **q08** (KST-5031, which team and where?). The catalog chunk with `#oncall-messaging` is rank 16 in BM25 and rank 20 in dense; the graph follows KST-5031 → RAISED_BY → postroom → OWNED_BY → Messaging → CONTACT_CHANNEL → #oncall-messaging and ranks it 2; after fusion it is rank 2. q08 Recall@5: 0.5 → 1.0. q11 also goes 0.67 → 1.0.

### One question where adding a retriever made things worse

**q12** (two_hop: "Which team's on-call channel should support contact for the service that generates invoice PDFs and runs automatic payment retries?"). dense + BM25: Recall@5 1.0. Adding the graph: 0.67.
1. *Before the fix* the graph seeded the **Plan "Team"** from the word "team's", followed Team → AVAILABLE_ON → "bank transfer against an invoice" and pushed a billing-policy chunk to rank 1. I made one-word capitalized names case-sensitive, which fixed that seed (and improved q11) — but q12 still loses.
2. *After the fix* no entity name is in the question (the service, `ledger`, is described, not named), so the lexical fallback seeds on the words "generates", "pdfs", "runs": it picks **scheduler** ("Generates the report PDFs") and Analytics Engine instead of ledger ("Generates invoice PDFs"). Its votes lift the scheduler catalog chunk and a runbook chunk, and push the chunk with "Generates invoice PDFs" from rank 3 to rank 6.
Lesson: the graph is only as good as its entry point; a described-but-unnamed entity needs semantic seeding (embed entity descriptions, or an LLM to extract the entity) — a planned V4 candidate. Note: the seed fix was motivated by a question of this same 12-question set, so its gain may be optimistic on new questions.

Other regression: **q05** (vocabulary) loses its evidence when BM25 joins dense (1.0 → 0.0): BM25 has no synonyms and its high-ranked keyword matches outvote dense's single correct chunk in RRF.

### Updated question sets

`evaluation/kestrel-v3-additions.jsonl` adds q11 and q12 (two_hop, each with an evidence quote for every hop); q08 was the existing two-hop question, so Kestrel has 3 two_hop questions. `evaluation/kestrel.jsonl` and `evaluation/vellora.jsonl` are unchanged byte for byte; `kestrel-v3.jsonl` is the combined view.

### Decision log (V3)

| Decision | Options | Choice and reason |
|---|---|---|
| BM25 storage | in-memory per request; JSON snapshot; SQLite FTS5; Elasticsearch | JSON snapshot keyed by selection/settings: persistent, inspectable, enough at 43 chunks |
| Fusion | weighted RRF; score normalization + sum; RRF | plain RRF, k = 60: rank-based, no score calibration between cosine and BM25 |
| Graph schema | open (LLM decides types); fixed | fixed 10 + 10 types: checkable edges, predictable traversal |
| Extraction unit | whole document; chunk; chunk + heading | chunk + heading path: provenance stays per retrieval chunk, error code not lost when a section is split |
| Invalid LLM output | reject response; drop item | drop the item, log it; reject only malformed JSON |
| Entity resolution | embeddings/fuzzy; LLM judge; exact + explicit alias | exact normalized + explicit alias: no wrong merges, accepts missed ones |
| Extraction model | flash-lite (v1); 3.6 Flash | 3.6 Flash: v1 flash-lite left 27 of 29 valid chunks empty; v2 costs ≈ $0.08 |
| Graph seeding | names; lexical fallback; LLM | names (case-sensitive for one-word names) + lexical fallback, no LLM per query |
| Candidate depth | 20; 40 | 20 (40 measured worse) |
| Defaults | per corpus | Kestrel dense + BM25 + graph; Vellora BM25 |

### Known failures and limits

- Small evaluation sets: 10 answerable Kestrel and 12 Vellora questions; one question moves Recall@5 by 0.1. Differences under ~0.1 are not meaningful.
- Graph recall (26 empty chunks, missing policy rules, 6/14 error codes) and the chunk-boundary truncation described above.
- Generation quality with the new retrievers was not re-graded; V3 measures retrieval only (as requested).
- The v1 graph and its review are kept for comparison (`concepts/kestrel_graph/`, `evaluation/graph_review/kestrel-10-triples*`); the v1 grades were AI-drafted and chat-confirmed over the whole 10-relation graph, so they are not used as the V3 extraction-quality result.


## V4 — final release: traces, concept map explorer, personal data redaction (12 November 2026)

Scope: the C9–C10 handout "RAG Project – V4 – The final release" (23 pages). For a team of two it asks for a clean-up, Part A (traces), one Part B feature and one Part C feature. The requirement-by-requirement check is in [reports/V4_FINAL_VERIFICATION.md](reports/V4_FINAL_VERIFICATION.md). All numbers below come from `evaluation/results/v4/` (index in its README).

### What changed in the architecture

The V3 pipeline is unchanged: upload → chunk → dense / BM25 / graph retrieval → RRF fusion → Gemini → citation validation. V4 adds three small modules around it and changes no retrieval logic.

```
question ──► dense ─┐
             BM25  ─┼─► RRF fusion ─► redact ─► Gemini ─► validate ─► restore ─► answer + trace id
             graph ─┘                 (C)                  (C guard)   (C)
   every step is a span of one trace (A) ─► data/traces/traces.jsonl ─► "Details" in the page
concept map tab (B) ─► reads concepts/kestrel_graph_v2/graph.json ─► links, quotes, chunks (+ a trace)
```

| File | Lines | Role |
|---|---|---|
| `rag_app/tracing.py` | ~100 | `Trace` (spans with a context manager), `TraceStore` (JSON lines, 30-day pruning), `llm_cost` |
| `rag_app/redaction.py` | ~65 | `Redactor`: replace, restore, detect invented contact details |
| `rag_app/concept_map.py` | ~50 | list of concepts, neighbourhood of one concept with its evidence |
| `rag_app/service.py` | changed | spans around existing steps; `index_run`, `concept`, `_traced_question` |
| `rag_app/api.py` | changed | `/api/traces`, `/api/traces/{id}`, `/api/concepts`, `/api/concepts/{id}`; errors carry a `trace_id` |
| `rag_app/static/*` | changed | Details dialog, Recent activity, Concept map tab, clean-up |

No new dependency.

### Clean-up

Looking at the V3 page as a first-time user, the problems were: six search parameters visible before the first question, a raw JSON block under every answer, the demo corpus hidden in the Evaluation tab, and a page that kept saying "preparing an answer…" after a failure. Changes: a **Load the Kestrel demo documents** button that also fills in a sample question; search parameters folded under *Advanced search settings* with plain names ("Meaning", "Exact words"); the JSON block replaced by the **Details** view; a clear "no answer this time" message with the reason and a Details button; the V1 baseline panel moved into the Evaluation tab. The README now starts with installation and a four-step first run. The Evaluation and Words tabs are unchanged.

### Part A — traces

**What is traced.** One trace per question, per indexing run and per concept lookup. Each trace has an id, a kind, a start time, a duration, an outcome and a list of spans.

| Trace | Spans | Outcomes |
|---|---|---|
| question | one per enabled retriever (`dense`, `bm25`, `graph`), `fusion`, `redact`, `generate`, `validate` | answered, abstained, invalid (LLM output rejected), error |
| indexing | `embed_document` per newly embedded document, `bm25_index` | indexed, error |
| concept | `load_graph`, `neighborhood` | found, error |

A retriever span records the number of candidates and the ids of its top chunks; `fusion` records the final ranking with the rank each retriever gave; `redact` records how many e-mails and phones were replaced; `generate` records the model, input and output tokens and the cost; `validate` records whether the answer was answerable, the cited chunk ids and how many invented contact details were removed.

**When an indexing run is traced.** Always when the user clicks *Prepare documents now*; and automatically when a question has to embed a document that was not indexed yet. A question that finds everything already indexed does not create an indexing trace (tested: two questions on a new document produce exactly one).

**What is never in a trace.** API keys, document or chunk text (ids only), answers. Exceptions are stored by type name only, because a library error message could quote document text. Personal data: the question is stored after redaction (Part C), so an e-mail address or phone number typed in a question is not written to disk. Names are not removed; this is the main gap and the reason traces stay local and expire.

**From the answer to its trace.** Every answer has a **Details** button; so does a failed question (the error response carries the trace id), the status line after an indexing run, and every concept. *Recent activity* lists the last 30 traces.

**Decision log questions (handout page 9).**

- *What do you trace, where, for how long?* The items above, appended to `data/traces/traces.jsonl` (git-ignored), pruned at start-up when older than 30 days.
- *Who can read them? Do they leave the machine?* Anyone with access to this user account on the laptop; the API listens on 127.0.0.1 only. They are never sent anywhere. The LLM provider receives the redacted question and passages, not the trace.
- *Metrics page.* Not built (optional). The per-request totals shown in Details are sums over the spans of that trace; the cost is `input_tokens × $0.30/M + output_tokens × $2.50/M` for `gemini-3.5-flash-lite` (price table from the V3 graph build, checked 8 November 2026). An unknown model gives "cost unknown", not zero.
- *Other options considered.* SQLite table: better for queries, but there is nothing to query without a metrics page, and JSON lines can be opened in any editor. Langfuse or Phoenix self-hosted: real trace views, but a second service to install, which works against "easy to install and run". A hosted tool: traces would leave the machine. Python `logging`: no structure per request.

**Trade-offs.** Reading a trace scans the whole file (fine for hundreds of traces, not for millions). Only the model and tokens of the last LLM call are kept on the service object, which is correct for a single-user app with one request at a time and would not be for concurrent users.

### Part B — concept map explorer

**Why this feature.** The menu offered study artifacts, concept map explorer, conversation mode, answer style controls, iterative retrieval, reranking and query routing. The concept map explorer was chosen because the V3 graph already stores, for every link, the quote and chunk it came from, so the feature could be checked completely and automatically; it needs no LLM call (no cost, no invalid output to handle); and it gives the user something they did not have: a way to see what is in the corpus before asking.

| Alternative | Why not |
|---|---|
| Reranking | needs a second model (a new download or more LLM calls); the gain on 22 answerable questions would be within noise |
| Iterative retrieval, conversation mode | one or more extra LLM calls per question, and no objective check of "a good reformulation" with our small question sets |
| Query routing | per-corpus defaults already exist (V3); a per-question router tuned on 22 questions would be overfitted |
| Study artifacts, answer style controls | quality of generated quizzes or tone can only be judged by hand |

**How it works.** `GET /api/concepts` lists the 42 concepts with their number of links. `GET /api/concepts/{id}` loads the saved graph (the loader re-validates checksums and that every quote matches its chunk), then returns the concept, its links (relation, direction, the other concept, the condition if any) and its mentions; each link and mention carries the quote, its character offsets, the document name and the full chunk text. The page draws the concept in the centre with one neighbour per link and lists the links below with their sources. Clicking a neighbour moves to it. *Ask a question about this concept* selects the Kestrel documents, writes "What do the documents say about X?" in the Ask tab and lets the user edit it.

**Traced like the rest.** Each lookup is a trace with two spans and the ids of the chunks shown. A question asked from a concept is an ordinary question trace.

**Cost and latency (measured).** Browsing: 0 LLM calls, 0 tokens, median lookup 1.0 ms, maximum 1.3 ms over the 42 concepts. A question asked from a concept costs one LLM call: $0.0015 for "ledger" and "#oncall-payments", $0.0036 for "Enterprise" (see the token finding below).

**Failures.** Unknown concept id: 404 "Concept not found in the graph", with a trace. Graph file missing or corrupted: 503 "Concept map unavailable: …" shown in the tab. A concept without links would show "No link was extracted"; the current graph has none.

**Checked (`offline_2026-11-12.json`, tests in `tests/test_v4.py`).**

- All 42 concepts were opened. 156 quotes (mentions and link evidence) were compared with the unchanged course documents at the recorded offsets: 156 correct, 0 wrong.
- Each of the 39 relations is visible from both of its ends (78 link views), with opposite directions.
- Difficult cases looked at: the hub *Enterprise* (6 links, the most), *#oncall-analytics* (1 link, the fewest), the 5 links that carry a condition, and a concept name starting with `#`.
- In the browser: selecting *Payments Core* shows 4 neighbours; clicking *#oncall-payments* moves to it; *Public share links → Business* shows the table row `| Public share links | — | Yes | Yes | Yes | Yes |` as its source and the full 800-character chunk.

**What we found.** The explorer shows the graph exactly as it is, including its weaknesses from V3: 26 of 43 chunks produced no triple, so many things in the documents (refund rules, most error codes) are simply not on the map; the table-row quote above is correct but hard to read; a mention can appear twice when the same sentence lies in the overlap of two chunks (Payments Core lists 5 mentions for 3 distinct sentences). Generated questions of the form "What do the documents say about X?" are broad: for the hub *Enterprise* the answer is a list of features rather than an explanation.

**Limits.** Kestrel only (the graph was built for these five documents with 800/80 chunks). Read-only: the graph does not update when documents change. The drawing places neighbours on an ellipse and would overlap beyond about 12 neighbours (maximum today: 6).

### Part C — personal data redaction

**Risk addressed.** The application runs on a laptop, but two things leave the process: the question and the retrieved passages go to the LLM provider, and the trace keeps a copy of the question on disk. If a user types "my e-mail is …" or a document contains a phone number, that data would be sent to Google and stored in the trace file.

**Why this feature and not the injection scanner.** One feature is required for a team of two. Redaction is a pure function applied at two points and can be tested by capturing exactly what is sent. The injection scanner needs a quarantine state and a review screen. Injection is only mitigated as before (system prompt: documents are untrusted data; citations must be retrieved ids).

**How it works.** `Redactor.redact` replaces e-mail addresses and phone numbers by numbered placeholders (`[EMAIL_1]`, `[PHONE_1]`); the same value always gets the same placeholder within a request. It is applied to the question and to the text of every retrieved passage just before the LLM call, and to the question before it is written in the trace. Retrieval itself uses the original question, because embeddings, BM25 and the graph run locally. After validation, `restore` puts the real values back in the answer, in memory, so the user reads a normal answer; references always show the original local text.

**How detection is done.** Patterns (regular expressions), not an LLM (that would send the data out in order to detect it) and not an NER library (a new dependency and model). E-mail: a standard address pattern. Phone: a run of digits with the usual separators that contains 9 to 15 digits and is not an IP address, an ISO date or a decimal number.

**Checked.**

| Check | Result | Source |
|---|---|---|
| 11 detection cases (addresses, French/US/international numbers, IP, dates, prices, error codes) | 11 behave as expected, including 3 expected misses | `offline_2026-11-12.json` |
| False positives on the two course corpora | 0 phone matches; 2 role addresses found (`billing@`, `privacy@kestrel.example`) | same |
| Captured LLM payload with personal data in question and document | none of the three values present; placeholders present | `tests/test_v4.py` |
| Trace file after 8 live questions, and after 3 runs of the hard case | no e-mail or phone found | `live_final_…`, `redaction_two_placeholders_…` |
| Same refund question with and without personal data in front | both answered; same content (30-day rule in 2025, 60-day rule in 2026) | `live_final_2026-11-12.json` |

**Three problems found by testing, and what was done.**

1. *A phone number at the end of a sentence kept its last two digits* ("+33 6 12 34 56 78." became "[PHONE_1] 78."). The pattern refused a number followed by a full stop, to protect decimals. Fixed in the pattern; regression test added.
2. *The model replaced the placeholder with an invented address.* For "How do I request a refund, and where do I send the request?", the first live run answered with `support@kestrel.example`, which is not in the corpus. A/B test, two runs each: with redaction the answer contained `refunds@kestrel.analytics` and `refunds@kestrel.example`; without redaction it contained the correct `billing@kestrel.example` both times (`redaction_ab_2026-11-12.json`). So redaction itself caused a wrong answer. Fix, part 1: one sentence in the system prompt saying that placeholders must be copied exactly. After it, 4 of 4 runs were correct (`redaction_after_fix_…`).
3. *With two placeholders the model wrote the real address without having seen it.* When the question also contained an e-mail, the model answered `billing@kestrel.example` literally, although the payload contained only `[EMAIL_2]` (checked: the string is absent from the payload). It guessed from the context. A first guard that rejected any address in the raw answer therefore rejected a correct answer 3 times out of 3. Fix, part 2 (final): an address or number written by the model is kept if it equals a value that was hidden for this request, and replaced by "[contact removed: not found in your documents]" otherwise; the count is recorded in the trace. Final code: 3 of 3 correct on this case, 8 of 8 live questions with 0 removals.

**Limits.**

- Names are not detected. Example from the saved run: the answer about `#oncall-payments` contains "led by Jonas Berg" in two of the three saved runs; that name is in a retrieved passage and was sent to the provider with it. Postal addresses, account numbers and obfuscated forms ("sam (at) example (dot) org", a number written in words) are not detected either.
- A role address such as `billing@kestrel.example` is treated like a personal one. This costs nothing to the user because it is restored, but it is the cause of problem 2.
- Not covered: file names, the V3 graph extraction (run once, on the course documents, with its own approval flag) and the V2 "no-context" evaluation call, which sends fixed course questions.
- Placeholders are an instruction the model can ignore. The guard removes invented values but cannot tell whether the rest of the sentence is right.

### Measured results

**Retrieval regression (no LLM).** The V3 evaluation was re-run on the final code for 7 configurations and compared with the committed V3 runs: 81 of 81 questions have an identical ranked list of chunk ids, and all metrics are equal (`retrieval_regression_2026-11-12/comparison.json`).

| Corpus | Retrievers | Recall@5 V3 | Recall@5 V4 | Hit@5 V3 | Hit@5 V4 | Median V3 → V4 |
|---|---|---|---|---|---|---|
| Kestrel | dense | 0.75 | 0.75 | 0.90 | 0.90 | 12.8 → 14.1 ms |
| Kestrel | dense + BM25 | 0.74 | 0.74 | 0.90 | 0.90 | 15.2 → 16.8 ms |
| Kestrel | graph | 0.38 | 0.38 | 0.50 | 0.50 | 2.2 → 2.5 ms |
| Kestrel | dense + BM25 + graph (default) | 0.79 | 0.79 | 0.90 | 0.90 | 17.6 → 19.0 ms |
| Vellora | dense | 0.58 | 0.58 | 0.58 | 0.58 | 10.8 → 11.3 ms |
| Vellora | BM25 (default) | 0.92 | 0.92 | 0.92 | 0.92 | 2.2 → 2.5 ms |
| Vellora | dense + BM25 | 0.92 | 0.92 | 0.92 | 0.92 | 12.9 → 14.6 ms |

The V4 medians are 0.3 to 1.7 ms higher. The runs were made on different days on the same laptop, so this is an upper bound for the cost of recording spans, not a precise measure.

**Eight live questions (`live_final_2026-11-12.json`).** Kestrel, default retrievers, top-k 5, `gemini-3.5-flash-lite`, one LLM call each.

| Case | Outcome | Time | Tokens in / out | Cost |
|---|---|---|---|---|
| two-hop (KST-5031) | answered | 1.85 s | 3407 / 289 | $0.00174 |
| answer needs a hidden corpus address | answered, correct address restored | 0.92 s | 3449 / 136 | $0.00137 |
| refund after 45 days | answered | 2.01 s | 3441 / 330 | $0.00186 |
| same, with name, e-mail and phone in front | answered; 2 e-mails and 1 phone replaced | 1.43 s | 3464 / 275 | $0.00173 |
| not in corpus (iPhone app) | abstained | 0.81 s | 3205 / 32 | $0.00104 |
| from concept *ledger* | answered | 1.24 s | 2981 / 224 | $0.00145 |
| from concept *Enterprise* (hub) | answered | 1.73 s | 8055 / 478 | $0.00361 |
| from concept *#oncall-payments* | answered | 0.91 s | 3459 / 198 | $0.00153 |

Totals: 8 calls, 31,461 input and 1,962 output tokens, $0.0143 (about $0.0018 per question). Median time 1.33 s, of which 1.31 s is the LLM call and 25 ms the three searches and the fusion. Indexing the five documents (43 chunks): 6.1 s, almost all of it loading the embedding model, 0 LLM calls.

"Answered" is the outcome recorded by the pipeline (valid JSON, citations among the retrieved chunks). It is not a judgment of correctness.

**Human review of the eight answers.** Feras M graded the eight answers of this run on 12 November 2026, with the V2 grading rules (correct / partial / wrong / unsupported). The grades and notes are recorded verbatim in `evaluation/results/v4/live_final_2026-11-12-REVIEW.csv` (and `.md`); the answers and result file were not changed.

| # | Case | Grade | Reviewer's note |
|---|---|---|---|
| 1 | two-hop (KST-5031) | partial | Missing after-hours escalation to Platform. |
| 2 | answer needs a hidden corpus address | correct | Both request methods are supported. |
| 3 | refund after 45 days | correct | Correct 2025 and 2026 policy comparison. |
| 4 | same, with personal data in front | correct | Correct refund rule; email and phone were redacted. |
| 5 | not in corpus | correct | Correctly says the documents do not provide the answer. |
| 6 | from concept *ledger* | correct | Service functions and owner match. |
| 7 | from concept *Enterprise* | correct | Plan features match the source passages. |
| 8 | from concept *#oncall-payments* | correct | Correct Payments Core channel and rotation. |

Result: **7 correct, 1 partial, 0 wrong, 0 unsupported**. The partial answer is the two-hop question: the team and channel are given but one part of the expected answer (the after-hours escalation to Platform) is missing. Eight questions graded by one reviewer on a single run is a small sample; answers vary between runs (across the three saved runs, the KST-5031 answer states the `#oncall-messaging` channel in only two), and only this run was graded.

**A cost finding made with the traces.** The *Enterprise* question used 8,055 input tokens against about 3,400 for the others. Cause: the evidence sent to the model is the retrieved rows as they are, including, for chunks found by the graph, the list of graph path ids (each one a 69-character hash). A hub concept seeds many paths: 84 path ids for *Enterprise* against 5 for *ledger*; the evidence JSON is 12,714 characters, of which only 4,827 are id, document name and text. Effect: about 4,650 extra input tokens, +$0.0014, so 2.4 times the usual cost of a question, and identifiers that are of no use to the model. Sending only `id`, `name` and `text` would remove it. It was not changed for the final release: it alters the prompt that the saved V2/V3/V4 answers were produced with, and it is a cost issue, not a wrong result.

**API cost of V4 development and checks.** About 44 calls to `gemini-3.5-flash-lite` in total (browser checks, A/B tests, three runs of the 8 questions), about $0.07 according to the traces.

### Decision log (V4)

| Decision | Options | Choice and reason | Evidence / trade-off |
|---|---|---|---|
| Trace storage | JSON lines; SQLite; Langfuse/Phoenix; hosted | JSON lines in `data/traces/`: nothing to install, readable in an editor, stays local | linear scan on read |
| Retention | forever; N traces; N days | 30 days, pruned at start-up | a test checks pruning |
| Trace content | full prompts and answers; ids and counts | chunk ids, counts, timings, tokens, cost, redacted question | handout: no keys, no whole documents; cannot replay an answer from its trace |
| Personal data in traces | store as typed; drop the question; redact | redacted question | names remain, hence local + 30 days |
| Indexing trace | every index check; only real work | button click always, automatic indexing only when something is embedded | 1 trace for 2 questions on a new document |
| Failed requests | no trace; trace without link | trace saved, id returned with the error, Details button on the message | browser check with a wrong chunk size and without API key |
| Outcomes | ok/error; four values | answered, abstained, invalid, error (the categories of the optional metrics page) | – |
| Cost | not shown; computed | tokens from the provider's `usage` × price table | unknown model → "unknown" |
| Metrics page | build; skip | skipped (optional) | – |
| Part B feature | 7 menu options | concept map explorer: fully checkable, no LLM call, reuses V3 | Kestrel only |
| Graph display | graph library; own SVG; list only | own SVG (about 30 lines) + list of links with sources | overlaps beyond ~12 neighbours |
| Part C feature | injection scanner; redaction | redaction | injection only mitigated by the prompt |
| Detection | patterns; NER library; LLM | patterns for e-mail and phone | names missed; 0 false positives on the corpora |
| Replacement | delete; fixed mask; numbered placeholders restored locally | numbered placeholders, restored in the answer | model may not copy them (problems 2 and 3) |
| Invented contact details | ignore; reject the answer; remove the value | remove when not among the hidden values, keep when equal to one | rejecting failed 3/3 on a correct answer |
| Where retrieval sees the question | redacted; original | original (retrieval is local) | – |
| Evidence sent to the LLM | trim to id/name/text; leave | left as in V3 | +4,650 tokens on hub questions, documented |

### Known failures and limits (V4)

- The eight live answers were graded by one reviewer on one run (7 correct, 1 partial); the earlier runs and the A/B runs were not graded. "Answered" alone only means the output passed validation.
- Redaction misses names and unusual formats; a correct-looking sentence around a removed contact is not checked.
- One trace file read in full for every Details view; single user, one request at a time.
- The concept map covers only what V3 extracted (17 of 43 chunks gave triples).
- Error messages from the graph retriever ("Graph chunk settings differ from the frozen extraction snapshot") are accurate but technical.
- After an update of the page files, a browser may keep the old JavaScript until the page is force-reloaded (seen once during the checks).
- Part C is presented in class in C10; if the session adds requirements, they are not reflected here.

## Final extension — graph of uploaded documents and configurable model (15 November 2026, Makuo)

Found while testing independently (see `reports/EXTERNAL_TESTING.md`): the concept graph only covered the frozen Kestrel snapshot, so a freshly uploaded file made the Concept graph retriever fail and its concepts never appeared in the map; and the app assumed Google Gemini.

- **Model settings.** `LLM_URL`, `LLM_API_KEY`, `LLM_MODEL` are read in one place (`rag_app/llm.py`) and used for answers and for graph extraction. Google stays the default and the old `GOOGLE_*` names still work. *Why:* any OpenAI-compatible provider works with one `.env` change. *Alternative:* a provider-specific SDK per vendor; rejected because the OpenAI-compatible endpoint is already what the code used.
- **Graph on upload (`rag_app/doc_graph.py`).** Generic schema instead of the Kestrel ontology, because an uploaded document has unknown entity types. Evidence stays strict (exact quote or dropped). *Alternative:* reuse the Kestrel types, which would extract almost nothing from non-Kestrel files. Built on upload up to 60 passages to bound cost; larger files use a manual button.
- **Retrieval and map.** The same traversal and scoring code (`GraphIndex`) is reused through a subclass, so graph paths, traces and fusion behave as for Kestrel. A missing graph no longer breaks a multi-retriever question.
- **Limits.** Extraction quality depends on the model; entities are merged by exact normalised name (no fuzzy matching); no graph for mixed Kestrel + uploaded selections; the graph is tied to the chunk settings used to build it.
- **Found while testing, then fixed (mixed selections).** With the five Kestrel files plus one extra file ticked, the Concept graph step returned "unavailable" and the question was answered "insufficient evidence", because the graph only ran when every selected file was one of its five. The graph now runs on the files it covers and lists the others as not covered (status "partial"). Evidence: before, dense and BM25 ranked the two service-catalog passages 8th–17th; with the graph they rise to fused ranks 2 and 3 and the answer cites them. *Alternative:* keep it all-or-nothing and document it; rejected because adding any extra file silently removed the most useful retriever.
- **Found while testing: Rich Text saved as `.txt`.** TextEdit saves rich text by default, so `lab.txt` was stored with RTF markup (`{\rtf1…`) inside the chunks. Uploads that start with an RTF header are now refused with advice to save as plain text.
