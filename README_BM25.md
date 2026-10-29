# BM25 retrieval

This guide covers the lexical-retrieval version of the RAG example in
[`ask_bm25_rag_google.py`](./ask_bm25_rag_google.py). It complements the dense,
embedding-based retrieval in [`ask_rag_google.py`](./ask_rag_google.py).

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

Use the project setup in [`README.md`](./README.md) to create a virtual
environment and install dependencies. Set `GOOGLE_API_KEY` in your environment
to a key from [Google AI Studio](https://aistudio.google.com/app/apikey), then
run:

```bash
python ask_bm25_rag_google.py
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

## Explore the BM25 challenge

The two challenge documents walk through the dense-retrieval failure on an
exact error code, the BM25 solution, and a query where semantic retrieval has
the advantage:

- [`bm25_challenge_part1.md`](./bm25_challenge_part1.md): investigate why
  dense retrieval misses E47.
- [`bm25_challenge_part2.md`](./bm25_challenge_part2.md): inspect BM25 and
  compare lexical and dense retrieval.

The challenge asks you to temporarily edit the document and question in the
scripts. Restore those edits after completing it if you want to return to the
default examples.
