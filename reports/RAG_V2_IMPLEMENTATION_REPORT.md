# RAG V2 implementation report

## Status and authoritative scope

**Implementation and evaluation complete; release verification recorded below.**

Authoritative assignment: C7, Session 3, Part III, “RAG Project - V2” (14 PDF pages), supplied under ignored `/Tasks/`. Deadline: **November 3, 2026, 11:59 a.m. (Europe/Paris)**. C6's November 4 timeline is superseded. This report records implementation-agent work and verified facts, not fictional student decisions. Feras M completed the required Kestrel human grades and personally verified and confirmed all 15 Vellora no-context judgments after the initial AI-assisted assessments; both stages of Vellora review are recorded. C7 page 3 requests a student-written report: the owner must review and personalize the REPORT draft and decision log.

## Requirements extracted from C7

| PDF page | Requirement | Status and evidence |
|---|---|---|
| 2 | Deadline and team repo submission | PASS: corrected deadline and actual sole-developer details. Email submission is the owner's action, not performed by the agent. |
| 3 | Retain web RAG, schema validation, documents, selection, parameters, references and controlled failures | PASS: original service unchanged, original 30 tests still pass. |
| 4–5 | Kestrel and own corpus; supplied 10 plus >=10 own questions | PASS: five unchanged Kestrel documents, 10 unchanged starter questions; 15 frozen Vellora questions losslessly converted to JSONL. |
| 6 | Ask both sets without retrieval; flag questions answered correctly | PASS: real hosted calls saved; Kestrel human flags verified; all 15 Vellora no-context judgments human-verified and confirmed by Feras M after initial AI-assisted assessments, with both stages preserved. Keep all original questions, disclose flags. |
| 7–8 | Separate verification and evaluation; repeatable results file, CLI and frontend, k=1/3/5/10, per-type measures, >=2 configurations | PASS: four real retrieval runs, full evidence, hashes and metrics; shared evaluator behind CLI/API/UI. |
| 9 | Default retrieval only, opt-in generation; best config answers on one set, grading rules before hand grading, failure diagnosis | PASS: Kestrel 800/80 k=10 generation, prior rubric, all 10 owner grades/notes/reviewer names/flags verified and preserved. |
| 10–11 | Words corpus/question modes with justified choices | PASS: vocabulary/counts/chunk frequency, word-to-chunks with counts, picked/typed questions, present/absent words; API tests. Browser click-through incomplete. |
| 12 | Two missed-question diagnoses, one per corpus | PASS: exact Words function counts and target source chunks in `reports/words_diagnoses.json` and REPORT. |
| 13 | Unlinked `/about` page, exact prescribed sentence in large type | PASS: dedicated HTML route, content and lack of frontend link tested. |
| 14 | Both JSONL sets + no-context results, retrieval results + human grades, README/REPORT, v2 tag | PARTIAL: artifacts/docs implemented; evaluation complete; Git release recorded below. |

The document does not mandate hybrid search, reranking, query rewriting, a new embedding model, or a new chunking algorithm. Those were not added. C7 does require an evaluation runner despite C6's broader V3 “automated evaluation” roadmap; this implementation follows C7's concrete V2 instructions.

## Initial audit and preservation

Branch `main`, initially clean except the user-authorized `.gitignore` change for `/Tasks/`. Origin is `https://github.com/Ferasmich/norag-rag.git`; professor repository remains `upstream`. No unexpected tracked modifications were found. Local and remote `main` initially pointed to `c1efb7590907e478f3d5d5045e3b307be935bb9e`. The annotated `v1` tag object is `079f4e5d66d724606e61f705470414f4f20a57df`; it dereferences to the same commit. No `v2` existed in the initial remote audit.

Read README, REPORT and the preserved V1 implementation report; inspected models, service, API, UI, tests and evaluation. V1 uses exact fixed character windows, MiniLM/Chroma cosine search, selected-document filtering, then Gemini structured JSON and citation membership validation. V2 extends that application without replacing it.

Actual pre-change checks: `30 passed in 9.47s`; original evaluator wrote only `/tmp/epita-v1-reproduced.json` and reproduced **7/12 Hit@5**. Original evaluation dataset, baseline, corpus, V1 report and core service remain unchanged.

