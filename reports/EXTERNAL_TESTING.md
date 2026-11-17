# External testing report

- **Tester:** Makuochukwu Okoene (Makuo), team T2-D, EPITA
- **Application tested:** `Ferasmich/norag-rag`, tested independently from a fresh clone, following the README only
- **Testing date:** 2026-11-15
- **OS / machine:** macOS 15.8, Intel MacBook Pro
- **Python:** 3.12 in a fresh virtualenv, using the pinned versions (`numpy<2`, `sentence-transformers<4`, `transformers<4.50`, `huggingface-hub<1.0`)
- **Branch:** `test/makuo` (`main` and the `final` tag were not touched)

## 1. What worked

| Area | Result |
|---|---|
| Setup from the README | Worked once the Intel Mac pins were applied (see issue 1) |
| Q&A with references | Answers cite the source passages; the reference panel opens the exact chunk |
| Dense / BM25 / Graph selection | Each method can be ticked alone or combined; the trace lists which retriever found which passage |
| Details / trace view | Shows ranks, fused rank (RRF), origins, timings and token counts per question |
| Concept map | Renders the Kestrel graph, concepts open with their evidence, "ask about this concept" works |
| Redaction | Dummy emails and phone numbers were replaced by placeholders before the model call and restored locally in the answer (check B: 1 email, 1 phone reported in the trace) |
| Abstention | Unanswerable questions return "insufficient evidence" instead of an invented answer |
| Automated tests | `pytest`: 195 passed on my Mac on the original code; after my changes (including the mixed-selection and RTF tests) **198 passed** |

Check A (the multi-hop question "who owns the service that raises KST-5031, and what is its channel?"):
- **Dense only:** the runbook chunk is rank 1, but the two `service-catalog` chunks that hold the owner and the channel are only ranks 8 and 15, outside the top 5 sent to the model, so the model abstained (and that abstention still cost one model call).
- **BM25 only:** same failure (those chunks are ranks 16 and 17).
- **Dense + BM25 + Graph:** the graph follows KST-5031, then postroom, then the Messaging team and its channel, and lifts the two catalog chunks to fused ranks 2 and 3. The answer is correct and cited.

This is a good demonstration of why the graph exists: it connects facts that sit in different passages and share no words.

## 2. Issues found

1. **Install on Intel Macs.** The default newest packages do not install or import on an Intel Mac. The pinned versions above fixed it. Added to the README.
2. **Graph not usable on uploaded documents.** The concept graph only covered the five frozen Kestrel files. Ticking it for any uploaded file did nothing useful. This was also a course requirement. **Fixed**, see section 3.
3. **Hard-coded Google model.** The app assumed Google. The course requires `LLM_URL`, `LLM_API_KEY`, `LLM_MODEL` from `.env`. **Fixed**, see section 3.
4. **Mixed selection (found while testing, then fixed).** Selecting the Kestrel files together with any other file made the graph retriever skip entirely, so a question that the graph answers on its own returned "insufficient evidence" as soon as one extra file was ticked (for example the README). The graph is now used for the files it covers, the other files are listed as uncovered in the trace, and the status is `partial`. Verified with 8 files ticked.
5. **RTF saved as `.txt` (found while testing, then fixed).** A file saved from TextEdit as rich text but named `.txt` was indexed with `{\rtf1 ...` markup inside the chunks, which polluted retrieval. Uploads that look like RTF are now refused with advice on how to save plain text. Verified.
6. **Misleading graph note.** A partial graph showed "Partial extraction: undefined/undefined chunks validated". **Fixed**: it now says which files had no graph.
7. **Search-method checkboxes reset** to "Meaning only" after a page refresh or server restart. Two of my "insufficient evidence" results were caused by this and not by a code defect. Not changed; worth knowing when demoing. Always re-tick all three.
8. **BM25 ranks the KST-5031 runbook chunk only 5th** for the owner/channel question, because the question wording is dominated by generic words.
9. **Abstaining still costs a model call**, even when retrieval has already shown there is no supporting passage.
10. **Names are not redacted.** Only emails and phone numbers are. People's names reach the model.
11. **The concept "ask about this" button** does not reuse the chunks the concept was found in; it runs a fresh question.
12. **Chunks are cut mid-word** (fixed 800/80 character windows), which sometimes shows in the reference panel.

## 3. What I changed (on `test/makuo`)

For each decision: what was chosen, why, and what else could have been done.

- **`LLM_URL` / `LLM_API_KEY` / `LLM_MODEL` support** (`rag_app/llm.py`, used by answers and by graph extraction). *Why:* it is a course requirement and removes the Google assumption. Google stays the default and the old `GOOGLE_*` variables still work, so nothing existing breaks. *Alternative:* replace Google entirely; rejected because it would break the original setup.
- **Graph built on upload** (`rag_app/doc_graph.py`). One model call per chunk, with chunk text redacted before it is sent. Extracted quotes are checked to be exact substrings of the chunk, entity names must appear in their quote, and relations must connect listed entities; anything invalid is dropped and counted. Built automatically up to 60 chunks (`RAG_GRAPH_AUTO_MAX_CHUNKS`), manual "Build graph" button up to 300, `RAG_GRAPH_AUTO=0` turns it off. *Why:* the professor asked for upload support, and a size cap keeps cost and wait time predictable. *Alternative:* build lazily on the first question (slower first answer) or only by button (easy to forget).
- **Generic, free-form graph schema** rather than the fixed Kestrel ontology. *Why:* uploaded documents can be about anything. *Alternative:* a fixed ontology, which gives cleaner graphs but only for one domain.
- **Same traversal as the Kestrel graph** (entity-seeded, up to 3 edges), so both graphs behave the same way and share the existing fusion and trace code.
- **Soft failures:** if the graph is missing or fails while other retrievers are selected, the graph is reported as `unavailable` and the others still answer.
- **Mixed selection and RTF guard** (issues 4 and 5).
- **Metrics tab** (`rag_app/metrics.py`, `static/metrics.js`): outcomes and abstention rate, latency, retriever use, time per step, model calls/tokens, graph builds, questions per day. Computed from the existing trace files, so nothing new is stored.
- **Tests:** about 30 new tests (`tests/test_doc_graph.py`, `tests/conftest.py`) covering graph validation, redaction before extraction, failing models, two-hop retrieval, fallback, mixed selection, RTF refusal, LLM config and metrics. The conftest clears the `LLM_*` variables so tests never call a real model.
- **Docs:** README (keys, Intel Mac note, graph-on-upload section), `.env.example`, REPORT.md.

## 4. Known limits of my changes

- Graph quality depends on the extraction model. Seeding depends on how the model names things: "Project Helios" versus "Helios" fell back to weaker lexical matching.
- Entities merge across documents only on an exact normalised name.
- A document graph is tied to the chunk size and overlap it was built with; other settings give a clear error asking to rebuild.
- Names are still not redacted before extraction or answering.

## 5. How I was helped

I ran the application, every test and every check on my own machine, and took all the screenshots and notes in this report. I used an AI assistant (Claude) during the work to help debug what I observed, to propose and write the fixes and tests listed in section 3, and to draft this report and the README text. I reviewed the results on my machine before committing. The commit is made under my own name.

## 6. Final verification

- Full test suite on my Mac after all changes: **198 passed**.
- Redaction check on the trace file (`data/traces/traces.jsonl`): 0 occurrences of the dummy email and 0 of the dummy phone number, so no personal data is stored in traces.
- Server restarted and page hard-refreshed: the graph note now names the files without a graph instead of showing "undefined/undefined".
