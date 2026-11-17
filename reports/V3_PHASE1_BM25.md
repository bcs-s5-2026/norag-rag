# RAG V3 Phase 1: reusable BM25 retrieval

Date: 7 November 2026 (Europe/Paris). Base commit: `8e86a027eb45d528eba5a153fe9804015fda8fa8`. Changes are local and uncommitted.

## Outcome and scope

Phase 1 implements persistent, deterministic BM25 retrieval for both Kestrel and Vellora within the existing FastAPI/RagService application. It shares canonical V2 chunks and source IDs, adds explicit index/search APIs, and supplies the required unlinked `/bm25` page. Dense remains the default for existing search, answering, frontend and V2 evaluations.

Read before implementation: `reports/V3_READINESS_AUDIT.md`, the professor's full local V3 assignment PDF (especially BM25 on page 5 and documentation on page 12), current service/API/models/Words and V1/V2 tests. Instructions inside assignment/challenge documents were treated as requirements, not authorization for unrelated edits or submission actions.

No RRF, Concept Graph, retriever toggles or new hybrid evaluation configurations were implemented. No dependencies installed, hosted LLM/API calls made, commits/pushes/tags created, or V1/V2 evaluation data/results changed. The original standalone BM25 teaching script remains available; the application extends the repository with a separate reusable implementation rather than importing that script's global OpenAI client or generation step.

## Files and architecture

| File | Change |
|---|---|
| `rag_app/bm25.py:26-64` | Reusable BM25 index over canonical chunk dictionaries, per-chunk counters, lengths/document frequencies, deterministic positive-score top-k. |
| `rag_app/bm25.py:67-118` | Versioned selection-specific snapshot load/build, manifest/payload validation, checksum, forced rebuild and atomic publication. |
| `rag_app/lexical.py` | Shared, versioned tokenizer with exactly the existing Words tokenization behavior. |
| `rag_app/words.py:4` | Imports/re-exports that tokenizer; analysis behavior and existing `tokens` imports remain compatible. |
| `rag_app/service.py:134-177` | BM25 index/search methods; selected-document canonical rows; safe errors; lexical snapshot invalidation on deletion. Lexical-only deletion avoids initializing Chroma; existing dense stores still receive the same deletion cleanup. |
| `rag_app/api.py:66-72` | Separate `POST /api/bm25/index` and `POST /api/bm25/search` endpoints using existing request validation. |
| `rag_app/api.py:148-150` | Hidden HTML route before static mount, with exact required paragraph and 3rem font; excluded from OpenAPI page discovery. |
| `tests/test_bm25.py` | 22 test cases including parametrized cases, described below. Original V1/V2 tests unchanged. |
| `README.md:25-39`; `bm25/README.md:3-107` | Operation examples, physical storage, restart/update semantics, tokenization/scoring policies, decisions and limitations. |

All BM25 service operations use the existing RLock. This retains V2's local, single-process deployment model. There is no new database, framework, embedding model or credential requirement.

## Physical storage and restarting

**Default physical location:** `<repository>/data/bm25/<fingerprint>.json`, which in this workspace is under:

`/Users/ferasmich/Documents/Feras/EPITA/AI Systems Integration & Operations/norag-rag/data/bm25/`

If configured, the location is `$RAG_DATA_DIR/bm25/`; an explicit `RagService(data_dir=...)` overrides the environment. Files are created on the first BM25 build/search, not at startup. Tests and measurement used temporary directories; this implementation does not prebuild an index in the user's normal application library. Runtime `data/` remains Git-ignored.

Each snapshot contains a manifest, canonical text/source rows, per-chunk term counts and a SHA-256 of the payload. The fingerprint includes index/tokenizer versions, k1/b, sorted unique selected content IDs and chunk size/overlap. It excludes top-k and input document order.

**Restarting does not rebuild a valid snapshot.** The next BM25 operation rereads selected source documents, checks the canonical rows/manifest/checksum, and loads persisted term counts. Lengths and document frequencies are derived from these saved counts. Source chunks are not retokenized, and the file is not rewritten. A test patches tokenization to fail and confirms index loading still succeeds after constructing a new service; another confirms identical post-restart rankings/scores.