## Implementation and files

- `.gitignore`: ignores the complete root `/Tasks/` tree. No Tasks path is staged or tracked.
- `docs/kestrel/*.md`: five unchanged copies of course corpus documents; include both current and superseded billing policies.
- `evaluation/kestrel.jsonl`: unchanged starter questions.
- `evaluation/vellora.jsonl`: V1 questions converted to Kestrel-format evidence arrays and type labels; original `questions.json` unchanged.
- `evaluation/v2.py`: shared real-retrieval evaluator, k-prefix metrics, per-type groups, optional validated answer generation, separate no-context calls, corpus/dataset hashes, rubric, complete evidence snapshots, CLI and UUID result saving. Refuses to overwrite an existing CLI output. Saves hosted errors per question. Hosted calls are spaced six seconds apart on real runs.
- `rag_app/words.py`: small dependency-free Unicode lexical analyzer over exact selected chunks. No vector or LLM request is needed.
- `rag_app/models.py`: bounded Words/evaluation/review inputs, fixed corpus names and grade vocabulary, strict booleans and review validation.
- `rag_app/api.py`: search, Words, fixed corpus loading, question sets, evaluation runs, safe saved-run retrieval, human review and measured-run import routes. `/about` serves prescribed large text without frontend references.
- `rag_app/static/index.html`, `app.js`, `style.css`: Ask/Evaluation/Words tabs within the existing interface, corpus load, opt-in hosted operations, saved results, human review/export, vocabulary and question-word exploration. All untrusted text remains textContent.
- `tests/test_v2.py`: focused tests for frozen datasets/corpus, lexical counts/offsets/filtering, metric semantics, real retrieval with mock generation, routes, saved review, import safety and failure recording.
- `evaluation/results/*.json`: actual measurements and hosted responses/errors; no local vector DB files.
- `reports/words_diagnoses.json`: reproducible word-count evidence and answer windows for two diagnoses.
- README and REPORT: startup/evaluation/review instructions, exact scope, decisions, actual tables and known failures.

## Retrieval methods and decision rationale

No new retriever: same `all-MiniLM-L6-v2` 384-dimensional CPU embeddings and Chroma cosine index, exact character windows, selected document metadata filter before top-k. Config A uses 800-character size / 80 overlap (V1); config B uses 500 / 100. Changing chunk settings creates distinct existing-style collections; changing top-k reuses vectors. The default app remains 800/80/k=5 because results do not show a universal improvement.

Each corpus is evaluated in an isolated temporary service/index. Kestrel indexes all five files, including the old billing policy, rather than cherry-picking expected evidence. Vellora indexes the unchanged manual. One depth-10 ranking is scored at k=1/3/5/10. The CLI and frontend share the same evaluator and application retrieval service; `/api/search` exposes the same retrieval method for HTTP callers. Browser evaluation is independent of unrelated library uploads; Words deliberately uses checked library documents instead.

HitRate@k means at least one expected exact quote from its expected source is contained in a retrieved chunk. For Vellora there is one quote per answerable question, making it identical to the V1 metric. Kestrel often needs several quotes: macro quote recall reports their fraction found per question, then averages across answerable questions. A hit alone is not complete evidence and not answer accuracy. Unanswerable questions are excluded from both metrics and retained as response/abstention cases.

Words tokenization uses case folding and Unicode word characters, retains internal hyphens/apostrophes (`KST-2044` stays one token), does not stem or remove stopwords, and counts occurrences in chunk windows. Overlap repeats count again. This choice is explicit and testable, avoids adding a framework, and makes absence/identifier diagnoses inspectable. Returned chunks retain exact offsets and start lines.

## Actual verification

