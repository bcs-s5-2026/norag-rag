# BM25 challenge, part 1: when meaning is not enough

So far, we used RAG on a novel. Many real RAG systems index technical documentation instead:
manuals, runbooks, API references. These documents are full of **exact identifiers**: error codes,
part numbers, function names, version numbers. Let's see how our RAG copes with them.

## The document

`docs/vellora-duo-espresso-machine.txt` is the user manual of the Vellora Duo, a (fictional) espresso machine.
Like many real manuals, it lists about a hundred error codes, from `E01` to `E99`.

**Step 1.** Open `docs/vellora-duo-espresso-machine.txt` and search (Ctrl+F / Cmd+F) for `E47`.

- How many times does it appear?
- What does error E47 mean, and how do you fix it? Write down the answer: we'll need it to judge the RAG.
- How long did it take you to find it?

## Ask the RAG

**Step 2.** Open `ask_rag_google.py` and make two changes.

Point the script to the manual:

```python
DOCUMENT_FILE = "docs/vellora-duo-espresso-machine.txt"
```

and, in `main()`, ask about error E47:

```python
    question = "What does error E47 mean and how do I fix it?"
```

Leave everything else unchanged (chunking settings, `n_results=5`, the prompt).

**Step 3.** Run the script:

```bash
python ask_rag_google.py
```

The script finds no index for this document and offers to build one: answer `y`.

Before reading the answer, look at the **retrieved context**:

- Which error codes appear in the 5 retrieved excerpts?
- Is `E47` among them?

Then read the answer. Does it match what you found in step 1?

**What you should observe:** the excerpts are full of error codes, some of them close to 47 (E49, E50, E51...),
but not E47 itself. The model can only answer "I don't know", even though the answer is in the manual,
in a single, well-delimited paragraph that you found in a few seconds.

## Investigate

**Step 4.** Try to understand what happened. A few leads:

1. **Rephrase the question**, for example *"How do I fix error E47?"* or *"My coffee machine displays E47. How do I fix it?"*.
   Does it help?

2. **Retrieve more chunks.** Increase `n_results` in `main()` (6, 8, 10...). How far do you need to go
   before the E47 entry shows up? Would you call that a fix? What does it cost?

3. **Look at the question through the eyes of the embedding model.** Run this in a Python shell
   (with the virtual environment activated):

   ```python
   from sentence_transformers import SentenceTransformer, util
   model = SentenceTransformer("all-MiniLM-L6-v2")

   print("1. How the model splits the question into tokens. What happens to E47?")
   print(model.tokenizer.tokenize("What does error E47 mean?"))

   print("2. 'error E47' compared with 'error E74', 'error E12', and with what E47 actually means:")
   emb = model.encode(["error E47", "error E74", "error E12", "grinder blocked by a foreign object"])
   print(util.cos_sim(emb[0], emb[1:]))

   print("3. The real question compared with the real manual entries for E47 and E57:")
   QUESTION = "What does error E47 mean and how do I fix it?"
   E47 = ("E47 - Grinder blocked by a foreign object. Cause: A foreign object, often a small stone "
          "found among the coffee beans, is jammed between the burrs and stops the grinder. "
          "What to do: Unplug the machine, empty the bean hopper with a vacuum cleaner, and use the "
          "hexagonal key supplied with the machine to turn the upper burr anticlockwise until the "
          "object falls out. Never use a knife or a screwdriver.")
   E57 = ("E57 - Main board fault. Cause: The main electronic board detected an internal fault. "
          "What to do: Unplug the machine for one minute, then plug it in again. "
          "If the code persists, contact customer service.")
   emb = model.encode([QUESTION, E47, E57])
   print(util.cos_sim(emb[0], emb[1:]))
   ```

   - What happened to `E47` in the tokens?
   - For the model, how close is "error E47" to "error E74"? To "error E12"?
     And to "grinder blocked by a foreign object", which is what E47 actually *means*?
   - In part 3, the question is about E47. Which entry is closer to it: the E47 entry, or the E57 entry
     ("Main board fault")? What do the two entries have in common with the question, besides the code?

4. **Compare with what you did in step 1.** You found E47 instantly with Ctrl+F.
   What does Ctrl+F do that the embedding search does not?

## Think about a solution

Before moving to part 2, write down your answers to these questions:

- The embedding search looks for chunks with a similar **meaning**. What kind of search would have found E47?
- Could we simply use Ctrl+F? Try to search the manual for the whole question,
  *"What does error E47 mean and how do I fix it?"*. And word by word: how many chunks contain "what"? "error"? "E47"?
- Among the words of the question, which ones are useful to find the right chunk, and which ones are not?
  How could a program tell the difference on its own?

Keep your changes to `ask_rag_google.py`: we'll compare with them in part 2 (`bm25_challenge_part2.md`).