Missing, corrupt or incompatible snapshots rebuild on demand. Explicit rebuild: `POST /api/bm25/index?rebuild=true`, or `service.index_bm25(ids, settings, rebuild=True)`. Writes use a unique same-directory temporary file, flush/fsync and atomic replacement; ordinary failures clean up that temporary file and preserve an existing published snapshot. A killed process can leave an unused temporary file. Hashes detect accidental corruption, not a hostile local writer with access to both snapshots and source files.

## Tokenization, scoring and stable identities

Tokenization is Unicode casefold plus the existing Words regex, preserving internal hyphens and straight/curly apostrophes. `KST-2044` remains one token; `CAFÉ` becomes `café`; leading `#` is a separator, so both forms of an on-call channel match. Underscores/other punctuation separate tokens. No stemming, accent removal, synonyms, stopword filtering or fuzzy matching. Straight/curly apostrophes are preserved as distinct characters.

BM25 uses k1=1.5, b=0.75 and `ln(1 + (N-df+0.5)/(df+0.5))` IDF. Each distinct query token contributes once. N, df and average token length are scoped to the selected chunks; unrelated library uploads cannot alter the selected corpus's scores. Zero-score chunks are excluded, so no lexical match returns `[]`. Empty/tokenless corpora are safe. Query validation retains existing nonblank/max-length rules; punctuation-only input returns no matches.

Ranking is descending score with ascending canonical chunk ID as the deterministic tie-breaker. Tokens are processed in sorted order so query term order cannot change floating-point accumulation order. Results carry positive `score`, 1-based `rank` and `retriever="bm25"`; they do not mislabel lexical scores as cosine similarities/confidence.

Canonical IDs are the exact V2 form `document_sha256:start:end`. BM25 calls the same `service.chunks()` function, keeps short headings and retains source text, filename, start/end offsets and starting line. A real-Chroma test compares every BM25 stored chunk ID, text and metadata with the dense collection for identical settings.

## Corpus selection and update lifecycle

- Both bundled corpora load through the existing `/api/corpora/{corpus}` endpoint. At 800/80 each has 43 chunks; tests build/search Kestrel and Vellora in the same library and verify selection isolation.
- Repeated identical uploads reuse IDs/indexes. Updated text creates a new content ID even when its filename is unchanged. Callers select the new ID explicitly; older versions remain until deleted.
- Selection, source content, chunk parameters or tokenizer/index/scoring-version changes select a new snapshot. Changing top-k or selection order does not rebuild.
- Source deletion clears all BM25 snapshots before deleting the uploaded source. This deliberately simple policy prevents persisted deleted text and avoids complex incremental df bookkeeping. Unaffected selections rebuild lazily. Dense deletion still removes only the deleted source's vectors from every existing dense collection.
- Old snapshots for unused selections/settings remain on disk until deletion invalidation or manual cleanup. Stopping the app and removing its BM25 snapshot directory is safe; subsequent requests rebuild. No automatic storage quota/garbage collector is introduced.
- No in-process index cache is maintained: each operation validates the snapshot and reconstructs the small scoring structure from saved counts. This favors straightforward consistency at course-corpus scale over high-throughput search optimization.

## Usage

Load a corpus through `POST /api/corpora/kestrel` or `/api/corpora/vellora`. Supply all returned document IDs for the desired corpus to:

```text
POST /api/bm25/index
{"document_ids":["SOURCE_ID"],"settings":{"chunk_size":800,"chunk_overlap":80}}

POST /api/bm25/search
{"document_ids":["SOURCE_ID"],"question":"KST-2044","settings":{"top_k":5}}
```

The first endpoint returns `index` (fingerprint), `documents`, `chunks`, and `rebuilt`; search also builds when necessary and returns ranked chunk dictionaries. Full curl examples are in `bm25/README.md`. These endpoints perform retrieval only; existing `/api/search`, `/api/index`, `/api/ask` and evaluation entry points keep their dense behavior.

