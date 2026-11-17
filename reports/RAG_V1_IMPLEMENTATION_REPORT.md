# RAG V1 implementation report

## Summary

Implemented Evidence, a functional local RAG web application using the existing course stack: Python, all-MiniLM-L6-v2, persistent ChromaDB, Gemini via the OpenAI SDK, and a FastAPI-served HTML/CSS/JavaScript interface. The existing command-line demos and original corpus files were preserved. Only V1 behavior is implemented.

## Repository audit and preservation

Workspace: `/Users/ferasmich/Documents/Feras/EPITA/AI Systems Integration & Operations/norag-rag`.

Initial branch: `main` at `36f24eb`, clean working tree, two local history commits (`93f3f90`, `36f24eb`). Original `origin` was `https://github.com/bcs-s5-2026/norag-rag`, with tracked remote main one commit ahead at `305ae5f` (commenting out a demo question). The user's fork had that same descendant. Renamed the original remote to `upstream`, added the fork as `origin`, fetched the fork and fast-forwarded safely to `305ae5f`. No prior working-tree modifications were found, no reset/reclone/force push was used, and original tracked source changes were retained.

Final remotes:

- origin: `https://github.com/Ferasmich/norag-rag.git`
- upstream: `https://github.com/bcs-s5-2026/norag-rag` (actual original URL, preserved)

No upstream push was performed. Branch tracking is `main` → `origin/main`.

## Features and files

- `rag_app/models.py`: validated retrieval settings, selected document/question inputs and strict generated answer schema.
- `rag_app/service.py`: UTF-8 upload, SHA-256 deduplication, document persistence, exact-offset chunking, local embeddings, cosine vector storage/search, selected-source filtering, deletion across every web index, incomplete-build recovery, Gemini integration and citation validation.
- `rag_app/api.py`: HTTP document/index/ask/baseline routes and controlled error responses.
- `rag_app/static/`: responsive source/settings/question workspace, loading and error states, plain-text answer rendering, clickable supporting references, all retrieved evidence and saved evaluation display.
- `evaluation/questions.json`: fixed 15-question corpus-specific dataset.
- `evaluation/run.py`, `evaluation/baseline.json`: repeatable real retrieval evaluation and measured results.
- `tests/test_rag.py`: integration and failure-handling tests.
- `README.md`, `REPORT.md`: installation, usage, decisions, observed failures, corpus origin and limitations.
- `.env.example`, `.gitignore`, `requirements.txt`, `requirements-dev.txt`, `requirements-lock.txt`: safe configuration and dependencies.
- `reports/live_smoke.json`: actual live model responses and evidence from three questions.
- `reports/RAG_V1_IMPLEMENTATION_REPORT.md`: this report.

## Architecture and pipeline explanation

The browser sends a question, selected document IDs and numeric settings to FastAPI. Uploaded text is persisted under a content-derived ID; filenames cannot escape the storage directory. Each chunk is an exact source substring with document ID, filename, character offsets and start line. MiniLM creates 384-dimensional embeddings locally. Chroma stores those vectors with their text and metadata in a collection tied to embedding model and chunk settings.

On a question, incomplete/missing selected-document indexes are built first. The same MiniLM model embeds the question. Chroma filters to selected document IDs and returns top-k cosine neighbors. The application sends this small evidence set and question to Gemini with grounding/abstention instructions. Pydantic validates generated JSON and requires a nonblank answer, boolean answerability and citation IDs; every cited ID must belong to the actual retrieved set. Supporting reference text comes from that set, not from the model. The UI renders answer and evidence separately and lets the user inspect exact passages.

Changing chunk size or overlap creates/reuses a distinct index; changing top-k does not recompute embeddings. Identical uploaded text is not indexed twice. Failed builds have no completion marker and are cleared/rebuilt on retry. Deletion removes all indexed configurations for the document before deleting its stored source. The original `docs/` corpus remains untouched.

## Actual verification

1. `.venv/bin/python -m pytest -q`: **30 passed in 6.42 seconds**; after frontend formatting, **30 passed in 7.19 seconds**. Tests use real MiniLM embeddings and real persistent Chroma. Generation is stubbed for deterministic validation tests. Covered uploads (.txt/.md), unsupported/empty/invalid UTF-8/path/oversize uploads, duplicates, listing, deletion across settings, selection, chunk offsets, 384-dimensional embeddings, vector storage/query, invalid parameters/questions/selections, malformed JSON/missing fields/fabricated references, abstention, missing credentials, simulated database/embedding failures and simulated LLM API failure.
2. `.venv/bin/python -m evaluation.run`: actual MiniLM/Chroma evaluation completed successfully, **Hit@5 7/12 = 0.5833333333**; three unanswerable questions excluded from the denominator.
3. Started the documented server command (`python -m uvicorn rag_app.api:app --host 127.0.0.1 --port 8000`). Actual HTTP responses for `/`, `/app.js`, `/style.css` succeeded. Multipart upload and `/api/ask` completed a real end-to-end request with Gemini.
4. Real Gemini: “How long is the Vellora Duo warranty?” → “The Vellora Duo is covered by a two-year warranty from the date of purchase.” One actual retrieved citation passed validation. Evidence snapshots are in `live_smoke.json`.
5. Real Gemini: tank-capacity question abstained because retrieval missed the source fact. Wi-Fi-password question abstained correctly because no password exists in the corpus. These do not establish a population answer-accuracy rate.
6. `node --check rag_app/static/app.js`: passed JavaScript syntax validation.
7. `.venv/bin/pip check`: no broken requirements.
8. `git diff --check`: passed at release preparation.
9. Browser inventory returned no available browser. Safari computer-use inspection timed out. No visual, mobile-layout or interactive browser click-through pass is claimed.

