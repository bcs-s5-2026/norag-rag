# BM25 challenge, part 2: searching for words

Do part 1 (`bm25_challenge_part1.md`) first.

## What went wrong

Our RAG uses **dense retrieval**: each chunk becomes a vector that represents its *meaning*, and we look for the
chunks whose meaning is closest to the question's.

For the embedding model, all the error code entries of the manual look alike: "code, cause, what to do".
And `E47` is not a word it knows: it splits it into pieces (`e`, `##47`) that carry almost no meaning.
For the model, "error E47" is about as close to "error E74" as to "error E12" (similarity around 0.73),
and it has almost nothing to do with what E47 actually means, "grinder blocked by a foreign object" (around 0.08).

Yet the right chunk has something no other chunk has: **the exact word `E47`**.
That is what you used with Ctrl+F.

## The key idea: lexical search, and BM25

Instead of comparing meanings, we can compare **words**: score each chunk by the words of the question that it contains.
This is called **lexical** (or **sparse**) retrieval. Plain Ctrl+F is not enough, though: the question also contains
"what", "does", "the"... which appear in almost every chunk. We need to weigh the words.

**BM25** ("Best Matching 25") is the classic way to do that. It has been the backbone of search engines for decades,
and it is still one of the first things to try. It rests on three ideas:

1. **Rare words count more.** A word found in only one chunk (like `e47`) is a strong signal.
   A word found in every chunk (like `the`) tells us nothing. This weight is called the IDF (inverse document frequency).
2. **Repetition helps, but less and less.** A chunk that contains a query word 3 times is a bit better than one that
   contains it once, but not 3 times better.
3. **Long chunks don't win just because they are long.** Scores are normalised by the length of the chunk.

The exact formula will be covered in the lecture.

## The new script

**Step 1.** Open `ask_bm25_rag_google.py` and compare it with `ask_rag_google.py`
(for example with `diff ask_rag_google.py ask_bm25_rag_google.py`, or side by side in your editor).

- The document, the chunking, the prompt and the generation are the same.
  The script already points to `docs/vellora-duo-espresso-machine.txt` and asks the E47 question.
- What has disappeared? (Look for ChromaDB and the embedding model.)
- Find the `tokenize()` function and the `BM25Index` class. Which of the three ideas above can you spot in the code?

**Step 2.** Run it:

```bash
python ask_bm25_rag_google.py
```

The script builds its BM25 index in memory (no question asked: it only takes a fraction of a second), then retrieves 5 chunks.

- Look at the BM25 scores of the retrieved chunks, and at the first excerpt. Is `E47` there?
- Read the answer. Does it match what you found in part 1, step 1?

**What you should observe:** the first excerpt is the one that contains E47, and the model gives the full answer:
the grinder is blocked by a foreign object, and how to remove it with the hexagonal key.

**Step 3.** Look at the weights BM25 gives to the words of the question. In a Python shell:

```python
import ask_bm25_rag_google as bm
index = bm.BM25Index(bm.chunk_document("docs/vellora-duo-espresso-machine.txt"))
for word in bm.tokenize("What does error E47 mean and how do I fix it?"):
    print(f"{word:6} found in {index.chunk_frequency[word]:2} chunks, weight (IDF) {index.idf(word):.2f}")
```

- Among the words found in at least one chunk, which one does almost all the work?
- Some words get a high weight but are found in **no** chunk ("mean", "fix"...). Can they change the ranking?

## Is BM25 always better?

**Step 4.** Ask both scripts a question phrased in everyday words:

```python
    question = "How do I get rid of calcium deposits in my machine?"
```

Change the question in `ask_rag_google.py` (still pointing to the manual) and in `ask_bm25_rag_google.py`, run both,
and compare the retrieved excerpts and the answers.

- Which script retrieves the descaling instructions?
- Search the manual for "calcium" and "deposits". What do you find? What does the manual call them?
- Why does the embedding search succeed this time?

**What you should observe:** this time, the embedding search finds the descaling section and the answer gives the full
procedure. BM25 retrieves chunks about unplugging the machine, milk, scheduled switch-on...: only one of them mentions
descaling, in passing. The manual never uses the words "calcium" or "deposits", so BM25 can only match "machine", "how", "do"...
(The answer may still mention descaling: the model knows that calcium deposits are limescale. But it can't give the procedure.)

## Conclusion

- **Dense retrieval** (embeddings) understands meaning and synonyms, but is blind to exact identifiers and rare words.
- **Lexical retrieval** (BM25) matches exact words and rewards rare ones, but knows nothing about meaning.

Each one fails where the other succeeds. Can you think of a way to get the best of both? (This is the topic of the lecture.)

## Cleanup

Undo your changes to the two scripts (document and question), for example with:

```bash
git checkout ask_rag_google.py ask_bm25_rag_google.py
```
