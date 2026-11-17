# BM25 retrieval

## Application BM25 (V3 Phase 1)

The reusable application implementation is `rag_app/bm25.py`, integrated through
`RagService.index_bm25(ids, settings, rebuild=False)` and
`RagService.retrieve_bm25(question, ids, settings)`. It uses only Python's standard
library. The original course demonstration below is preserved for comparison;
it is not imported by the application and its hosted answer-generation step is
not part of these BM25 endpoints.

### Build and search

Upload UTF-8 text/Markdown through the existing document API, or load a bundled
corpus. Example using curl (substitute the returned document IDs in the JSON):

```bash
curl -X POST http://127.0.0.1:8000/api/corpora/kestrel
# Or: curl -X POST http://127.0.0.1:8000/api/corpora/vellora

curl -X POST http://127.0.0.1:8000/api/bm25/index \
  -H 'Content-Type: application/json' \
  -d '{"document_ids":["RETURNED_DOCUMENT_ID"],"settings":{"chunk_size":800,"chunk_overlap":80}}'

curl -X POST http://127.0.0.1:8000/api/bm25/search \
  -H 'Content-Type: application/json' \
  -d '{"document_ids":["RETURNED_DOCUMENT_ID"],"question":"KST-2044","settings":{"top_k":5}}'
```

For Kestrel, include all five returned IDs to search the full corpus. Vellora has
one document. Search builds a missing index automatically; explicit indexing is
optional. Force rebuilding with `POST /api/bm25/index?rebuild=true` using the same
body. Index responses contain the fingerprint, document/chunk counts and `rebuilt`.
Search returns canonical chunk dictionaries with source name, source document ID,
start/end offsets, starting line, text, `retriever="bm25"`, positive `score` and
1-based `rank`. BM25 scores are neither cosine similarities nor confidence values.
No credentials, model download, embeddings or LLM calls are needed.

### Tokenization and ranking

`rag_app/lexical.py` supplies the same tokenizer used by V2 Words: Unicode casefold,
word tokens with internal hyphens and straight/curly apostrophes. `KST-2044`,
`connector-hub`, `CAFÉ` and `isn't` become `kst-2044`, `connector-hub`, `café` and
`isn't`. Other punctuation, underscores and leading `#` separate tokens;
`#oncall-payments` and `oncall-payments` both match `oncall-payments`. Straight and
curly apostrophes are retained, not mapped to each other. No stemming, stopword
filtering, accent stripping, synonym expansion or fuzzy identifier matching.
Index and query use exactly the same policy, versioned in the index manifest.

Standard BM25 uses k1=1.5, b=0.75, and positive IDF
`ln(1 + (N-df+0.5)/(df+0.5))`. Document length means token count per chunk; N/df
and average length are computed over **only the selected chunks**. Each distinct
query token contributes once, so repeating a word does not increase its weight.
Results sort by descending score, then ascending canonical chunk ID. Scores of
zero are excluded; empty/punctuation-only/out-of-vocabulary queries and tokenless
corpora return an empty list. Top-k can therefore return fewer than k chunks.

### Physical storage, restart and updates

Snapshots live at `data/bm25/<sha256-fingerprint>.json`, or
`$RAG_DATA_DIR/bm25/<sha256-fingerprint>.json`. A `RagService(data_dir=...)` argument
takes precedence over the environment, as for dense storage. `data/` is already
Git-ignored. Snapshots include a versioned manifest, exact canonical source chunks,
per-chunk term counts and payload SHA-256. Lengths/document frequencies are derived
from those saved counts when loaded. No additional service or database is required.

The fingerprint includes sorted unique source content IDs, chunk size/overlap,
tokenizer/index versions and BM25 parameters; it excludes top-k and selection order.
Sources are reread and canonical rows checked on each operation; valid saved counts
load without source tokenization or disk rewrite. A restart does not rebuild them.
There is no process-lifetime index cache to become stale. Loading and scoring scan
the small selected corpus; this choice targets the existing local course application,
not a large multi-user search deployment.

- Identical uploads reuse their source ID/index and retain the original filename.
- Changed content has a new source ID. Include that ID in the selection to use it;
  uploads do not silently replace older documents with the same name.
- New selections, chunk settings, BM25 parameters or version changes create a new
  snapshot. No incremental df updates are needed; rebuild the small selection.
- Deleting any source clears **all** BM25 snapshots before removing the source.
  Other selections rebuild lazily, so deleted text cannot persist in old snapshots.
  Dense deletion still removes the source's rows from every dense collection.
- Malformed/changed-checksum/source-mismatched snapshots rebuild automatically.
  Storage permission/write errors produce a handled service error. Forced rebuilds
  publish through a unique temporary file plus atomic replacement; a failed write
  leaves an existing complete snapshot intact. Normal failure paths remove the temp
  file. A process killed during writing can leave an unused `.tmp` file.
- Unused snapshots from changed selections/settings remain until a document is
  deleted or the operator removes the BM25 snapshot directory. Stop the app before
  manual cleanup. On-demand rebuilding recreates the required snapshot.

All service operations use the existing process-local RLock. Run the application
as one local worker, as in V2; cross-process document mutation is not supported.
Snapshot hashes detect accidental corruption, not a malicious local writer who
can also replace source files. Preserve the entire data directory for restart reuse.

### Design choices and limitations

