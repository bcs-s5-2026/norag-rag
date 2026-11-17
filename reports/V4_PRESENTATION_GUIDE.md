# V4 oral presentation guide

Preparation notes for the final presentation (C9: Parts A and B; C10: Part C and recap). No slides are required by the handout; the demo is "ask a question, then open its trace and explain what happened". Numbers come from `evaluation/results/v4/` and REPORT.md.

## 1. The project in four steps (30 seconds)

| Version | What it added | What we measured |
|---|---|---|
| V1 | Naive RAG web app: upload, chunk (800/80), MiniLM embeddings, Chroma, Gemini, validated citations | Hit@5 = 7/12 on the Vellora manual |
| V2 | Second corpus (Kestrel), evaluation per question type, Words tab, hand grading | Kestrel 6 correct / 3 partial / 1 wrong; dense misses exact codes |
| V3 | Hybrid search: dense + BM25 + concept graph, fused with RRF | Kestrel Recall@5 0.75 → 0.79 (two-hop 0.50 → 0.89); Vellora 0.58 → 0.92 with BM25 |
| V4 | Observable (traces), a new feature (concept map), responsible (redaction), cleaned-up page | 81/81 rankings identical to V3; see below |

One sentence: *V2 told us where V1 failed, V3 fixed retrieval and proved it, V4 lets anyone see what the app does and stops personal data from leaving the laptop.*

## 2. What problem V4 solves

- **Before:** an answer appeared and we could not say which search found the passage, how long each step took or what the call cost. A failed question left nothing behind.
- **Before:** an e-mail address typed in a question went to Google as it was.
- **Before:** the V3 graph was used for retrieval but the user could not look at it.

## 3. How tracing works (Part A)

- A `Trace` object is created at the start of a question. Each step runs inside `with trace.span("name") as info:`; the span measures the time and the step writes what happened into `info`.
- Spans of a question: dense, BM25, graph, fusion, redact, generate, validate. At the end the trace gets an outcome (answered, abstained, invalid, error) and is appended as one JSON line to `data/traces/traces.jsonl`.
- The answer carries the trace id; **Details** calls `GET /api/traces/{id}` and shows a table: step, time, what happened.
- Never stored: API key, chunk text, answer. Stored: chunk ids, counts, tokens, cost, the question after redaction. Kept 30 days, local only.
- Indexing: one trace when *Prepare documents now* is clicked, and one when a question has to embed a new document.

## 4. How the concept map gets its evidence (Part B)

- In V3 the LLM extracted triples (subject, relation, object) from each chunk, and every triple was saved with the exact quote, its character offsets and the chunk id. The loader checks that each quote really is at that position.
- The explorer does not compute anything new: for a concept it collects the links where it is subject or object and the saved quotes and chunks. No LLM call, about 1 ms.
- So when the page shows "ledger — OWNED_BY → Payments Core", the sentence under it is the sentence the triple came from, and "Open the full source chunk" shows the chunk.

## 5. How redaction protects personal data (Part C)

- Just before the LLM call, e-mail addresses and phone numbers in the question and in the retrieved passages become `[EMAIL_1]`, `[PHONE_1]`. The mapping stays in memory for that request.
- Search uses the original question because it runs on the laptop. The trace stores the redacted question.
- After the answer is validated, placeholders are replaced by the real values on the laptop. If the model wrote an address or number that is not one of the hidden values, it is removed.
- Patterns only: no extra model, nothing sent out to detect it. Names are not detected.

## 6. Live demo (about 4 minutes)

Before class: start the server, ask one question so the embedding model is loaded, check the API key works.

1. **Load the Kestrel demo documents** → **Find an answer** (KST-5031 question). Show the answer and one supporting reference.
2. **Details.** Read the table aloud: three searches (the graph matched the concept KST-5031), fusion line "#1 … found by bm25 #1, dense #1, graph #1", redaction count, LLM call with tokens and cost, citation check. Point out: chunk ids only.
3. Type: *"My email is sam.student@example.org and my phone is +33 6 12 34 56 78. How do I request a refund, and where do I send the request?"* → the answer contains billing@kestrel.example → **Details**: the stored question shows `[EMAIL_1]` and `[PHONE_1]`, "emails: 2, phones: 1".
4. **Concept map** → *Payments Core* → click *ledger* → open a link and its source quote → **Ask a question about this concept**.
5. If asked about failures: in *Advanced search settings* set chunk size to 500 with the graph ticked, ask → red message with **Details** → the trace shows which step failed. Set it back to 800.
6. **Recent activity** at the bottom: every step of the demo is listed.

