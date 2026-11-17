# Evidence — EPITA RAG project (final release)

A local web application for asking questions about your own `.txt` and `.md` documents. Every answer comes with the passages it is based on and a **Details** button that shows what the application did, step by step.

Course: AI Systems Integration & Operations (BCS S5, EPITA, 2026). Versions: V1 naive RAG → V2 two corpora and evaluation → V3 hybrid search (dense + BM25 + concept graph) → **V4 final release** (traces, concept map explorer, personal data redaction). Decisions and measured results are in [REPORT.md](REPORT.md); the final check against the handout is in [reports/V4_FINAL_VERIFICATION.md](reports/V4_FINAL_VERIFICATION.md).

## Quick start

You need Python 3.12 and an internet connection for the installation (PyTorch is installed with `sentence-transformers`, so it takes a few minutes) and for the first run (it downloads the small `all-MiniLM-L6-v2` embedding model, once).

```bash
git clone https://github.com/Ferasmich/norag-rag.git
cd norag-rag
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env
```

Open `.env` and put your key in `LLM_API_KEY` (a free Google AI Studio key works: https://aistudio.google.com/app/api-keys). By default the app talks to Google Gemini. To use another OpenAI-compatible model, also set `LLM_URL` and `LLM_MODEL` (examples are in `.env.example`; a local server such as Ollama needs no key). The older `GOOGLE_API_KEY` / `GOOGLE_MODEL` names still work. Without a key you can still load documents, search, browse the concept map and run the retrieval evaluation; asking a question shows "Set LLM_API_KEY (or GOOGLE_API_KEY) in .env to generate answers."

**Intel Mac (x86_64):** recent PyTorch versions have no Intel Mac build. Use Python 3.12 and, after `pip install -r requirements-dev.txt`, pin `numpy<2`, `sentence-transformers<4`, `transformers<4.50` and `huggingface-hub<1.0` if the install or the first question fails with a torch/transformers import error.

```bash
python -m uvicorn rag_app.api:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000**, then:

1. Click **Load the Kestrel demo documents** (five sample company documents from the course). A sample question is filled in.
2. Click **Find an answer**. The first question takes a few seconds while the embedding model loads.
3. Read the answer, open a **supporting reference** to check the source text, then click **Details** to see each step: the three searches, the fusion, the redaction, the LLM call with its tokens and cost, and the citation check.
4. Open the **Concept map** tab, choose a concept and click its neighbours.

To use your own files: **Add a document** (UTF-8 `.txt` or `.md`, up to 5 MiB), keep it ticked, ask. Nothing else is required: documents are prepared automatically on the first question.

If something goes wrong, the message is shown in red above the answer area, with a **Details** button when a trace exists. Common cases: no API key (see above); "Graph chunk settings differ" or "supports only selected Kestrel source versions" means the *Concept graph* search method is ticked for documents or chunk sizes it was not built for — untick it in *Advanced search settings*. Stop the server with Ctrl+C. Use one server process only.

Run the tests (no API key needed, about 20 seconds): `python -m pytest -q` → 174 tests.

## What the final release (V4) adds

**A. Traces.** Every question, every indexing run and every concept lookup records one trace with one span per step (name, duration, what happened). Traces are JSON lines in `data/traces/traces.jsonl`, on your machine only, kept 30 days. They contain chunk ids, counts, timings, token counts and cost; never API keys, document text or answers. The question is stored after redaction. Open a trace with **Details** (on an answer, on an error, after **Prepare documents now**, on a concept) or from **Recent activity** at the bottom of the page. API: `GET /api/traces`, `GET /api/traces/{id}`.

**B. Concept map explorer.** The *Concept map* tab shows the V3 Kestrel concept graph: 42 concepts and 39 links. Choose a concept to see its neighbours, the relation on each link, any condition, and the exact sentence and chunk each link was extracted from. **Ask a question about this concept** prepares a question in the *Ask* tab. It reads the saved graph and makes no LLM call. API: `GET /api/concepts`, `GET /api/concepts/{id}`.

**C. Personal data redaction.** E-mail addresses and phone numbers in the question and in the retrieved passages are replaced by placeholders such as `[EMAIL_1]` before anything is sent to Gemini and before the trace is written. The real values are put back in the answer on your machine. Names are not detected. Details and limits: REPORT.md, section "V4".

**Clean-up.** One-click demo corpus, search settings folded under *Advanced search settings* (the defaults work), plain-language step names, a clear message when a question fails.

Check scripts and results: `python -m evaluation.v4_checks offline --output <new file>` (no LLM call) and `python -m evaluation.v4_checks live --approve-external --output <new file>` (8 Gemini calls, about $0.015). Saved runs: [evaluation/results/v4/](evaluation/results/v4/README.md).

## Where things are

| Path | Content |
|---|---|
| `rag_app/service.py` | the pipeline: upload, chunk, index, retrieve, fuse, generate, validate |
| `rag_app/tracing.py`, `redaction.py`, `concept_map.py` | the three V4 modules |
| `rag_app/bm25.py`, `fusion.py`, `graph_*.py` | V3 retrievers |
| `rag_app/static/` | the web page (plain HTML, CSS, JavaScript; no build step) |
| `evaluation/` | question sets, evaluation scripts and saved results for V1–V4 |
| `concepts/kestrel_graph_v2/` | the saved concept graph used by the app |
| `data/` | created at run time, git-ignored: uploaded documents, indexes, traces |
| `tests/` | automated tests |

Optional settings in `.env`: `LLM_URL`, `LLM_API_KEY`, `LLM_MODEL` (default Gemini `gemini-3.5-flash-lite`), `RAG_DATA_DIR` (default `./data`), `RAG_GRAPH_AUTO_MAX_CHUNKS` (default 60). `requirements-lock.txt` lists the exact versions tested on macOS with Python 3.12.

## Concept graph of your own documents

When you upload a `.txt` or `.md` file, the app builds its concept graph right away (one model call per 800-character passage, up to 60 passages; bigger files get a **Build graph** button instead). The model picks a short type for each concept (person, project, material…) and a short name for each link. A concept or link is kept only if its quote is copied exactly from the passage, otherwise it is dropped. Emails and phone numbers are replaced by placeholders before a passage is sent. The graph is saved in `data/doc_graphs/` and can be:

- explored in **Concept map** (choose the document in "Map of"), every link showing the sentence it came from;
- used as a retriever: tick **Concept graph** next to Meaning and/or Exact words. Several documents can be selected; a concept with the same name in two of them becomes one node, so a path can cross documents;
- left out safely: if no graph could be built, ticking it together with another retriever simply shows "graph unavailable" and the answer comes from the others. The graph must use the same chunk settings it was built with.

The Kestrel demo keeps its frozen, validated graph, and it can be mixed with uploaded files: each graph is used for its own files, and files that have no graph are listed as "not covered" in the graph trace instead of switching the retriever off. A broken Kestrel snapshot is still an error. A file that is really Rich Text saved as `.txt` is refused with advice (save as plain text).

---

# Earlier versions (V1–V3)

The sections below document the previous releases. They are kept because the evaluation commands and results are still valid. Button names in the page changed in V4 ("Build selected index" is now **Prepare documents now**, under *Settings*).

## Architecture (V1)

FastAPI serves both the API and the static page. Pydantic validates requests and the JSON generated by the LLM. Local `all-MiniLM-L6-v2` embeddings feed a persistent Chroma cosine index. Gemini generates answers through its OpenAI-compatible endpoint.

Indexing: UTF-8 source → overlapping character windows → local embeddings → Chroma.
Answering: selected documents + question → retrieval → Gemini → schema and citation validation → answer and source passages.

The original `ask_rag_google.py` and `ask_norag_google.py` course demos remain available and use their own `chroma_db/` store.

## Course demos and new challenges

The professor’s upstream updates are included alongside the V2 web application:

- `ask_norag_google.py`: full-context NoRAG demo, now using `gemini-2.5-flash-lite`.
- `ask_rag_google.py`: dense RAG demo using `docs/CrimeAndPunishment.txt` and five retrieved chunks.
- [BM25 guide](bm25/README.md): lexical retrieval demo and challenges. Run `python bm25/ask_bm25_rag_google.py` from the repository root.
- [Two-hop concept graph challenge](concepts/concept_graph_challenge_part1.md): the new retrieval exercise.

These standalone course demos are separate from the V2 web application and its measured evaluation results.

## V3 Phase 1: reusable BM25 retrieval

The application now offers local lexical retrieval through `RagService.index_bm25()`
and `retrieve_bm25()`, and `POST /api/bm25/index` / `POST /api/bm25/search`.
Both use existing document IDs and chunk settings. Load either course corpus through
`POST /api/corpora/kestrel` or `POST /api/corpora/vellora`, then pass its returned IDs.
Legacy dense search and V2 evaluation commands retain their existing behavior.
The opt-in Phase 2 API and CLI below add retriever selection and fusion.

BM25 snapshots physically live in `data/bm25/<fingerprint>.json` by default,
or `$RAG_DATA_DIR/bm25/` when configured. Restarting loads saved token counts;
it does **not** retokenize/rebuild a valid index. Missing, corrupt or incompatible
snapshots rebuild on demand. `POST /api/bm25/index?rebuild=true` forces a rebuild.
See [BM25 storage, tokenization and API documentation](bm25/README.md#application-bm25-v3-phase-1)
and [Phase 1 implementation report](reports/V3_PHASE1_BM25.md).

## V3 Phase 2: dense + BM25 RRF

`RagService.retrieve_configured(question, document_ids, settings, retrieval)` and
`POST /api/retrieve` provide dense-only, BM25-only, or dense+BM25 retrieval.
The legacy `/api/search`, `/api/ask` requests without retrieval configuration, and `evaluation.v2` retain dense behavior. The frontend now provides dense/BM25/graph controls; `/api/ask` accepts optional retrieval configuration and `/api/evaluations/v3` runs retrieval-only evaluation. No hosted generation occurs in the V3 evaluator.

```bash
# Standard V3 retrieval evaluation; choose a new output name for each run.
python -m evaluation.v3 --corpus kestrel --retrievers dense bm25 \
  --candidate-depth 20 --rrf-k 60 --top-k 5 \
  --output evaluation/results/v3/kestrel-dense-bm25.json
python -m evaluation.v3 --corpus vellora --retrievers bm25 \
  --output evaluation/results/v3/vellora-bm25.json
python -m evaluation.v3 --corpus kestrel --retrievers dense \
  --output evaluation/results/v3/kestrel-dense.json
```

Plain RRF sums `1/(rrf_k + rank)` with 1-based ranks, one contribution per chunk
per retriever and canonical chunk-ID deduplication. Ties sort by chunk ID.
Each result contains `origins` (retriever ranks/raw scores), `fused_rank` and
`rrf_score`. The default rank constant is 60, independent of final `--top-k`.
`--candidate-depth` is the maximum per-retriever list length before fusion;
it must be at least final top-k. Evaluation additionally requires depth >=10,
scores prefixes 1/3/5/10 and saves `selected` as the final top-k prefix.
Rankings for metrics and selection come from one retrieval snapshot per question.

API request example (replace IDs with existing uploaded source IDs):

```json
{
  "document_ids": ["SOURCE_ID"],
  "question": "What does KST-2044 mean?",
  "settings": {"chunk_size": 800, "chunk_overlap": 80, "top_k": 5},
  "retrieval": {"retrievers": ["dense", "bm25"], "candidate_depth": 20, "rrf_k": 60}
}
```

The response contains `results` plus configuration and per-retriever status/counts.
Missing/corrupt BM25 snapshots rebuild using Phase 1's policy and report
`index_rebuilt: true`. An empty list is reported as `empty`; failure of an enabled
retriever aborts the request/run rather than switching to another configuration.
The new dense path queries all selected chunks before resolving score ties and
truncating candidates; this ensures deterministic cutoff membership at the current
small corpus scale. The original dense path is unchanged.

See [Phase 2 implementation report](reports/V3_PHASE2_RRF.md) for tests, reproduced
V2 baselines, measured CLI results and limitations. Existing output files are refused;
new evaluations never overwrite frozen V1/V2 artifacts.

## V3: switching retrievers, building the graph, running the evaluation

Final V3 results, defaults and analysis: [REPORT.md](REPORT.md), section "V3 final".

### Switch retrievers on and off

- **UI:** in the retrieval panel, tick any of *Dense*, *BM25*, *Graph*. Results are fused with RRF over the ticked retrievers. Each citation shows which retriever(s) found it and at which rank; with *Graph* on, the answer panel shows the entities found in the question, the edges followed (with conditions) and the source chunks. Loading a corpus selects the measured default: Kestrel → dense + BM25 + graph, Vellora → BM25.
- **API:** `POST /api/ask` with `"retrieval": {"retrievers": ["dense", "bm25", "graph"], "candidate_depth": 20, "rrf_k": 60}`.
- **CLI:** `python -m evaluation.v3 --retrievers dense bm25 graph …` (any subset). The graph is Kestrel-only.

### Build the Kestrel Concept Graph (recipe v2)

Needs `GOOGLE_API_KEY` in `.env`. Sends the 43 Kestrel chunks to Gemini once; results are cached, so a resume or rebuild only calls the API for missing chunks.

```bash
# 1. Plan only: chunk count, estimated tokens and cost; no API call.
python -m rag_app.graph plan  --recipe v2 --model gemini-3.6-flash --max-output-tokens 8192 --max-calls 90
# 2. Build (explicit approval flag; paced for rate limits; resumable).
python -m rag_app.graph build --recipe v2 --model gemini-3.6-flash --max-output-tokens 8192 \
  --max-calls 90 --max-attempts 3 --approve-external --pace 8 --backoff 30
# 3. Export the portable, committed bundle used by the app.
python -m rag_app.graph export --recipe v2 --model gemini-3.6-flash --max-output-tokens 8192 \
  --max-calls 90 --max-attempts 3 --out concepts/kestrel_graph_v2
# Inspect offline
python -m rag_app.graph inspect --graph-path concepts/kestrel_graph_v2/graph.json
```

`scripts/v3_graph_v2.sh` runs plan → build (with automatic resume) → export → 10-triple review sample → all evaluations → tests. The app loads `concepts/kestrel_graph_v2/graph.json` (override with `RAG_GRAPH_PATH`); it never builds a graph at start-up. The first, partial v1 graph stays in `concepts/kestrel_graph/` for comparison.

Manual extraction-quality review: `python -m rag_app.graph_review prepare --output evaluation/graph_review/<name>-ungraded.json` creates a random sample and a blank `-GRADES.csv`; after it is filled in, `python -m rag_app.graph_review collect --output …-ungraded.json` records the grades verbatim. The completed current V3 review is [kestrel-v2-10-triples.json](evaluation/graph_review/kestrel-v2-10-triples.json): Feras M, 10 correct / 0 wrong / 0 unsupported, sampled from 39 relations. Its original ungraded JSON, full-chunk Markdown and filled CSV are preserved beside it. The older `kestrel-10-triples*` review belongs to the superseded first graph.

### Run the evaluation

Retrieval only (no LLM calls): HitRate@k and Recall@k for k = 1, 3, 5, 10, overall and per question type, plus latency.

```bash
# Use a fresh directory. Each invocation refuses an existing result filename.
OUT=$(mktemp -d "${TMPDIR:-/tmp}/rag-v3-eval.XXXXXX")
python -m evaluation.v3 --corpus kestrel --question-set v3 --retrievers dense               --output "$OUT/kestrel-dense.json"
python -m evaluation.v3 --corpus kestrel --question-set v3 --retrievers dense bm25          --output "$OUT/kestrel-dense-bm25.json"
python -m evaluation.v3 --corpus kestrel --question-set v3 --retrievers dense bm25 graph \
  --graph-path concepts/kestrel_graph_v2/graph.json --output "$OUT/kestrel-dense-bm25-graph.json"
python -m evaluation.v3 --corpus vellora --question-set v2 --retrievers dense               --output "$OUT/vellora-dense.json"
python -m evaluation.v3 --corpus vellora --question-set v2 --retrievers dense bm25          --output "$OUT/vellora-dense-bm25.json"
python evaluation/results/v3/graph_v2_final_2026-11-08/analyze.py "$OUT"
```

Options: `--candidate-depth` (per retriever, default 20), `--rrf-k` (default 60), `--top-k` (default 5). Existing output files are never overwritten. `scripts/v3_seedfix_eval.sh` reproduces the final Kestrel runs.

## V1 walkthrough

From the repository root:

```bash
source .venv/bin/activate
python -m uvicorn rag_app.api:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000**. The same process serves the frontend. API documentation is at `/docs`. Use one worker: document/index operations are protected by a process-local lock. This is a local single-user homework application.

1. Upload `docs/vellora-duo-espresso-machine.txt` with **Upload source**. Uploaded sources persist across restarts. Each file is limited to 5 MiB and must contain nonempty UTF-8 text.
2. Check one or more documents. New uploads are selected automatically. Identical content is deduplicated even with a different filename; the first filename is kept.
3. Set chunk size (100–1,000 characters), overlap (0 to size minus one), and top-k (1–20).
4. Click **Prepare documents now** (called "Build selected index" before V4), or ask a question to build missing indexes automatically. New size/overlap settings use a new index. Top-k reuses existing embeddings.
5. Try **How long is the Vellora Duo warranty?** The measured live answer was two years from purchase.
6. Open a supporting reference to see its exact retrieved text, filename, start line and character offsets. Offsets are zero-based, end exclusive, in decoded source characters. The UI also exposes every retrieved passage, including on abstentions.
7. Delete removes the uploaded source and its chunks from every web-app index. It does not delete the original repository file in `docs/`.

## Corpus and evaluation

The baseline uses the unchanged 31,036-character Vellora Duo manual supplied in the professor's repository. Its header identifies it as a fictional course document: the application did not invent it. It spans 11 sections and many similar error codes, making both answers and retrieval failures verifiable. The two existing Crime and Punishment files remain available for uploads, but the shortened/full copies are excluded from the baseline to avoid duplicate evidence. Corpus origin: `https://github.com/bcs-s5-2026/norag-rag`, `docs/vellora-duo-espresso-machine.txt`.

```bash
python -m evaluation.run
# For comparisons, preserve baseline.json and write another file:
python -m evaluation.run --top-k 3 --output evaluation/comparison.json
```

The evaluator creates an isolated temporary corpus/index and uses real embeddings and Chroma, never an LLM. `evaluation/questions.json` freezes 15 questions: 12 answerable (4 easy, 4 precise, 4 hard), 3 unanswerable. Each answerable question has an expected answer, source, section and verbatim evidence span. **Hit@k** is the fraction of answerable questions where a retrieved chunk from the expected document contains the full expected span. Matching spans rather than chunk IDs allows different chunk sizes to be compared, though split spans can still count as misses. V2 retains this dataset/corpus and records settings and hashes.

Measured V1: **Hit@5 = 7/12 = 58.3%** at size 800, overlap 80. `evaluation/baseline.json` contains settings, hashes and individual results. Three unanswerable queries are retrieved and recorded but excluded from Hit@k: nearest-neighbor search always returns candidates, so that metric cannot establish abstention accuracy. The frontend displays the saved baseline, independently of current library selection/settings.

## Tests

```bash
python -m pytest -q
node --check rag_app/static/app.js  # optional JavaScript syntax check
```

The original 30 V1 tests use real MiniLM/Chroma; hosted generation is stubbed to test valid and invalid structured output predictably. Tests cover upload, deduplication, deletion across configurations, selection, offsets, 384-dimensional embeddings, retrieval, settings, schema/citation integrity, abstention normalization, missing credentials and simulated embedding/database/API failures. A separate actual Gemini HTTP smoke test is recorded in `reports/live_smoke.json`; it includes a supported answer and two abstentions. Automated tests do not call the paid API.

## V2: two corpora, evaluation and Words

C7’s V2 specification requires measurement and word exploration, without prescribing hybrid retrieval or a new embedding model. The original service, embedding model, upload/delete/selection, settings and citation validation are retained. No new dependencies.

The five unchanged course Kestrel documents are distributed under `docs/kestrel/`; the unchanged 10 starter questions are in `evaluation/kestrel.jsonl`. Vellora remains the own corpus: `evaluation/vellora.jsonl` converts the 15 frozen V1 questions to Kestrel JSONL format without changing their questions, expected answers or passages. Both corpora are fictional course material. `/Tasks/` contains local source material and is ignored, including its PDFs; the runtime needs none of it.

From **Evaluation**, choose a corpus and click **Load corpus into library** to upload and select just that corpus. Choose chunk settings, then **Run evaluation**. Evaluation uses an isolated temporary index, independently of the current library selection, so extra uploads cannot contaminate the benchmark. Metrics always use k=1/3/5/10. Top-k controls evidence for optional answer generation. The default run retrieves only; the answer checkbox generates validated answers, and the no-context checkbox asks the exact questions with no documents, expected answers or evidence supplied to Gemini. Hosted calls are spaced six seconds apart; a run may take several minutes. API failures are saved per question rather than scored as wrong answers.

Terminal equivalents (use fresh output filenames; existing files are refused):

```bash
python -m evaluation.v2 --corpus kestrel --output evaluation/results/kestrel-new-800-80.json
python -m evaluation.v2 --corpus vellora --chunk-size 500 --chunk-overlap 100 --output evaluation/results/vellora-new-500-100.json
python -m evaluation.v2 --corpus kestrel --top-k 10 --answers --no-context --output evaluation/results/kestrel-new-answers.json
python -m evaluation.v2 --corpus vellora --no-context --output evaluation/results/vellora-new-no-context.json
```

Measured 800/80 → 500/100 Hit@5: **Vellora 7/12 (58.3%) → 8/12 (66.7%)**; **Kestrel 7/8 (87.5%) → 6/8 (75.0%)**. Smaller chunks help some facts and hurt others; the app defaults remain 800/80. Kestrel’s best measured depth is k=10 with 800/80, used for the answer-review run. See REPORT for all depths, types and question differences. A hit means at least one expected literal quote occurs in a retrieved chunk from the expected source. Quote recall also measures the fraction of all expected quotes found; this exposes partial evidence in split/two-hop questions. Unanswerable questions are excluded from both retrieval metrics. A hit does not prove the generated answer is correct.

Use **Open measured run for review** to open a saved CLI/project result in a local grading copy. Expand questions, read expected answers, generated answers and references, then enter your reviewer name, grade, notes and no-context correctness flag. Grading rules are saved before grading and shown in the page. **Save human grade** writes to the same local results JSON. **Download saved results** exports that reviewed file for the project; copy it to `evaluation/results/` with a new filename. A no-context flag is true only when the answer supplies the expected facts; an abstention is not prior knowledge. Preserve questions even if flagged and discuss them in the report. No manual grades are fabricated by the implementation agent.

Browser runs are saved under ignored `data/evaluations/`. Copy the displayed run ID to reopen after a restart, or use the measured-run selector for committed evidence. Local evaluations are single-user synchronous requests; keep the tab open until completion. The saved V1 baseline panel remains available.

The **Words** tab operates on checked library documents and current chunk size/overlap, without an LLM or embeddings. Corpus mode lists words, their occurrence counts and number of containing chunks; enter or click a word to inspect exact matching passages/counts. Question mode accepts typed text or a question-set selection and shows present and absent words and matching chunks. Tokenization case-folds Unicode words, keeps hyphenated identifiers and internal apostrophes together, and uses no stemming or stopword removal. Counts refer to chunk windows, so overlap duplicates count again. Question words are shown once each. Exact source offsets are preserved. Large uploaded corpora can produce large tables; intended for the course-sized corpora.

V2 API additions: `POST /api/search`, `/api/words`, `/api/corpora/{corpus}`, `/api/evaluations`; `GET /api/question-sets`, `/api/measured-runs`, `/api/evaluations/{run_id}`; and result-review routes documented in `/docs`. The CLI and API call the same application retrieval service and evaluation function. The C7-required standalone `/about` page is deliberately unlinked from the frontend.

## Controlled failures and limitations

Bad uploads/settings/questions produce 400/413/422 errors; missing documents produce 404; embedding/storage/API failures produce a safe 503; invalid generated JSON or citations produce 502. The UI displays the message and restores controls. Invalid model output is rejected rather than repaired or shown. Failed indexes have no completion marker and are cleared/rebuilt on retry.

V1 dense retrieval misses some exact codes and boundary-spanning facts. There is no calibrated relevance threshold; evidence sufficiency is decided by the prompted LLM. Schema validation checks structure and citation membership, not whether every factual statement follows from a cited passage. Prompt instructions reduce but cannot eliminate hallucination or document prompt injection. Long/token-dense chunks may be truncated by MiniLM's 256-wordpiece limit even within the character cap. Similarities are not probabilities.

This application has no authentication, multi-user isolation, background indexing, reranking or cost dashboard (since V4 each trace shows the tokens and cost of its own request). Source passages and the question are sent to Google for generation; since V4, e-mail addresses and phone numbers are replaced first. It is intended for loopback use with non-sensitive course material. Single-process indexing serializes retrieval; first indexing can take time. Old parameter-specific indexes remain until their documents are deleted. Browser smoke testing reached the V2 tabs and corpus loading; full result rendering, Words interaction and responsive layout remain unverified after browser access timed out. API workflows and JS syntax were verified.

See `REPORT.md` for decisions and observed failures, `reports/RAG_V2_IMPLEMENTATION_REPORT.md` for current delivery evidence and Git status, and the preserved V1 report for historical evidence.


Kestrel's completed owner review is saved in `evaluation/results/kestrel-reviewed.json`: 6 correct, 3 partial, 1 wrong; all 10 no-context flags false. All 15 Vellora no-context judgments were initially AI-assisted, then personally verified and confirmed by **Feras M**. Human verification is complete and recorded in `evaluation/results/vellora-reviewed.json` and `evaluation/results/vellora-no-context.jsonl`: q09 and q10 are true; the other 13 are false. Original AI assessment provenance and the subsequent human-confirmation history are preserved. See the latest review-status section in REPORT for release readiness.


## Post-release Vellora human confirmation

Feras M completed human verification and explicitly confirmed all 15 proposed no-context judgments in chat after reviewing the question/expected-answer/response summary table: **Yes for q09 and q10, No for the other 13**. The confirmation concerns the no-context flags, not a new Vellora RAG-answer grading experiment. `evaluation/results/vellora-reviewed.json` and `vellora-no-context.jsonl` now record the verifier, confirmation timestamp, rationale and review history. Original AI assessor metadata remains unchanged, including its historical `human_reviewed: false` value at the time of the AI-only assessment; the subsequent `human_verification` event records the later confirmation. `vellora-ai-assessed.json` remains byte-for-byte intact. All 10 Kestrel human reviews are unchanged. The original v2 release snapshot contains the initial AI-only assessments; the subsequent human confirmation is recorded in the follow-up artifacts. Final V2 documentation reflects completed human verification by Feras M.

This is a follow-up on main, not a new release. The existing annotated v2 tag remains object `07ff1e7d3262b4fbbb589eb97921cfa1803d1d20`, pointing to release commit `2a223476c8df74ae6e0464fada5c277f39aaa984`. Main is expected to advance beyond that tag. No evaluation questions, model responses, retrieval metrics or application code changed.