Persisted JSON plus in-memory counters was chosen over RAM-only rebuilds for restart
reuse and inspectability, and over SQLite/search frameworks to avoid migrations and
dependencies for the current 43-chunk corpora. Canonical V2 windows preserve short
headings, exact offsets and IDs `document_sha256:start:end`, allowing future fusion.
Fixed windows can still split words/facts, overlaps repeat evidence, and lexical
matching cannot resolve synonyms or multi-hop chains. Dense is still the default;
there is no fusion, graph, UI toggle or new evaluation configuration in Phase 1.

Tests: `python -m pytest -q tests/test_bm25.py`.

## Original course demo

This guide covers the lexical-retrieval version of the RAG example in
[`ask_bm25_rag_google.py`](./ask_bm25_rag_google.py). It complements the dense,
embedding-based retrieval in [`ask_rag_google.py`](../ask_rag_google.py).

## What BM25 does

Both applications split a document into chunks, retrieve a few chunks for a
question, and send those excerpts to Google Gemini to generate an answer. The
difference is how they retrieve:

- **Dense retrieval** embeds the question and chunks, then finds chunks with
  similar meaning. It can match paraphrases and synonyms, but can miss exact
  identifiers such as error codes.
- **BM25 retrieval** compares the words in the question with the words in each
  chunk. Rare matching words contribute more than common ones. Repeated matches
  have diminishing returns, and scores are adjusted for chunk length.

BM25 is a good fit for exact names, codes, and terms. It does not understand
meaning: if a document calls something “limescale” and the question asks about
“calcium deposits,” there may be no useful word match. Dense retrieval may do
better for that question. Neither approach is best for every query.

## Run the example

Use the project setup in [`README.md`](../README.md) to create a virtual
environment and install dependencies. Set `GOOGLE_API_KEY` in your environment
to a key from [Google AI Studio](https://aistudio.google.com/app/apikey), then
run:

```bash
python bm25/ask_bm25_rag_google.py
```

The script currently searches
`docs/vellora-duo-espresso-machine.txt` for the question “What does error E47
mean and how do I fix it?” It builds an in-memory BM25 index each time it runs,
prints the scores and retrieved excerpts, and asks Gemini to answer using those
excerpts. Retrieval and indexing run locally; the question and retrieved
context are sent to Gemini for generation, so a Google API key and network
access are needed for the complete run.

## Implementation

The example uses a small BM25 implementation directly in the script rather
than a separate search service:

1. `chunk_document()` reads the document, filters short paragraphs, and creates
   fixed-size chunks with overlap. Its chunking settings match the dense RAG
   example.
2. `tokenize()` lowercases text and extracts word-like tokens.
3. `BM25Index` records each token's frequency in each chunk, the chunk lengths,
   the average chunk length, and the number of chunks containing each token.
4. `search()` scores every chunk against the question and returns the
   highest-scoring results. `get_rag_context()` joins the top five excerpts for
   Gemini.

The BM25 parameters are configured near the top of the script:

- `BM25_K1` controls how quickly repeated appearances of a word stop adding
  score.
- `BM25_B` controls how strongly longer-than-average chunks are normalised.
- `CHUNK_SIZE`, `OVERLAP_PERCENT`, and `MIN_PARAGRAPH_LENGTH` control
  chunking.

Tokens that do not occur in any chunk do not affect the ranking: their term
frequency is zero in every chunk. For this example, the rare token `e47` is a
strong signal, so the chunk containing the exact error code is retrieved.

## Investigate dense retrieval with the E47 probe

[`probe_e47.py`](./probe_e47.py) explores why an embedding-based search can miss
an exact error code. From the repository root, with the project dependencies
installed, run:

```bash
python bm25/probe_e47.py
```

The probe runs the `all-MiniLM-L6-v2` embedding model locally. The first run may
need network access to download the model, but it does not need a Google API
key, Gemini, or ChromaDB.

The four tests report:

1. **Tokenization:** how the model splits the question and its error code.
2. **Code swaps:** cosine similarity between the E47 question and the same
   question with other codes. Values closer to 1 mean the question vectors
   point in more similar directions, despite referring to different codes.
3. **Individual entries:** the rank and score of the E47 entry among all error
   entries. If its rank is greater than five, a top-five search over these
   individual entries would miss it.
4. **Chunks:** the ranks of chunks containing E47 using the same chunking
   settings as the dense RAG example, and whether a top-five search would
   include one. A chunk containing the code may still omit part of the answer.

For example, in one local run the E47 entry ranked 35th out of 99 entries,
and the first chunk containing E47 ranked 10th out of 43 chunks: both fall
outside the top five. Results depend on the model, manual, and chunk settings.
The probe ranks recreated chunks with cosine similarity; it does not query
ChromaDB, so the dense RAG script can produce a different ranking.

## Explore the BM25 challenge

The two challenge documents walk through the dense-retrieval failure on an
exact error code, the BM25 solution, and a query where semantic retrieval has
the advantage:

- [`bm25_challenge_part1.md`](./bm25_challenge_part1.md): investigate why
  dense retrieval misses E47.
- [`bm25_challenge_part2.md`](./bm25_challenge_part2.md): inspect BM25 and
  compare lexical and dense retrieval.

The challenge asks you to temporarily edit the document and question in the scripts. Restore those edits after completing it if you want to return to the default examples.