## Retrieval baseline and known failures

Corpus: unchanged `docs/vellora-duo-espresso-machine.txt`, 31,036 characters; fictional course manual from the original professor repository. Full and shorter novel copies are preserved but excluded from baseline duplication. The fixed dataset has four easy, four precise, four hard and three unanswerable questions. Each answerable entry includes expected answer, expected document, section and verbatim source span. Corpus/dataset hashes, settings and per-question retrieved IDs/scores are saved in `evaluation/baseline.json`.

Metric: Hit@k counts an answerable question as a hit when an actual retrieved chunk from the expected source contains its full expected span. **7 hits / 12 answerable questions = 58.3% at k=5, size=800, overlap=80.** This is retrieval performance, not LLM accuracy. Three unanswerable questions have no expected passage and are recorded separately; ordinary nearest-neighbor retrieval still returns candidates for them.

Observed misses: q01 (tank capacity), q05 (E47 procedure), q07 (E86 unlock), q09 (grounds-counter reset), q11 (unused-machine circuit fill). `REPORT.md` contains the exact test question, expected/observed behavior, plausible causes and possible V2 experiments for each. No baseline tuning was performed to hide these misses. Preserve dataset/corpus for V2 and write comparison outputs separately.

## Security checks and limits

Compared all proposed application/test/evaluation/report/configuration files against the actual local environment secret values without displaying those values: no matches. `.env`, local databases, uploads, virtual environments and Python caches are ignored. `git ls-files .env data chroma_db` was empty. `.env.example` contains placeholders only. Frontend output uses textContent, so filenames, chunks and generated text cannot become injected HTML. Keys stay server-side; only selected retrieved evidence and questions are sent to Google.

This is a loopback single-user application, not a public production deployment. Locks are process-local: run one worker. No semantic verifier proves that a valid citation supports every claim; model abstention is not calibrated. MiniLM may truncate token-dense chunks. Exact-code retrieval and boundary-spanning facts fail in the observed baseline. Old parameter-specific indexes consume disk until document deletion. First-use downloads/storage/API failures remain environmental dependencies. The frontend's visual appearance and actual browser interactions remain unverified.

Feras (GitHub: Ferasmich) is the sole project developer. The professor specifies teams of 2–3; individual participation requires confirmation. The student should review and personalize the decision log and be prepared to explain/change the code.

## Git release

Implementation commit: `27bd1da5a4ae0059358a6e7fa9ae9cbdc43b79f5`. A subsequent release-documentation/formatting commit contains this finalized report and is the commit referenced by `v1`. To obtain the exact release hash, run `git rev-parse 'v1^{commit}'`; a tracked report cannot contain its own commit hash.

Release status: **PASS** — `main` and annotated tag `v1` published together to the fork using `git push --atomic origin main refs/tags/v1`, without force. Remote branch and dereferenced tag hashes verified against the local release commit; working tree clean. No pre-existing local or remote `v1` tag was found before creation. No professor/upstream writes were made.

## Run and reproduce

```bash
cd "/Users/ferasmich/Documents/Feras/EPITA/AI Systems Integration & Operations/norag-rag"
source .venv/bin/activate
pip install -r requirements-dev.txt
# If starting fresh, copy .env.example to .env and set GOOGLE_API_KEY.
python -m uvicorn rag_app.api:app --host 127.0.0.1 --port 8000
# Open http://127.0.0.1:8000; frontend is served by this same command.
```

Upload the Vellora manual, leave it checked, use default settings, optionally build the index, then ask the warranty question. Open the reference and inspect its text. To reproduce evaluation/tests in another terminal:

```bash
source .venv/bin/activate
python -m evaluation.run --output evaluation/reproduced.json
python -m pytest -q
```

## Final requirements checklist

| Status | Requirement and evidence |
|---|---|
| PASS | Preserve existing work and safely configure origin/upstream; clean initial tree and fast-forward only |
| PASS | Two-phase RAG, same embedding model, real vectors, text and source metadata; tests and live request |
| PASS | Add/list/delete .txt/.md; selection and deletion invalidation verified by API integration tests |
| PASS | Validated chunk size/overlap/top-k; distinct chunk indexes, reused top-k index tested |
| PASS | Backend structured output, missing credentials, API/embedding/database errors, invalid questions and citation IDs handled |
| PASS | Real supported Gemini answer with citation and real abstention samples |
| PASS | Stable question set, expected sources/passages, difficult/unanswerable questions and measured Hit@5 |
| PASS | README, decision log, team note, actual known failures, corpus origin and this report |
| PASS | Environment placeholders, ignored secrets/databases, secret-value scan and dependency check |
| PARTIAL | Frontend document/question/settings/reference/evaluation features implemented; HTTP routes and JS syntax verified; browser runtime interaction unavailable |
| NOT TESTED | Visual/responsive browser appearance and reference click-through in an actual browser |
| PARTIAL | Individual participation requires professor confirmation; no teammates fabricated |
| PASS | Fork main and annotated v1 tag published atomically and verified; no force or upstream push |

No mandatory V1 application capability is knowingly missing. Browser verification and individual-team approval remain outstanding. Retrieval misses are measured baseline limitations, not hidden passes.