- Baseline before code changes: `.venv/bin/python -m pytest -q` — **30 passed in 9.47 seconds**.
- V2 expanded suite: same command — **40 passed in 8.32 seconds** on the final release-preparation rerun. Real MiniLM and Chroma, hosted generation mocked in tests.
- Original evaluator: `.venv/bin/python -m evaluation.run --output /tmp/epita-v1-reproduced.json` — **7/12 = 58.3% Hit@5**; original committed baseline not overwritten.
- Four actual CLI retrieval runs: `evaluation.v2` on Kestrel and Vellora, each at 800/80 and 500/100 — completed successfully, metrics below.
- Actual HTTP `POST /api/evaluations` with Kestrel 800/80/k=10 and both hosted options: saved real generation/no-context responses. Initial run had six generation and six no-context errors; retained unchanged. Paced rerun: **10/10 generated responses and 10/10 no-context responses, no recorded hosted errors**.
- Initial Vellora no-context run: 9 responses and 6 errors, preserved. Paced rerun: **15/15 no-context responses, zero recorded hosted errors**. Both fixed question sets with actual no-context responses are also exported as `evaluation/results/kestrel-no-context.jsonl` and `vellora-no-context.jsonl`; Kestrel human flags are verified; all 15 Vellora judgments were initially AI-assessed and subsequently human-verified and confirmed by Feras M, with both stages recorded.
- Live HTTP GET `/`, `/app.js`, `/style.css`, `/api/question-sets`, `/api/measured-runs`, `/about`: **200** with the documented server running.
- `node --check rag_app/static/app.js`: **PASS** after formatting.
- `.venv/bin/pip check`: **No broken requirements found**.
- `git diff --check`: **PASS** at current review preparation.
- Actual native Chrome: V2 page rendered, Evaluation tab opened, Kestrel loaded and selected with five sources, retrieval evaluation launched and server returned 200. Browser access later timed out after focus changed. **PARTIAL**, no full result-rendering/Words/grade click-through or responsive-layout pass claimed.
- A first ad hoc HTTP check used system `python3`, which lacked requests; it was rerun successfully with the documented `.venv/bin/python`. This was an interpreter-selection issue, not a passing test.

## Actual retrieval results

Full overall/per-type tables and per-question Hit@5 differences follow. Raw files record all k-prefix hits, quote recall, similarities, chunk text and metadata.
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

V1 versus V2 on the original Vellora set: 800/80 stays at **7/12 (58.3%)**, while 500/100 reaches **8/12 (66.7%)** at k=5. q01 and q09 improve, q12 worsens, the other nine answerable questions are unchanged. Kestrel at k=5 decreases from **7/8 (87.5%)** to **6/8 (75.0%)**, losing q08; the other seven answerable questions are unchanged. At k=1 smaller windows are worse on both. At k=10 both configs tie on any-quote HitRate, but 800/80 has greater Kestrel quote recall (93.75% versus 90.625%). Kestrel 800/80/k=10 is therefore used for the required best-config answer review. No question text/expected quote was changed to improve scores.

## Diagnosed failures and remaining limitations

Words analysis at 800/80 finds 43 chunks per corpus. Kestrel q01 misses expected quotes at k=5 even though the unique `kst-2044` word occurs in exactly one answer-bearing chunk; generic `error` occurs in 9 chunks and `and` in 43. `mean`, `i`, `fix` are absent. Vellora q11 misses at k=5: `sits` and `unused` are absent; `machine` occurs in 38 chunks; the expected window contains `three`/`weeks` but lacks `preparation`, `needed`, `after`. The counts and exact source excerpts are in `reports/words_diagnoses.json`. Possible interpretations—digit underweighting and paraphrase/common-word dilution—are hypotheses for owner review, not established internal model explanations.

Observed generated Kestrel answers require human scrutiny: q08 abstains on an answerable two-hop question; q06/q07 discuss both policy versions instead of clearly selecting the current policy. Quote recall@10 for two-hop is 50%, which helps distinguish missing retrieval evidence from a generation-only failure. Other generated answers can omit expected details. None is labeled correct automatically. The owner must enter correct/partial/wrong/unsupported and explain the retrieval/generation diagnosis for wrong answers using the saved evidence. No-context responses include abstentions, generic advice and an unrelated real-world Kestrel app claim; these are actual outputs, not verified facts about the fictional corpus.

Grading rules were encoded before generation. Original questions are retained for comparability even if prior-knowledge flags are true. Human review should flag an answer only if it supplies the expected corpus facts; abstention is not prior knowledge. On unanswerable RAG questions abstention is correct, answering anyway wrong. Kestrel human grade counts are reported below without claiming general accuracy.

