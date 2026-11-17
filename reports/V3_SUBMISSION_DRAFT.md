# Current V3 submission email draft — unsent

Updated 9 November 2026 from the rebuilt graph and current audit. This replaces an obsolete email draft that pointed to the first graph; the first graph, evaluations and review artifacts remain preserved unchanged.

To: [professor’s submission address]

Subject: EPITA AI Systems Integration & Operations — C8 RAG V3 — Feras M

Hello,

Please find my RAG V3 work for the C8 assignment:

- Repository: https://github.com/Ferasmich/norag-rag
- Release tag: `v3`, commit `2664b6f2b80cef4c710f30ffb32a2ae7ebe2c857` (verified locally and on origin).
- Main technical report: `REPORT.md`, section “V3 final”; final requirement audit: `reports/V3_SUBMISSION_AUDIT.md`.
- Current graph: `concepts/kestrel_graph_v2/` (42 entities, 39 relations; 43 validated chunk extractions, including 26 empty extractions).
- Current extraction-quality review: `evaluation/graph_review/kestrel-v2-10-triples.json`, ten randomly sampled relations out of 39, graded by Feras M: 10 correct / 0 wrong / 0 unsupported. The original ungraded JSON, full-source Markdown and filled grading CSV are preserved alongside it.
- Final Kestrel retrieval results: `evaluation/results/v3/graph_v2_seedfix_2026-11-08/`.
- Vellora results and before-fix/BM25 comparisons: `evaluation/results/v3/graph_v2_final_2026-11-08/`.
- Updated Kestrel questions: `evaluation/kestrel-v3.jsonl`; the original ten questions are unchanged, with q11/q12 appended.

The implementation includes persistent BM25 on both corpora, independently selectable dense/BM25/graph retrieval, plain RRF, reference origins/ranks and graph-path evidence. Defaults are dense+BM25+graph for Kestrel and BM25 for Vellora. The report presents measured gains and regressions, incomplete factual graph coverage, extraction cost and unknown failed-call usage. It distinguishes the current ten-of-39 manual review from the superseded first graph review.

The final audit passed all 150 tests and freshly reproduced all five mandatory configuration/corpus combinations without altering saved evaluation records. Full interactive/responsive browser verification is not claimed.

Best regards,
Feras M

---

Unsent draft for the recorded sole-developer submission; confirm the recipient and any applicable course/team instructions before sending. The existing v3 tag is published and remains unchanged. The audit’s documentation corrections and earlier V2 documentation corrections are prepared in a separate local documentation-only follow-up commit, pending a normal push to origin/main with owner approval. After that push, submit https://github.com/Ferasmich/norag-rag/tree/main for the implementation plus corrected documentation; https://github.com/Ferasmich/norag-rag/tree/v3 remains the original implementation snapshot. The separate one-line UI status-text correction in rag_app/static/app.js is excluded from the documentation-only commit and remains uncommitted. No push, tag movement or email send is authorized by this preparation.
