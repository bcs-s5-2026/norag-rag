# RAG V2 post-submission audit

> **Documentation follow-up — 9 November 2026:** V2 human verification was completed and recorded by **Feras M for all 15 Vellora no-context judgments**, after the initial AI-assisted assessments (true for q09/q10; false for the other 13). README, REPORT and the V2 implementation/submission reports now state both stages consistently. The superseded-review-wording warning below records the earlier audit finding and is resolved by this documentation correction. Original evaluation records, review history, provenance and results remain unchanged; the historical v2 tag is unchanged. Other findings below retain their original audit scope.

Audit date: November 3, 2026 (Europe/Paris). Scope: read-only Git/GitHub, code, records and documentation inspection; automated checks; this local report only. The owner states the assignment submission email has already been sent. This audit did not independently access email or contact the professor.

## Verdict

**PASS for the verified implementation, evaluation records and remote publication, with documentation and release-reference WARNINGS. No critical defect or failed automated check was found. No application change or tag movement is presently required before grading.** If the professor is grading only the v2 checkout, the later Vellora human confirmation will not be visible there; the current main commit below is the complete confirmation reference. That distinction warrants clarification only if the submitted instructions restrict grading to the tag.

| Area | Result | Evidence / implication |
|---|---|---|
| Remote main and Git history | PASS | origin/main is exactly a1e7e0c48d5ad4226d56eb73bbf36377f0039c4d; all six post-v2 files downloaded from GitHub at that SHA match local bytes. |
| v1 preservation | PASS | Local/remote annotated tag object and target unchanged; frozen V1 code/data/report compare unchanged. |
| v2 release reference | WARNING | Correct, unchanged release tag; intentionally one commit behind main, without Vellora human confirmation. Not a broken tag or missing implementation. |
| Kestrel human grades | PASS | All 10 intact, attributed, timestamped and consistent across reviewed JSON and no-context JSONL. |
| Vellora human confirmations | PASS | All 15 recorded in JSON/JSONL; Yes only q09/q10; Feras M attribution, timestamp, reasons and two-stage history verified. |
| Metrics and provenance | PASS | Recalculated from stored evidence; four fresh real CLI runs reproduce all overall/per-type/per-question results. Retrieval, RAG grades and no-context flags remain separate. |
| Tests and critical code | PASS | 40 automated tests passed; JS syntax, dependency and whitespace checks passed. No critical error found in inspected paths. |
| Reproduction limits | WARNING | No new clean-machine installation, live hosted-generation run or full interactive/responsive browser pass in this audit. |
| Secrets / tracked artifacts | PASS with privacy note | No tested secret patterns or configured secret values in 86 reachable Git blobs; no Tasks/env/database/cache paths tracked. A pre-existing local home-directory path remains in the preserved V1 report. |
| Documentation consistency | WARNING | Explicit outdated email-status text and superseded AI-only descriptions remain, despite later human-confirmation sections. |

## Exact GitHub and Git references

- Repository / origin: https://github.com/Ferasmich/norag-rag.git
- Main: https://github.com/Ferasmich/norag-rag/commit/a1e7e0c48d5ad4226d56eb73bbf36377f0039c4d
- v2 commit: https://github.com/Ferasmich/norag-rag/commit/2a223476c8df74ae6e0464fada5c277f39aaa984
- v2 annotated tag object: 07ff1e7d3262b4fbbb589eb97921cfa1803d1d20
- v1 commit: c1efb7590907e478f3d5d5045e3b307be935bb9e
- v1 annotated tag object: 079f4e5d66d724606e61f705470414f4f20a57df

`git ls-remote origin` verified all branch/tag values against local refs. Initial working tree was clean. `git log` shows one post-v2 commit, “Record Feras M confirmation of Vellora no-context assessments”, committed November 3 at 11:31:01 +01:00. No remote, branch, tag or history was modified by this audit.

## All six files in v2...main

Inspected the complete documentation diff and parsed the actual changed JSON/JSONL records, including preserved original fields and new human-review metadata. Each of the following was also retrieved over HTTPS from raw.githubusercontent.com at the exact main SHA and compared byte-for-byte:

| File | Verified post-tag change |
|---|---|
| README.md | Adds human-confirmation and preserved-tag explanation. |
| REPORT.md | Adds human-confirmation explanation and follow-up test result. |
| evaluation/results/vellora-no-context.jsonl | Adds reviewer, confirmation timestamp, rationale, human verification and review history to the same 15 question/response records. |
| evaluation/results/vellora-reviewed.json | New full reviewed snapshot; original AI assessment fields/evidence retained, with human confirmation metadata and human confirmation notes. |
| reports/RAG_V2_IMPLEMENTATION_REPORT.md | Adds human-confirmation explanation and follow-up test result. |
| reports/V2_FINAL_SUBMISSION.md | Clarifies main advancing beyond v2; adds human confirmation and follow-up test result. |

No post-tag application, test, corpus, retrieval algorithm or evaluator code change exists. Diff totals: six files, 2,765 insertions and 16 deletions, mostly the full reviewed evidence snapshot. The large JSON is an intentional reproducibility artifact, not a local database or unexplained generated output.

