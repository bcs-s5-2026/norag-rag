# V4 final verification — 12 November 2026

Checked against the professor's handout "C9-C10 – RAG Project – V4 – The final release" (23 pages, local `Tasks/` folder). State verified: working tree on `main` at `cd0a0b9` plus the V4 changes listed at the end. These changes were then committed and tagged `final` after Feras's approval on 12 November 2026.

Status meanings: **PASS** = implemented and verified by a test, a script or a browser check that was actually run. **WARNING** = done, with a limit or a step that only the team can complete. **FAIL** = not done.

## Requirements

| # | Handout requirement (page) | Status | Evidence |
|---|---|---|---|
| 1 | Submit by e-mail with repo link and git tag `final`, CC teammates, by Sunday 15 November 11:59 (p. 2) | **WARNING** | Commit and tag `final` published after Feras's approval (commands below). The e-mail to the professor is sent by Feras and is not part of this verification. |
| 2 | Easy to install and run from the README (p. 4) | **WARNING** | README starts with a Quick start (6 commands, one secret, 4-step first run). Checked on this machine with a second server using an empty data folder and no API key. Not checked on a fresh clone on another computer. |
| 3 | Natural to use for a non-programmer; what happens when something goes wrong or takes time (p. 4) | **PASS** | Demo button, settings folded, status messages while working, "No answer this time" + reason + Details on failure. Browser checks B1, B3, B8. |
| 4 | Start V4 with a clean-up (p. 4) | **PASS** | REPORT "Clean-up"; raw JSON removed from the answer, baseline panel moved. |
| 5 | A. One trace per question, one span per step (p. 7) | **PASS** | `test_question_trace_has_one_span_per_step`, `test_legacy_ask_without_retrieval_is_traced`; browser B1. |
| 6 | A. One trace per indexing run (p. 7) | **PASS** | `test_indexing_run_trace`, `test_automatic_indexing_is_traced_once`; browser B4. |
| 7 | A. Never in a trace: API keys, whole documents (p. 7) | **PASS** | Traces hold chunk ids only (test asserts no chunk or answer text); the key is never passed to the tracing code. |
| 8 | A. Personal data in traces: decide and explain (p. 7) | **PASS** | Question stored after redaction; REPORT Part A; `test_personal_data_never_reaches_the_llm_or_the_trace`; names remain (stated). |
| 9 | A. Every answer has a way to open its trace, showing relevant information for that request (p. 8) | **PASS** | Details button on answers, errors, indexing status, concepts; browser B1–B5. |
| 10 | A. Decision log answers the four questions (p. 9) | **PASS** | REPORT "Decision log questions (handout page 9)". |
| 11 | A. Optional metrics page (p. 10) | not required | Not built. |
| 12 | B. One feature from the menu for a team of 2 (p. 5, 12) | **PASS** | Concept map explorer. |
| 13 | B. Display the graph or a neighbourhood; click a concept: links, relations, source chunks; ask a question or open documents from a concept (p. 15) | **PASS** | `test_concept_list_and_neighborhood`, `test_every_link_and_mention_points_to_real_source_text`; browser B6. |
| 14 | B. Traced like the rest of the app (p. 13) | **PASS** | Concept lookup trace with two spans; a question asked from a concept is a normal question trace. |
| 15 | B. Its cost: LLM calls, tokens, latency (p. 13) | **PASS** | REPORT Part B: 0 calls, ~1 ms per lookup; cost of questions asked from concepts measured. |
| 16 | B. Its failures: what the user sees (p. 13) | **PASS** | 404 / 503 messages; `test_unknown_concept_and_missing_graph`. |
| 17 | B. Checked on several cases including difficult ones, written in the report (p. 13) | **PASS** | `offline_2026-11-12.json`: 42 concepts, 156 quotes, 0 wrong; findings in REPORT. |
| 18 | C. One responsible-AI feature for a team of 2 (p. 5, 21) | **WARNING** | Personal data redaction implemented and tested. Part C is presented in C10; the 23-page handout gives only the menu, so later requirements cannot be checked here. |
| 19 | C. Detect personal data and replace it before the LLM call and before the trace (p. 21) | **WARNING** | E-mail and phone: PASS (tests, live trace-file checks). Names, which the handout lists as an example ("names…"), are not detected. Stated in REPORT. |
| 20 | C. Detection method chosen and explained in the decision log (p. 21) | **PASS** | REPORT Part C and decision log. |
| 21 | Team size rules (p. 5) | **WARNING** | Two-person requirements applied (Feras Michael, Makuochukwu Okoene). If a third member is confirmed, a second Part B feature and the injection scanner would be required and are not implemented. |

