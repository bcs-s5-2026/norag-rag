# V3 final verification — awaiting owner approval

> **Historical scope:** this document records an earlier V3 phase or the first graph. For the current recipe-v2 graph, completed 10-of-39 review, final metrics, existing release tag and latest checks, use [V3_SUBMISSION_AUDIT.md](V3_SUBMISSION_AUDIT.md) and the “V3 final” section of [REPORT.md](../REPORT.md). Earlier pending or incomplete statements below are historical, not the current submission status.

> **Superseded (8 Nov 2026, afternoon).** This file describes the first, partial v1 graph (gemini-3.5-flash-lite, 10 relations). The submitted V3 results, rebuilt graph (`concepts/kestrel_graph_v2/`) and the extraction-quality review (`evaluation/graph_review/kestrel-v2-10-triples.json`) are in REPORT.md, section "V3 final". The v1 grades below were AI-drafted reasons confirmed in chat, not an independent review.


Date: 8 November 2026. Local implementation and retrieval evaluation are complete within the approved scope. **No commit, tag, push or submission has been performed.** The Concept Graph is usable but partial; its limitations are part of the proposed submission.

## Verification results

| Requirement / check | Status | Evidence |
|---|---|---|
| Persistent reusable BM25 on both corpora; stable dense-compatible chunk IDs; deterministic ranking | PASS | `rag_app/bm25.py`, `lexical.py`; `tests/test_bm25.py`; Phase 1 report. Valid snapshots survive restart without rebuilding. |
| Exact large “Watch your sources!” on hidden `/bm25`; no frontend reference | PASS | `rag_app/api.py`; automated route and frontend checks. |
| Fixed typed entity/relation schema, validation/quarantine and source provenance | PASS | `graph_schema.py`, `graph_build.py`; exported raw graph, caches, rejections and attempt ledger. |
| Approved model, five-source scope and lifetime 43-request ceiling across resumes | PASS | `V3_EXTRACTION_APPROVAL.json`, `V3_EXTRACTION_RESULTS.json`, `V3_FINAL_CHECKS.json`; 43 spent, zero remaining. No model switch. |
| Corpus extraction coverage | PARTIAL | 29 strict-valid chunk responses (27 empty), 10 rejected and four provider errors. No further attempts made. |
| Auditable offline context repair and conservative entity resolution | PASS | `graph_context.py`; six repair records; nine recovered proposals, one truncated raw relation excluded. Original quotes preserved. No weak semantic merges. |
| Persistent graph, build/cache identity, resume and dry-run controls | PASS | `data/graphs/` runtime state; portable `concepts/kestrel_graph/`; mocked construction tests. App restart does not rebuild graph. |
| Actual calls, token usage, latency and cost reporting | PASS with unknowns | 43 attempts, 237.465s build-body latency; known 50,239 input / 1,845 output tokens. Known-usage estimate $0.0196842; four failed-call usages and total invoice cost unavailable. |
| Graph retrieval returns ranked canonical chunks | PASS | `graph_retrieval.py`; exact entity/alias seeds plus local lexical fallback, bounded traversal, checksum/proof validation and explicit errors. |
| Any enabled retriever subset, standard RRF, depth/top-k controls and provenance | PASS | `models.py`, `service.py`, `fusion.py`; independent dense/BM25/graph; k=60 default and deterministic ID ties. |
| UI and CLI toggles; citation origins/ranks; graph edges, conditions and source passages | PASS automated / browser unverified | `api.py`, `static/`, `evaluation/v3.py`; API/template tests and JavaScript syntax passed. Interactive browser host unavailable. |
| Required dense / two-way both-corpus and three-way Kestrel evaluations; HitRate/Recall @1/3/5/10 overall/by type | PASS | Nine final runs in `evaluation/results/v3/submission_2026-11-08/`; eight main configurations plus depth-40 sensitivity. All zero-LLM, zero retrieval execution failures. Partial graph status exposed. |
| Two additional Kestrel two-hop questions; original questions/evidence unchanged | PASS | `kestrel-v3-additions.jsonl`, combined `kestrel-v3.jsonl`; original V2 bytes are the exact combined-file prefix. |
| Ten randomly selected graph triples manually graded | PASS | Feras M: **10 correct / 0 wrong / 0 unsupported**. Seed 20261108, population 10. Original ungraded artifact and all quote/expansion metadata preserved. |
| V1/V2 and prior benchmark preservation | PASS | 41 frozen document/evaluation files unchanged; intentional source extension only in `evaluation/v3.py`. All four V2 dense baselines reproduced in regression tests. |
| Full regression suite | PASS | **144 passed in 11.96s**, offline MiniLM cache; `node --check rag_app/static/app.js` and `git diff --check` passed. |
| Documentation, measured defaults, failure analysis and graph-fusion survival experiment | PASS | `README.md`, appended `REPORT.md`, `V3_FINAL_INTEGRATION.md`. |
| Credentials absent from deliverables | PASS | Actual configured secret values scanned against changed/new files without printing values; no matches. `.env` and runtime data remain excluded. |
| Git tag `v3`, published repository and submission email | PENDING APPROVAL | Deliberately not executed under the owner's restriction. Local email draft: `V3_SUBMISSION_DRAFT.md`. |

## Measured defaults and limitations

Use **dense for Kestrel** and **BM25 for Vellora**, final top-k 5. Kestrel Recall@5: dense 75.0%, dense+BM25 74.2%, three-way 70.8%. Vellora BM25 reaches 91.7% versus dense 58.3%. All-three retrieval is available for inspection, but its partial graph is not the default. Increasing depth from 20 to 40 increased graph survival at top-5 from 12/18 to 17/18 candidates while worsening Recall@5 to 50.8%; retain depth 20.

Human review establishes correctness of the ten retained relations, **not raw extraction precision or complete corpus coverage**. Nine relations retain explicit offline quotation-expansion provenance. New q11/q12 are same-file multi-hop and do not demonstrate broad cross-document reasoning; original q08 remains incomplete. Full costs for failed calls, interactive browser verification and newly generated hybrid-answer quality are unavailable. No optional features or further model calls are needed to present these measured limitations honestly. Improving graph coverage would require separate approval for a new extraction plan.

## Reviewable submission materials

- Detailed architecture, decisions, all K/type metrics, per-question failures and exact commands: [V3_FINAL_INTEGRATION.md](V3_FINAL_INTEGRATION.md).
- Human grades with exact passages: [kestrel-10-triples.md](../evaluation/graph_review/kestrel-10-triples.md).
- Machine results: [summary.json](../evaluation/results/v3/submission_2026-11-08/summary.json), [comparison.csv](../evaluation/results/v3/submission_2026-11-08/comparison.csv), [run_manifest.json](../evaluation/results/v3/submission_2026-11-08/run_manifest.json).
- Integrity checks: [V3_FINAL_CHECKS.json](V3_FINAL_CHECKS.json). Submission file checksums: [V3_SUBMISSION_MANIFEST.json](V3_SUBMISSION_MANIFEST.json).

Awaiting the owner's review of this report before any publication or submission action. The required release tag has not been created.