Fallback if the network or the API fails: the error itself is a valid demo of point 5, and the concept map and Recent activity work offline.

## 7. What the experiments showed

- **No regression:** the V3 retrieval evaluation re-run on V4 gives the same ranked chunks for 81 of 81 questions.
- **Concept map:** 42 concepts, 156 quotes checked against the source files, 0 wrong.
- **Eight live questions:** 7 answered, 1 abstained as expected; median 1.3 s, of which 25 ms is retrieval; about $0.0018 per question. Not yet hand-graded (say so if asked, unless the review is done by then).
- **Redaction made an answer wrong, and we saw it:** with the address hidden, the model invented `refunds@kestrel.analytics`; without redaction it was right. A prompt sentence fixed the simple case (4/4). With two placeholders the model guessed the real address; a "reject" guard then refused a correct answer 3/3, so the final rule is "keep if it equals a hidden value, remove otherwise" (3/3 correct).
- **A bug found only by a live test:** a phone number followed by a full stop kept its last two digits.
- **A cost finding from the traces:** one question used 8,055 input tokens instead of about 3,400 because graph path ids are sent with the evidence (84 ids for the hub concept *Enterprise*). +$0.0014 on that question. Documented, not changed.

## 8. Limits to state openly

- Names and unusual formats are not redacted; role addresses are treated as personal.
- The concept map only shows what V3 extracted (17 of 43 chunks gave triples) and only for Kestrel.
- Traces are a flat file for one user; no metrics page.
- Small question sets: one question moves Recall@5 by 0.1.
- The code was written with AI assistants and reviewed by the team; results are from saved runs.

## 9. Likely questions and short answers

**Why JSON lines and not Langfuse or SQLite?** Nothing to install, one file we can open and read, and the traces stay on the laptop. Without a metrics page there is nothing to query. With many users we would move to SQLite or a tracing tool.

**What is a span?** One timed step of a request with attributes. A trace is the list of spans for one request.

**Why are chunk ids enough?** The id is `document hash:start:end`, so the text can be found again in the local document. The trace does not duplicate the corpus.

**How do you compute the cost?** Tokens reported by the provider in `usage`, multiplied by the price per million tokens of the model ($0.30 input, $2.50 output for flash-lite). If the model is not in the table, the cost is shown as unknown.

**What is in the trace when the LLM returns invalid JSON?** Outcome "invalid", the validate span marked failed, no answer shown, and the Details button on the error message.

**Why the concept map and not reranking?** We could check it completely (every quote against the source) and it needs no extra model or call. A reranker's gain on 22 answerable questions would be inside the noise.

**Does the explorer call the LLM?** No. The LLM was used once in V3 to build the graph; the explorer reads that file.

**What if the graph is wrong?** Each link shows its quote, so the user can see it. In V3 a sample of 10 relations was reviewed by hand: 10 correct. Missing links are the bigger problem than wrong ones.

**Why regular expressions and not an LLM or NER for personal data?** An LLM would receive the data in order to find it. NER needs another model and still makes mistakes on names. Patterns are predictable and testable; the cost is that names are missed.

**Why not redact before retrieval?** Retrieval is local; the original question gives better matches. Only what leaves the machine or is written to the trace is redacted.

**Can the model undo the redaction?** It never sees the value, but it can guess a plausible one. We observed this. The guard removes any address or number that is not one of the hidden values.

**How do you know V4 did not break V3?** Same evaluation, same questions, identical ranked lists for 81 of 81 questions, and the 150 earlier tests pass unchanged.

**What would you do next?** Send only id, name and text to the model (saves tokens), a metrics page from the traces, name detection, and hand-grade more answers.

**Who did what?** State the real split. The commits in this repository are by Feras; say plainly which parts each person can explain.