## Actual evaluation-record audit

### Kestrel

`kestrel-reviewed.json` is byte-identical to the v2 snapshot. All 10 entries contain a valid grade, nonblank notes, reviewer Feras M, parseable timestamp and explicit boolean no-context flag. Its JSONL companion agrees on question, expected answer/evidence, actual no-context response, flag and review metadata.

Grades: q01 correct; q02 partial; q03 correct; q04 partial; q05 partial; q06 correct; q07 correct; q08 wrong; q09 correct; q10 correct. Totals: **6 correct, 3 partial, 1 wrong, 0 unsupported**. All 10 no-context flags are false. Review timestamps range from 2026-11-03T10:01:40.140031+00:00 to 2026-11-03T10:11:52.557667+00:00 (11:01:40–11:11:52 Paris).

Citation IDs in each saved generated response belong to its actual retrieved set; the reference IDs equal the cited IDs. This verifies citation integrity, not universal semantic support. The human judgments on q06/q07 are preserved; version-selection caveats in the report remain legitimate qualitative limitations rather than grounds to silently change those grades.

### Vellora

Parsed all 15 entries in both `vellora-reviewed.json` and `vellora-no-context.jsonl`:

| Question | no_context_correct | Human verifier |
|---|---|---|
| q01 | false | Feras M |
| q02 | false | Feras M |
| q03 | false | Feras M |
| q04 | false | Feras M |
| q05 | false | Feras M |
| q06 | false | Feras M |
| q07 | false | Feras M |
| q08 | false | Feras M |
| q09 | true | Feras M |
| q10 | true | Feras M |
| q11 | false | Feras M |
| q12 | false | Feras M |
| q13 | false | Feras M |
| q14 | false | Feras M |
| q15 | false | Feras M |

All confirmations have timestamp **2026-11-03T10:30:46.188366+00:00**, equivalent to **11:30:46.188366 Paris**. A shared timestamp correctly represents the owner's single explicit confirmation of all 15 proposed judgments, not 15 fabricated independent review sessions. Each row includes confirmation rationale and `human_verification` with verifier/method/confirmed flag. JSON and JSONL histories agree.

The original `vellora-ai-assessed.json` is byte-identical to its v2 copy. In the reviewed snapshot, its original fields remain equal except the originally empty grade_notes now contains the confirmed rationale. Each `review_history` contains an AI-assessment event followed by human confirmation. Historical `assessment_provenance.human_reviewed: false` describes the original AI event; it does not negate the later human_verification event. This distinction is explicit in the records, though consumers must read the complete provenance rather than that isolated boolean.

q09 supplies both powered-on and five-second removal facts; q10 supplies no dishwasher plus removal of necessary lubricant. q04 is only a generic/incomplete match. q13–q15 abstentions do not count as prior knowledge. Vellora RAG grade fields remain null: this is a no-context verification exercise, not fabricated RAG-answer grading.

### Retrieval / answer / no-context separation

For all four original retrieval configurations, checked dataset/corpus SHA-256 hashes, each retrieved text against its source character offsets, expected source/quote matches, per-question hit/quote-recall arrays, overall aggregates and every type aggregate. Unanswerable questions are excluded from retrieval denominators. No-context flags and RAG human grades are not used to calculate retrieval scores.

| Corpus | Size/overlap | Hit@1 | Hit@3 | Hit@5 | Hit@10 |
|---|---|---|---|---|---|
| Kestrel | 800/80 | 5/8 | 7/8 | 7/8 | 8/8 |
| Kestrel | 500/100 | 2/8 | 6/8 | 6/8 | 8/8 |
| Vellora | 800/80 | 6/12 | 6/12 | 7/12 | 10/12 |
| Vellora | 500/100 | 2/12 | 6/12 | 8/12 | 10/12 |

All four fresh CLI runs reproduced every overall/per-type/per-question metric, not just these summary counts. Kestrel's any-quote HitRate@10 is 100% while quote recall is only 93.75% at 800/80; partial two-hop evidence and q08's wrong abstention are therefore not contradictory. Vellora 2/15 no-context matches are a different measure from its retrieval Hit@5 and from Kestrel's 6/10 correct RAG answers.

## Checks actually executed

- `.venv/bin/python -m pytest -q`: **40 passed in 8.06 seconds**. Real embeddings/Chroma; hosted model mocked by the automated suite.
- `node --check rag_app/static/app.js`: exit 0.
- `.venv/bin/pip check`: no broken requirements.
- `git diff --check`: exit 0.
- Four subprocess CLI runs of `python -m evaluation.v2`, on each corpus at 800/80 and 500/100. Fresh output in a temporary directory; all results matched saved metrics; temporary outputs removed. No original baseline/evaluation files overwritten; no hosted LLM calls made.
- Remote branch/tag queries; byte comparisons for six GitHub-hosted changed files; JSON/JSONL review assertions; saved citation-membership assertions; hash/source-offset/metric recalculations.
- Read critical functions in service, models, API, evaluator, Words and frontend review paths. Selected-document filtering occurs before top-k; exact source snapshots build references; strict generated-answer validation and citation membership remain; evaluation uses isolated corpora; Words reuses exact chunk windows.
- Compared the preserved V1 service, CLI demos, original evaluator, dataset, baseline, corpus and V1 report with v1: no differences. Original baseline remains 7/12 Hit@5; new CLI reproduces the same score at identical Vellora settings.