## Engineering audit

| Check | Status | Result |
|---|---|---|
| Automated tests | **PASS** | `python -m pytest -q`: 174 passed (150 existing, unchanged, + 24 in `tests/test_v4.py`). `node --check rag_app/static/app.js`: OK. |
| V1–V3 retrieval unchanged | **PASS** | V3 evaluation re-run on the final code, 7 configurations: 81/81 identical ranked lists, identical metrics (`evaluation/results/v4/retrieval_regression_2026-11-12/comparison.json`). |
| V1–V3 functions | **PASS** | Covered by the 150 earlier tests (upload, delete, index, dense/BM25/graph, RRF, evaluation API, Words, grading). Evaluation and Words tabs were not re-exercised by hand in the browser. |
| Trace persistence and privacy | **PASS** | Traces survive a server restart (Recent activity listed earlier traces after restarts); pruning tested; no e-mail or phone in the trace file after the live runs and in the local `data/traces/traces.jsonl` (19 traces, 0 matches). |
| Redaction edge cases | **PASS** | 11 detection cases as expected; sentence-final phone; IP, date, decimal not matched; 0 false positives on both corpora. |
| Error handling | **PASS** | Invalid LLM output → 502 + trace "invalid"; pipeline error → trace "error"; no API key → clear message + trace; unknown trace/concept → 404. |
| Credentials | **PASS** | `.env` is git-ignored and was never committed; pattern scan of tracked and new files finds only the placeholder in `.env.example`. |
| Tags and history | **PASS** | `v1` 079f4e5, `v2` 07ff1e7, `v3` ce76444 identical locally and on origin. No file under `evaluation/results/` (V1–V3), `concepts/` or the question sets is modified; all V4 results are new files. |
| Local change in `rag_app/static/app.js` | **PASS** | The pre-existing uncommitted edit (Recall@5 0.79, two-hop 0.89) is preserved inside the V4 version of the file; it matches the final V3 numbers in REPORT. |

## Browser checks (run on 12 November 2026, final code)

| # | Check | Result |
|---|---|---|
| B1 | Load demo → ask the sample question → answer, references, Details with 7 steps, tokens and cost | OK (3407 in / 202 out, $0.001527) |
| B2 | Question with an e-mail and a phone → answer contains the corpus address; Details shows `[EMAIL_1]`, `[PHONE_1]`, "emails: 2, phones: 1"; raw values absent from the trace view | OK |
| B3 | Failed question (graph ticked with chunk size 500) → red message, Details opens the trace with outcome "error", answer area shows "No answer this time" | OK |
| B4 | Prepare documents now → status with Details → indexing trace | OK (documents already indexed: only the BM25 step listed). The first-time case with one `embed_document` step per document is covered by a test and by the live script, not by a browser click. |
| B5 | Recent activity lists questions, indexing runs, outcomes | OK |
| B6 | Concept map: select *Public share links*, 4 neighbours drawn, link shows its source quote and the 800-character chunk, clicking a neighbour moves to *Business*; earlier run: *Ask a question about this concept* fills the Ask tab | OK |
| B7 | Second server without API key and with an empty data folder: demo loads, question fails with "Set GOOGLE_API_KEY in .env to generate answers.", Details shows the failed LLM step, concept map works | OK |
| B8 | Browser console | No JavaScript error. Only the expected "Failed to load resource" lines for the deliberately failed requests (400, 502, 503). |

