# Two-hop challenge, part 1: when the answer is a chain

The BM25 challenge showed a question that embedding search could not answer, but keyword search could.
This challenge shows a question that **neither** of them can answer, even though every fact it needs is in the document.

## The story

We add three short passages about Denis Amselemovitch to *Crime and Punishment*, far apart from each other:

1. **Part I:** Denis lends his silver notebook to the old bookbinder of Stolyarny Lane.
2. **Part III:** the old bookbinder of Stolyarny Lane is called Yakov Glinkin.
3. **Epilogue:** Yakov Glinkin packs up everything in his cellar and leaves Petersburg for Tver.

Then we ask: *"Where is Denis Amselemovitch's silver notebook now?"*

Someone who read the whole book would answer: **most likely in Tver, with Yakov Glinkin.** Let's see what our RAG says.

> Before you start: both files are tracked by git, so you can always go back with
> `git checkout docs/CrimeAndPunishment.txt ask_rag_google.py`.

---

## Step 1: Edit the book

Open `docs/CrimeAndPunishment.txt`. For each passage below, search for the given words, find the end of that paragraph,
and add a blank line followed by the new paragraph (one line, followed by a blank line).

**1a. Part I.** Search for `The house of Kozel`. At the end of that paragraph (it ends with *"Lead the way!"*), add:

```text
Denis Amselemovitch had only one treasure: a silver notebook in which he wrote down everything he overheard in the taverns of the Haymarket. He never let it out of his sight, except once. That winter, he lent it to the old bookbinder of Stolyarny Lane, who had promised to give it a new leather cover by Easter.
```

**1b. Part III.** Search for `question him too much about anything`. At the end of that short paragraph
(it ends with *"he doesn't like that."*), add:

```text
The old bookbinder of Stolyarny Lane was a thin, silent man called Yakov Glinkin. He had worked in the same damp cellar for thirty years, and the whole street knew that he never returned anything on time.
```

**1c. Epilogue.** Search for `quite like an ordinary murderer and robber`. At the end of that long paragraph
(it ends with *"another element in the case."*), add:

```text
In the spring, Yakov Glinkin closed his cellar for good. He packed his tools and every book still on his shelves into two trunks, and left Petersburg to live with his brother in Tver.
```

## Step 2: Edit the script

Open `ask_rag_google.py`. Leave the chunking settings and `n_results=5` unchanged.

**2a. The question.** In `main()`, replace:

```python
    question = "What does this say about Denis?"
```

with:

```python
    question = "Where is Denis Amselemovitch's silver notebook now?"
```

**2b. The prompt.** In `generate_response()`, ask the model to show its evidence. Replace:

```python
    answer the question provided. If the information is not in the excerpts, say you don't know.
```

with:

```python
    answer the question provided. If the information is not in the excerpts, say you don't know.
    Answer in one sentence, then quote the excerpt that supports your answer.
```

## Step 3: Predict, then run

Before running anything, write down your predictions:

- Which of the three new passages will be among the 5 retrieved excerpts?
- What will the model answer?

The index name depends on the **file name**, not its content, so the existing index does not contain the new passages.
Delete it, then run the script and answer `y` when it offers to build a new one:

```bash
rm -rf chroma_db
python ask_rag_google.py
```

Look at the retrieved context **before** reading the answer:

- Which of the three passages are there?
- Is the answer correct? Is it complete? Is it up to date?

**What you should observe:** the Part I passage is retrieved, the other two are not. The model answers, at best,
that the notebook was lent to the bookbinder of Stolyarny Lane, which is no longer true, or that it does not know
where the notebook is now.

## Step 4: Investigate

1. **Would keyword search help?** If you did the BM25 challenge, point `ask_bm25_rag_google.py` to
   `docs/CrimeAndPunishment.txt` and ask the same question. Where do the Part III and Epilogue passages rank?
   (Hint: look at which words of the question they contain.)

2. **Retrieve more chunks.** Increase `n_results`. How far would you need to go? Would you call that a fix?

3. **Follow the chain by hand.** Ask the question in several steps, each one built from the previous answer:
   - *"Who is the old bookbinder of Stolyarny Lane?"*
   - *"Where did Yakov Glinkin go?"*

   Is each passage retrieved now? What did you have to know to write the second and third questions?

4. **Compare the passages with the question.** For the Part III and Epilogue passages, list the words and the ideas
   they share with the original question. What connects them to it?

## Think about a solution

Before moving on, write down your answers to these questions:

- Each step of the chain was easy to retrieve on its own. What made the **whole** question hard?
- The links between the passages are things like *"lent to"*, *"is called"*, *"moved to"*. They are relations between
  people, objects and places. Where, in our pipeline, could such relations be stored? When could they be extracted?
- "The old bookbinder of Stolyarny Lane" and "Yakov Glinkin" are the same person. How would a program know that?
- Could a program follow the chain on its own, as you did in step 4.3? How would it know when to stop?
- What would it cost to do this for every chunk of the book (about 1 600 chunks)? And every time the book changes?

## Cleanup

```bash
git checkout docs/CrimeAndPunishment.txt ask_rag_google.py
rm -rf chroma_db
```

The next run of `python ask_rag_google.py` will offer to rebuild the index of the original book.