No new hosted-generation, full browser interaction or fresh-machine dependency installation pass is claimed. Saved real hosted responses were inspected and preserved. Existing tests and CLI reproduction provide strong local verification, not a guarantee for every OS/provider account.

## Security, privacy and unnecessary files

Scanned **86 reachable Git history blobs** for exact configured API secret values and selected Google/GitHub/OpenAI key and private-key patterns: no matches. Pattern/exact-value scanning is bounded; it is not a guarantee that no conceivable secret format exists. No tracked `.env`, Tasks tree, virtual environment, Python cache, upload directory or local vector database. `.env.example` contains a placeholder. No non-.example email-like strings were found in tracked file contents. Git author metadata contains three distinct contributor identities, ordinary history attribution rather than leaked credentials.

Deliberate reviewer attribution (Feras M) and GitHub identity are expected. A local `/Users/...` workspace path exists in `reports/RAG_V1_IMPLEMENTATION_REPORT.md`; it exposes a username/directory layout, not a credential. **Minor privacy warning**: preserve it during this audit/V1 freeze; cleanup is optional only with explicit approval. Pre-existing course agent templates and novel files are baseline artifacts, not new accidental submission files. Failed hosted-run snapshots are intentionally retained as truthful evidence; reviewed/final files are clearly named. No urgent deletion is indicated.

## Documentation warnings and reproduction risks

1. **Outdated email status:** `reports/V2_FINAL_SUBMISSION.md:31` says the submission email was “not sent”; `reports/RAG_V2_IMPLEMENTATION_REPORT.md:157` also says it was not sent. These now conflict with the owner's explicit statement that it has been submitted. Statements that the agent did not send email are historically true; the blanket current-status statements are stale. This audit records **email sent, per owner**. No existing document was edited.
2. **Superseded review wording:** README line 109 says no human Vellora review is claimed; final submission report line 23 and earlier REPORT/implementation sections describe AI-only review and an untouched blank runtime copy. Later “Post-release Vellora human confirmation” sections correctly supersede those descriptions, and actual main JSON/JSONL records are complete. Minor narrative inconsistency, not missing reviews. A future approved documentation-only cleanup could consolidate the status.
3. **Reproduction prerequisites:** Python 3.12, installed dependencies, writable storage and first-use model access/cache are needed. Hosted generation requires a valid Google key and available model; provider availability is external and not newly tested here. The lock file documents a macOS/Python 3.12 environment; a clean non-macOS install was not tested. The documented V2 CLI worked in this workspace.
4. **Preserve baseline when reproducing:** the older README command `python -m evaluation.run` writes the V1 baseline by default. Prefer V2 commands with fresh output paths, or pass the old evaluator an explicit temporary --output path. The audit did not overwrite the baseline.
5. **Minor future-edit provenance risk:** the existing grade API updates current review fields but does not append to an already imported review_history/human_verification structure. Current committed records are internally consistent. Re-saving an imported reviewed artifact later with changed decisions would require deliberate provenance maintenance; this is not a current grading blocker and no code fix was made.
6. **Schema limits:** references are structurally valid, not proof every factual assertion is supported. Dense identifier/two-hop failures, partial answers and non-universal chunk-size improvements are honestly reported. Full interactive/responsive UI testing remains a disclosed gap, not an invented pass.

## Is the earlier v2 tag acceptable?

**Yes as an immutable release snapshot, with a visibility warning.** It contains the implementation, full retrieval comparison, Kestrel human grades and AI-assessed Vellora flags. main adds only the human-confirmation records and documentation; both versions use the same application code. The tag is not corrupt or accidentally pointing at V1. C7's hand grading on one question set is represented by Kestrel in the tag already. However, a professor checking out only v2 will not see `vellora-reviewed.json` or the later human confirmation. Latest confirmed evidence is on main at a1e7e0c48d5ad4226d56eb73bbf36377f0039c4d.

The audit cannot determine from Git alone whether the submitted email requested a tag-only checkout or what exact grading rule the professor will apply. **Do not move v2 automatically.** If clarification is actually needed, identify the follow-up main commit; create another release only by explicit decision. No mandatory code change, regrading, automatic tag movement or second submission is indicated by the evidence inspected.

## Action and audit-only preservation

No critical action required before grading on current main. Optional owner-approved documentation cleanup could acknowledge the sent email and consolidate superseded review wording. Conditional clarification of main versus v2 may help only if the professor expects the later confirmation while grading the tag alone. The email is already submitted according to the owner; no message was sent by the audit agent.

Only this local audit report was created. No commit, push, amend, reset, history rewrite, tag change, application edit or evaluation-file edit was performed. The report is deliberately uncommitted and is not claimed to be available on GitHub.