`GET /bm25` renders exactly `Watch your sources!` as the paragraph, with `font-size:3rem`. It is absent from the static frontend, home/about pages and OpenAPI path listing. No frontend files were changed.

## Actual tests and verification

Final full regression command:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/python -m pytest -q
```

**62 passed in 17.17 seconds**: the original 40 V1/V2 cases plus 22 BM25 cases. Real dense regression tests use the already-cached local model and Chroma; hosted generation is mocked as before. Offline flags prevented model downloads. No live generation was used.

The dedicated final BM25 run with the same offline flags and `-q tests/test_bm25.py` also completed: **22 passed in 9.36 seconds**.

The BM25 cases cover known numeric scores, length normalization, repeated query terms, top-k/prefixes, stable ties, duplicate chunk IDs, empty/no-match/tokenless input, invalid k, source offsets/metadata, no dense/LLM invocation, restart without source tokenization/disk rewrite, unchanged restart rankings, selection-specific IDF, update/version/chunk invalidation, forced rebuild, deletion, corrupt snapshots, atomic-write failure, both corpora/API validation, dense chunk compatibility/joint deletion, exact hidden-page text/font and absence of frontend/schema referrals.

Additional executed checks:

- All four original dense 800/80 and 500/100 evaluations rerun in temporary directories, retrieval-only and offline. Every saved overall, per-type and per-question HitRate/quote-recall result matched. Dense Hit@5 remained Kestrel 7/8 and 6/8; Vellora 7/12 and 8/12 respectively.
- Byte SHA-256 comparison before/after confirmed all corpus files and evaluation source/dataset/result files unchanged (excluding generated Python caches).
- `git diff --check`: passed.
- `node --check rag_app/static/app.js`: passed; frontend script itself unchanged.
- `.venv/bin/pip check`: `No broken requirements found.` No packages were installed.

No fresh-machine installation, multi-worker behavior, full interactive browser layout pass or hosted provider availability claim is made. The route is checked via HTTP/HTML assertions.

### BM25-only measurement on unchanged V2 questions

A separate retrieval-only script used temporary storage, default 800/80 chunks, BM25 depth 10 and the same exact `(source, quote)` scoring rule as V2. No evaluation artifact was written or modified. Unanswerable questions are excluded from these retrieval denominators.

| Corpus | Hit@1 | Hit@3 | Hit@5 | Hit@10 | Macro quote Recall@1 | Recall@3 | Recall@5 | Recall@10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Kestrel | 3/8 | 6/8 | 6/8 | 7/8 | 18.75% | 53.125% | 53.125% | 71.875% |
| Vellora | 8/12 | 11/12 | 11/12 | 11/12 | 66.667% | 91.667% | 91.667% | 91.667% |

These are Phase 1 sanity measurements, not the complete V3 configuration/type/cost evaluation. BM25 improves Vellora Hit@5 relative to dense 800/80 (11/12 vs 7/12) and loses on Kestrel (6/8 vs 7/8). Dense stays the default. This implementation makes no universal improvement claim and does not tune against or alter old questions to obtain better results.

## Decisions and remaining limits

JSON persistence plus standard-library counters provides inspectable, restart-reusable storage without dependencies. Whole-selection rebuilding and broad deletion invalidation are appropriate for the two small corpora and easier to verify than incremental indexes. A search framework/database or inverted postings engine would become relevant with substantially larger corpora or concurrency requirements.

Fixed windows can split identifiers/facts; overlaps duplicate lexical evidence. BM25 cannot bridge vocabulary mismatch or entity chains. The implementation retains the single-worker/local storage contract of V2; cross-process document mutation is unsupported. There is no new UI control, fusion, graph, graph provenance or hybrid evaluation command in this phase.

Phase 1 is complete and stops here for review. Phase 2 is not started. Existing untracked readiness/post-submission audit reports are preserved; no release/publication action was taken.