All V1 limits remain: MiniLM input truncation, exact-code failures, no calibrated relevance threshold, schema/citation integrity does not prove semantic grounding, process-local locks, no authentication or multi-user isolation. Frontend runs are synchronous and may take minutes. Words emits all matches and is intended for course-sized corpora. No V3/V4 features were added. Student personalization of the AI-assisted report remains the owner’s responsibility; submission email was not sent.

## Security and Git checks

`/Tasks/` is ignored and untracked; runtime copies are outside Tasks, and PDFs are not proposed for commit. `.env`, local databases, uploads, caches and the virtual environment remain ignored. The existing service keeps credentials server-side and renders model/source text safely. No new dependencies. Candidate tracked-file scan against actual local API secret values found **zero matches**. Course corpus and starter copies were verified byte-identical to the local supplied material. `git ls-files Tasks .env data chroma_db` is empty; frozen V1 service, corpus, dataset, baseline and report compare unchanged against `v1`. Final staged-path scan passed for all 32 implementation files; no secret-value matches, Tasks paths, environments or databases were staged. The agent will not force-push, change `v1`, overwrite an existing `v2`, or write to upstream.

Release hashes and verified GitHub status are recorded in `reports/V2_FINAL_SUBMISSION.md`. The final release SHA is resolved from the annotated `v2` tag; a tracked report cannot embed its own commit hash.

## Startup and Q&A explanation

From the repository root:

```bash
source .venv/bin/activate
python -m uvicorn rag_app.api:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. No separate frontend process. Install with `pip install -r requirements-dev.txt` in a Python 3.12 virtual environment if needed, then configure GOOGLE_API_KEY in ignored `.env` for hosted calls.

For the professor: the RAG pipeline is unchanged. V2 adds controlled experiments on two fixed corpora and tools to inspect lexical misses. Chunking changes the text embedded and therefore the ranking; top-k only changes how much of that ranking is supplied. A lexical word can be uniquely present yet dense search can still miss it. HitRate measures at least one expected quote; quote recall exposes partial multi-hop evidence. Neither measures generated-answer quality, which is why actual answers/references and manual grades are saved separately. No-context checks test whether the question requires retrieval at all. C7’s comparison shows a measurable Vellora gain with smaller chunks and a Kestrel regression, so it does not justify replacing the default globally.



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


## Release verification record

Verified implementation commit: `c7b4c1deee2629b67e6ffd31edf4fa92e64a23ca`. Pushed to `origin/main` successfully; `git ls-remote origin refs/heads/main` matched that exact SHA. A final documentation-only commit adds `V2_FINAL_SUBMISSION.md`; the annotated `v2` tag identifies the final release commit including that report. Final commit/tag hashes are resolved and checked against GitHub after publication. V1 remains `c1efb7590907e478f3d5d5045e3b307be935bb9e`, annotated object `079f4e5d66d724606e61f705470414f4f20a57df`.


## Post-release Vellora human confirmation

Feras M completed human verification and explicitly confirmed all 15 proposed no-context judgments in chat after reviewing the question/expected-answer/response summary table: **Yes for q09 and q10, No for the other 13**. The confirmation concerns the no-context flags, not a new Vellora RAG-answer grading experiment. `evaluation/results/vellora-reviewed.json` and `vellora-no-context.jsonl` now record the verifier, confirmation timestamp, rationale and review history. Original AI assessor metadata remains unchanged, including its historical `human_reviewed: false` value at the time of the AI-only assessment; the subsequent `human_verification` event records the later confirmation. `vellora-ai-assessed.json` remains byte-for-byte intact. All 10 Kestrel human reviews are unchanged. The original v2 release snapshot contains the initial AI-only assessments; the subsequent human confirmation is recorded in the follow-up artifacts. Final V2 documentation reflects completed human verification by Feras M.

This is a follow-up on main, not a new release. The existing annotated v2 tag remains object `07ff1e7d3262b4fbbb589eb97921cfa1803d1d20`, pointing to release commit `2a223476c8df74ae6e0464fada5c277f39aaa984`. Main is expected to advance beyond that tag. No evaluation questions, model responses, retrieval metrics or application code changed.

Follow-up validation: 40 tests passed in 8.26 seconds; all 15 confirmations and original AI/Kestrel artifact integrity checked; git diff whitespace check passed.
