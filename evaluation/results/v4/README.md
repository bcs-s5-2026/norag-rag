# V4 evaluation artifacts (12 November 2026)

| File | What it is | LLM calls |
|---|---|---|
| `offline_2026-11-12.json` | Concept map check on all 42 concepts and redaction detection cases | 0 |
| `retrieval_regression_2026-11-12/` | V3 retrieval evaluation re-run on the V4 code; `compare.py` checks it against the committed V3 runs | 0 |
| `live_final_2026-11-12.json` | The 8 fixed live questions on the final code. This is the run reported in REPORT.md | 8 |
| `live_final_2026-11-12-REVIEW.md` / `.csv` | Blank human review sheet for those 8 answers | – |
| `redaction_two_placeholders_2026-11-12.json` | Hard case: personal data in the question and a hidden address needed in the answer, 3 runs, final code | 3 |
| `live_2026-11-12.json` | First live run, before the redaction fixes (kept as evidence of the problem) | 8 |
| `redaction_ab_2026-11-12.json` | Same question with redaction on and off, before the fix | 4 |
| `redaction_after_fix_2026-11-12.json` | Same question after the prompt instruction was added | 4 |
| `live_after_fix_2026-11-12.json` | Intermediate run with the first version of the guard (reject), later replaced | 8 |

Reproduce: `python -m evaluation.v4_checks offline --output <new file>` and
`python -m evaluation.v4_checks live --approve-external --output <new file>` (needs `GOOGLE_API_KEY`).
Existing files are never overwritten. Live answers vary slightly between runs.