Not run in the browser: upload of a personal file through the file picker, the Evaluation and Words tabs, narrow/mobile widths, other browsers than the built-in one.
Seen once: after the page files changed, the browser served the old `app.js` from its cache until a forced reload.

## Measurements

- Live questions (final code): 8 calls, 7 answered, 1 abstained (the not-in-corpus question); median 1.33 s (LLM 1.31 s, retrieval 25 ms); 31,461 / 1,962 tokens; $0.0143.
- Hard redaction case (personal data in the question + hidden corpus address needed): 3/3 correct on the final code.
- Indexing run: 5 documents, 43 chunks, 6.1 s, 0 LLM calls.
- Concept lookups: median 1.0 ms, 0 LLM calls.
- Token finding: 8,055 input tokens for the *Enterprise* question (84 graph path ids in the evidence; 12,714 vs 4,827 characters). +$0.0014 on such questions. Documented in REPORT, not changed.
- API cost of all V4 work: about 44 calls, about $0.07, `gemini-3.5-flash-lite`, Kestrel course documents and fictional personal data only.

## Known limitations

Names not redacted; concept map limited to the V3 Kestrel graph; traces in one flat file for one user; no metrics page; technical wording of graph errors; small question sets. Full list: REPORT "Known failures and limits (V4)".

## Human review status

- The eight live answers were reviewed by Feras M on 12 November 2026: 7 correct, 1 partial (two-hop question: after-hours escalation to Platform missing), 0 wrong, 0 unsupported. Recorded verbatim in `evaluation/results/v4/live_final_2026-11-12-REVIEW.csv` (and `.md`) and in REPORT.
- The report text, the decision log and the presentation guide were drafted with an AI assistant from the code and the saved results. They need to be read and adjusted by the team.

## Git status

Branch `main`, HEAD `cd0a0b9`, in sync with `origin/main` before these changes.

Modified: `README.md`, `REPORT.md`, `rag_app/api.py`, `rag_app/service.py`, `rag_app/static/app.js`, `rag_app/static/index.html`, `rag_app/static/style.css`.
New: `rag_app/tracing.py`, `rag_app/redaction.py`, `rag_app/concept_map.py`, `tests/test_v4.py`, `evaluation/v4_checks.py`, `evaluation/results/v4/`, `reports/V4_FINAL_VERIFICATION.md`, `reports/V4_PRESENTATION_GUIDE.md`.

## Remaining actions before submission

1. Feras: read REPORT (V4 section) and the presentation guide; correct anything that is not how the team would say it.
2. Done: the eight live answers are graded and the result is in REPORT.
3. Team: confirm the team list (two or three members) and the e-mail recipients.
4. Optional but recommended: clone the repository into a new folder and follow the README once.
5. After approval, publish:

```bash
git status
python -m pytest -q
git add README.md REPORT.md rag_app tests/test_v4.py evaluation/v4_checks.py evaluation/results/v4 reports/V4_FINAL_VERIFICATION.md reports/V4_PRESENTATION_GUIDE.md
git status --short            # check that .env, data/ and Tasks/ are not listed
git commit -m "V4 final release: traces, concept map explorer, personal data redaction"
git tag -a final -m "RAG project final release (V4)"
git push origin main
git push origin final
git ls-remote --tags origin   # v1, v2, v3 unchanged, final present
```

6. Send the e-mail to the professor with teammates in CC:
   repository https://github.com/Ferasmich/norag-rag — tag `final`: https://github.com/Ferasmich/norag-rag/tree/final

If anything changes after the tag is pushed, do not move the tag: ask the professor how to deliver a correction.
