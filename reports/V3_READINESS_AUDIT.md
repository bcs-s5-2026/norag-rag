# RAG V3 readiness audit

> **Historical scope:** this document records an earlier V3 phase or the first graph. For the current recipe-v2 graph, completed 10-of-39 review, final metrics, existing release tag and latest checks, use [V3_SUBMISSION_AUDIT.md](V3_SUBMISSION_AUDIT.md) and the “V3 final” section of [REPORT.md](../REPORT.md). Earlier pending or incomplete statements below are historical, not the current submission status.

Audit date: 7 November 2026 (Europe/Paris). Repository: `norag-rag`, HEAD `8e86a027eb45d528eba5a153fe9804015fda8fa8`.

## Verdict and scope

**V2 is a useful, reusable baseline; the integrated V3 hybrid system is not implemented.** Dense retrieval, exact chunk provenance, two-corpus evaluation and quote recall exist. BM25 exists only as a separate Vellora demonstration. There is no application concept graph, graph extraction/validation, graph retrieval, RRF, retriever selection, or graph-path UI.

Implement BM25 and dense+BM25 fusion first, then graph extraction and retrieval. Retain the current Python/FastAPI/static-JS/Chroma architecture. A small local graph snapshot and deterministic traversal are sufficient; a graph database or full GraphRAG framework is unnecessary for 43 Kestrel chunks at the existing default settings.

The professor's PDF was available locally and read in full using `pdftotext -layout` before inspecting application internals:

`/Users/ferasmich/Documents/Feras/EPITA/AI Systems Integration & Operations/Versions/BCS 2026 - S5 - AI Systems Integration And Operations - C8 - Session 3 - Part IV - RAG - V3.pdf`

PDF page references below are physical pages, counting the title as page 1. It specifies submission on Monday 9 November 2026 at 11:59 a.m. (page 2), by email with the team GitHub link and teammates copied. This audit sends no email. Assignment instructions and challenge-file editing instructions were treated as requirements to assess, not authorization to execute them.

This is a static, read-only audit except for this report. No dependencies installed, application imports/startup, model downloads, embeddings, LLM calls, evaluation runs, application edits, commits, pushes or tag creation. Read-only Python inspected saved JSON, hashes and source windows. No visual/browser pass or fresh test-suite pass is claimed. The pre-existing untracked `reports/V2_POST_SUBMISSION_AUDIT.md` is preserved; its historical test claims are not new results from this audit.

## Current architecture and reusable components

| Component | Exact reference | Current behavior and reuse |
|---|---|---|
| Web/API | `rag_app/api.py:12-49,57-98,136-144` | FastAPI synchronous endpoints for documents, index, ask, search, evaluations; static frontend mounted last. `/about` is an existing V2 special page, not `/bm25`. Module-level app initialization creates service storage, so it was not imported during this audit. |
| Request/answer contracts | `rag_app/models.py:4-45,54-74` | Strict settings: 100-1000 characters, overlap smaller than size, top-k 1-20. Selection requires documents. Generated answers require consistent citation/answerability fields and no duplicate citations. No retriever settings or graph schemas. |
| Source management | `rag_app/service.py:35-95,134-146` | Content-hashed UTF-8 documents under `RAG_DATA_DIR` or `data/documents`; same decoded content retains first filename. Upload deduplicates; delete removes Chroma rows/markers and source. Reuse document hashes, but extend deletion to new indexes. |
| Canonical chunking | `rag_app/service.py:24-32,106-128` | Exact character windows, default 800/80; IDs `document_sha256:start:end`; text, name, offsets and line retained. Reuse these exact chunks across every retriever. |
| Dense embedding/index | `rag_app/service.py:14,45-61,97-128` | CPU `all-MiniLM-L6-v2`, persistent Chroma in `data/chroma`; cosine collections keyed by embedding model and chunk settings; per-document ready markers and partial-build retry. |
| Dense retrieval | `rag_app/service.py:148-163` | Index selected documents, filter before top-k, return chunk dictionaries with `similarity=1-distance`. Single dense ranking; no shared retriever abstraction yet. |
| Prompt/LLM | `rag_app/service.py:165-206` | OpenAI SDK to Google's compatible endpoint; environment-selected model, default `gemini-3.5-flash-lite`; temperature 0, JSON, 45-second timeout, no SDK retries. System prompt treats question/documents as untrusted, instructs evidence-only answers/abstention. Pydantic and citation-ID membership checks reject invalid results. Usage metadata is discarded. No live model-availability verification was attempted. |
| UI | `rag_app/static/index.html:45-79,111-148`; `rag_app/static/app.js:19-29,108-159,234-285,374-389` | Chunk settings, source selection, answers, expandable citations, evaluation controls and grading. All reference cards assume a numeric cosine similarity. No retriever toggles, origin ranks or graph paths. |
| V2 word analysis | `rag_app/words.py:8-10,13-38` | Unicode casefolded tokens retain internal hyphens/apostrophes; exact chunk IDs/offsets already match the service. Good starting tokenizer for integrated BM25, with a versioned policy. |
| Standalone demos | `ask_rag_google.py:45-76,109-149`; `ask_norag_google.py:79-136`; `README.md:12-23` | Separate CLI examples, original `chroma_db/` lifecycle and prompts. Do not treat them as application implementations or import them for V3. |
| Dependencies | `requirements.txt:1-9`; `requirements-dev.txt:1-3`; `requirements-lock.txt` | dotenv, requests, OpenAI, Chroma, sentence-transformers, FastAPI/Uvicorn, multipart, Pydantic; pytest/httpx for development. Existing standard library and Pydantic suffice for the proposed BM25/graph implementation. No graph-specific dependency is currently required or present in application imports. |

### Existing BM25: useful formula, incomplete integration

`bm25/ask_bm25_rag_google.py:45-56,59-116,158-180` hardcodes Vellora, 800-character chunks, 10% overlap, BM25 k1=1.5 and b=0.75. It builds counters, chunk lengths and document frequencies in RAM on every execution and scans every chunk per query. `tokenize()` at lines 76-77 uses lowercase `\w+`.

Limitations:

- No Kestrel multi-file index, selected-document filtering, durable index format, update/delete invalidation, API integration or evaluation integration.
- `KST-2044` becomes `kst` and `2044`; hyphenated names and on-call channels are split. No stemming/synonym handling; repeated query terms repeat their score contribution. Decide these policies explicitly rather than silently changing Words behavior.
- Paragraphs shorter than 20 characters are removed (`:64-66`), changing source offsets and potentially dropping headings/facts. Demo chunks cannot be fused safely with application chunks by string equality or position.
- Search returns text/score pairs, not canonical IDs or metadata. Zero-score results are still returned, with positional ties; empty chunks or an all-zero-token corpus can trigger division by zero.
- OpenAI client initialization at module scope (`:25-28`) couples import to credentials; the runnable demo also invokes hosted generation. Extract/adapt pure indexing logic later rather than importing the demo.
- The prompt is a literary-analysis prompt (`:129-139`) despite the manual corpus; it lacks the application's structured answer/citation checks.

The PDF asks the team to choose and document index location/build/update policy; **persistence itself is not an explicit mandatory storage technology**. A documented in-memory rebuild could satisfy the design discussion, but a versioned disk snapshot with an in-memory scoring cache is more reproducible and inexpensive here.

## Requirement-by-requirement compliance matrix

Status meanings: **Implemented** = the current repository supplies the requirement; **Partial** = reusable behavior exists but not the complete V3 requirement; **Missing** = no executable implementation or required artifact found. Documentation about a feature is not implementation. Proposed work below does not change these statuses.

| PDF | Requirement | Status | Evidence / precise gap |
|---|---|---|---|
| 3-4 | Preserve dense V2 baseline alongside new retrievers | Implemented | `rag_app/service.py:148-163`; four dense result files listed below. Dense-only must remain reproducible after V3. |
| 5 | BM25 on both corpora | Partial | `bm25/ask_bm25_rag_google.py:45,80-116` handles Vellora only, outside app/evaluator. Kestrel/application implementation missing. |
| 5,12 | Document BM25 index location, build, tokenization, updates, alternatives and decision | Partial | `bm25/README.md:36-69` documents demo RAM index and tokens. No V3 multi-document lifecycle or decision log; `REPORT.md:74-84` is V2. |
| 5 | Unlinked/unreferred `/bm25`, large exact text `Watch your sources!` | Missing | Only special route is `/about`, `rag_app/api.py:136-140`; no `/bm25` route or file. Add before static mount; no frontend link, menu, JS mention or referral. |
| 6 | LLM triples extracted at indexing time on Kestrel | Missing | Only LLM use is answer generation (`service.py:165-189`) and no-context checks (`evaluation/v2.py:37-50`). `concepts/concept_graph_challenge_part1.md:1-100` is an exercise, not extraction code. |
| 6 | Entity/relation schema; fixed/open rationale | Missing | `models.py:32-45` validates answers only. No typed nodes, relation directions or allowed endpoint combinations. |
| 6 | Every graph node and edge points to source chunks | Missing | Chunk offsets exist (`service.py:120-125`), but no graph provenance. Node and edge provenance both required. |
| 6 | Validate every LLM extraction and define invalid-output behavior | Missing | Existing answer validator is reusable, not graph validation (`service.py:197-202`). No extraction quarantine, repair or failure manifest. |
| 6 | Entity resolution; one correct merge and one wrong/missed merge | Missing | No canonical entity IDs, alias policy, merge logs or observed examples. Must report real extraction observations, not invented examples. |
| 6 | Graph build calls, tokens, time; models/keys if necessary | Missing | Answer client discards usage; no build job, ledger or cached extraction. Multiple models/keys are permitted, not mandated. |
| 6-7 | Research existing graph systems, choose retrieval and explain alternatives | Missing | Challenge brief only. External research supporting the proposed design appears below; repository's V3 decision log remains to be implemented. |
| 7 | Graph question-to-ranked-chunks retriever | Missing | `service.py:148-163` is dense only. No entity matching, graph traversal, scoring or chunk projection. |
| 8 | Independently switch every retriever from UI and evaluation command | Missing | `models.py:4-8,54-59`, `evaluation/v2.py:119-127`, `app.js:19-29,379-386` have no retriever selection. |
| 4,8 | RRF over exactly the enabled retrievers | Missing | No RRF module/call in service/evaluation. Need canonical-ID deduplication and deterministic ranks. |
| 8 | For each answer reference: originating retriever(s) and rank(s) | Partial | Exact citation lookup exists (`service.py:198-206`); `app.js:145-157` shows source/cosine only. No per-retriever ranks. |
| 8 | Graph-enabled UI: question entities, followed edges, originating chunks | Missing | `app.js:108-159` renders answer/reference cards only. No path trace or visualization. |
| 9 | Dense on both corpora | Implemented | `evaluation/v2.py:60-102`; `evaluation/results/{kestrel,vellora}-{800-80,500-100}.json`. |
| 9 | Dense+BM25 on both; dense+BM25+graph on Kestrel | Missing | No such configurations or measured result files. At least five corpus/configuration runs required. |
| 9 | HitRate and Recall at 1,3,5,10 overall/per type | Partial | `evaluation/v2.py:17,53-57,69-77,98-101` computes any-quote hit and macro quote recall for dense. Need V3 configurations, explicit Recall@K definition, full reporting grid. |
| 9 | Six named types; retain old questions, append explicitly | Partial | `evaluation/kestrel.jsonl:1-10` has all six types; Vellora has `other` and lacks three answerable types. Existing hashes are recorded (`v2.py:97`). Never silently relabel old Vellora rows; report absent types as N/A with counts. |
| 9 | At least three Kestrel two-hop questions, evidence quote per hop | Partial | Only q08 (`evaluation/kestrel.jsonl:8`). Two proposals below, not added to frozen artifacts in this audit. |
| 9 | Ten randomly sampled graph triples, manually graded correct/wrong/unsupported, file and counts | Missing | No extracted graph or grades. Existing answer grades (`models.py:62-74`) use a different rubric and cannot substitute. |
| 9 | Cost per question/configuration: calls, tokens, latency | Missing | `service.py:176-187` returns only content; `v2.py:94-102` records timestamp/model/settings but no per-question cost. Six-second pacing is not measured latency. |
| 10 | Results table: configurations × corpora × types; default justified by numbers | Partial | `REPORT.md:92-159` contains dense chunk-setting comparisons. No hybrid table or measured V3 default. |
| 10 | Measure whether graph chunks survive fusion/top-k; adjust and remeasure if not | Missing | No graph ranking, fusion traces or candidate-depth experiment. |
| 10 | A question made worse by adding a retriever, with explanation | Missing | V2 reports chunk-size regressions (`REPORT.md:111-159`), which are not retriever-addition regressions. |
| 10 | Graph counts, merges, build cost, wrong merge/bad triple and consequence | Missing | No graph artifacts or measured downstream failure analysis. |
| 11 | Three-person teams: path-as-context OR weighted RRF, measured | Missing (conditional) | `REPORT.md:5` identifies a sole developer; this extra is not triggered by current recorded team size. Confirm participation arrangements separately; do not add optional scope by default. |
| 12 | Updated question sets, all configurations, ten triple grades | Partial | V2 datasets/results exist; no V3 additions/configurations/triple grades. |
| 12 | README: toggles, graph build, evaluation | Partial | `README.md:82-105` explains V2 controls/CLI, no V3 operations. |
| 12 | REPORT: BM25 choices; graph design/cost/failures/options; fusion; decision log | Partial | `REPORT.md:7-24,74-84` provides reusable log structure, not V3 decisions/results. |
| 12 | Git tag `v3` | Missing | Local `git tag --list` returned only `v1`, `v2`. No remote-tag check performed. Creating any tag is outside this audit. |
| 2 | Submission email with repo link and teammate CCs | Missing (not evidenced) | No V3 submission evidence inspected. This is a future owner action; the audit neither sends nor drafts an email. |

Optional PDF features (page 6): properties, temporal validity, aliases, graph on own corpus/subset. None is implemented as a graph feature. They are not mandatory compliance failures. Document whichever are actually chosen; temporal separation is nevertheless important to avoid mixing the two billing policies.

## V2 evaluation inventory and integrity findings

Authoritative runtime datasets: `evaluation/kestrel.jsonl` (10 questions, 8 answerable), `evaluation/vellora.jsonl` (15, 12 answerable). Frozen V1: `evaluation/questions.json`, `evaluation/baseline.json`, `evaluation/run.py:13-48`.

| Corpus | Type counts | Current corpus |
|---|---|---|
| Kestrel | exact_identifier 2; split_answer 2; vocabulary 1; versions 2; two_hop 1; not_in_corpus 2 | All five `docs/kestrel/*.md`, including both billing-policy versions; 29,568 decoded characters; 43 chunks at 800/80, 76 at 500/100. |
| Vellora | exact_identifier 4; vocabulary 4; other 4; not_in_corpus 3 | `docs/vellora-duo-espresso-machine.txt`; 31,036 characters; 43 chunks at 800/80, 78 at 500/100. Novel files are not evaluation corpora. |

Measured saved dense runs (not freshly rerun):

| File under `evaluation/results/` | Hit@1 | Hit@3 | Hit@5 | Hit@10 | Macro quote Recall@5 | Recall@10 |
|---|---:|---:|---:|---:|---:|---:|
| `kestrel-800-80.json` | 5/8 | 7/8 | 7/8 | 8/8 | 81.25% | 93.75% |
| `kestrel-500-100.json` | 2/8 | 6/8 | 6/8 | 8/8 | 71.875% | 90.625% |
| `vellora-800-80.json` | 6/12 | 6/12 | 7/12 | 10/12 | 58.333% | 83.333% |
| `vellora-500-100.json` | 2/12 | 6/12 | 8/12 | 10/12 | 66.667% | 83.333% |

Dataset SHA-256 values independently matched all four stored runs:

- Kestrel: `6c00d42de872482820a4ddc4fca21bf5207bc7c6749f1e0a60e8586bd2c94d75`.
- Vellora: `81f02e4b28216d456e589cf04338d941e9a9c90c09e8c536ec8f73abd8d495fd`.

All four runs' recorded corpus-file hashes match current bytes. All saved per-question hit/recall arrays were independently recomputed from their retrieved text/source names and expected quotes. Every gold quote can fit wholly in at least one canonical chunk at both existing settings: the current misses are not an unavoidable whole-quote chunk-boundary ceiling. This does not establish fresh ranking reproducibility or validate every generated assertion.

Answer/no-context evidence:

- `evaluation/results/kestrel-reviewed.json`: 10 grades, 6 correct/3 partial/1 wrong, all no-context flags false. q08 is wrong; its dense 800/80 quote recall is 0.5 even at k=10. See `evaluation/kestrel.jsonl:8` and `REPORT.md:100,122`.
- `evaluation/results/vellora-reviewed.json`: 15 no-context flags, true only q09/q10; RAG answer grades remain null. `vellora-ai-assessed.json` preserves the earlier AI assessment; later human-verification metadata is separate, as explained in `README.md:123-127`.
- Supporting raw/failed/paced artifacts: `kestrel-answers-no-context.json`, `kestrel-answers-no-context-paced.json`, `kestrel-no-context.jsonl`, `vellora-no-context.json`, `vellora-no-context-paced.json`, `vellora-no-context.jsonl`. Preserve errors/history rather than selectively retaining successes.
- Reports: `REPORT.md:55-159` and later review sections, `reports/RAG_V2_IMPLEMENTATION_REPORT.md`, `reports/V2_FINAL_SUBMISSION.md`, `reports/words_diagnoses.json`, and the pre-existing post-submission audit.

Existing tests to reuse: `tests/test_rag.py:30-66,100-158` (workflow, selection/deletion, offsets, citations, errors, baseline); `tests/test_v2.py:14-28` (frozen V1/current Kestrel), `:31-67` (tokens/metrics/evaluator), `:89-145` (saved grades, imports, errors). The exact `len(kestrel)==10` assertion at line 25 must remain meaningful for the frozen set: create a separate V3 loader/test rather than breaking the V2 invariant by appending in place.

### Metric contract for V3

Reuse the V2 definitions explicitly: a gold item is an expected `(source, literal quote)`, not an arbitrary chunk ID. HitRate@K is the fraction of answerable questions with any gold item found; Recall@K is the mean per-question fraction of gold items found in the ranked prefix. For multi-hop questions also report complete-evidence rate (all gold hops retrieved). A hit alone does not prove the chain was recovered.

Retain `quote_recall` for historical compatibility and expose/document it as evidence Recall@K in V3. Report all six requested types plus Vellora's existing `other`; show `n`, and N/A for empty categories or unanswerable-only retrieval denominators. `not_in_corpus` needs separate abstention/unsupported-answer review, not invented gold recall or automatic zeros. Keep old question labels/answers/evidence immutable.

Evaluate the old Kestrel 10-question slice separately from the augmented 12-question set so adding easy/hard questions cannot masquerade as retrieval improvement. Run dense on the new questions too. Freeze chunk settings, embedding/model revisions, generation prompt, final context k and candidate depths when comparing retriever combinations. Report sensitivity experiments separately.

## Simplest sound implementation architecture (proposal only)

Keep `RagService` as the orchestration boundary. Add small pure modules for canonical chunks, BM25, graph schema/build/storage/retrieval, fusion, and a separate V3 evaluator; avoid a second application stack. Preserve V2 entry points and result schemas.

1. **Shared retrieval contract.** Each retriever returns ranked canonical chunk IDs and its own raw score plus metadata; the orchestrator attaches `origins={retriever: {rank, raw_score}}`, fused score and graph trace. Rank is 1-based; deduplicate within each retriever before fusion. Keep source text/offsets from canonical storage, never model-supplied replacements. Dense-only requests default to current behavior. Use a distinct retrieval configuration object so collection names do not depend on toggles/top-k.
2. **BM25 snapshot/cache.** Standard-library counters and current formula are adequate at this scale. Persist a JSON snapshot under ignored `data/bm25/<fingerprint>.json`, atomically replaced, with canonical IDs/tokens/statistics and a manifest. Fingerprint sorted selected document hashes, chunk parameters, tokenizer version, k1/b and implementation version. Rebuild on upload/content/selection/tokenizer/chunk changes; invalidate on delete. At 43 chunks a complete rebuild is simpler than incremental frequency arithmetic. Keep document-frequency statistics scoped to the selected corpus for predictable selection semantics.
3. **Tokenizer.** Start from `rag_app.words.tokens`: retain `KST-2044`, `connector-hub`, Unicode names and apostrophes. Specify channel-marker handling (`#oncall-payments` may normalize its leading `#` consistently), casefold, numbers, punctuation and repeated query terms. Use identical index/query tokens; no stemming/stopword/synonym expansion initially. Treat no lexical match as an empty BM25 result rather than arbitrary zero-score chunks. Test empty corpora/tokens and deterministic tie ordering.
4. **RRF.** Plain unweighted `score(c)=sum(1/(rrf_constant+rank_r(c)))` over enabled lists only. Start with constant 60 as a documented experimental choice, not a PDF requirement. Use separate candidate depth (initially 20 per retriever, capped by available chunks) and final top-k; metrics require at least 10 fused candidates. Stable chunk-ID tie-breaks, one contribution per retriever/chunk, no raw-score normalization. Dense-only can preserve its existing raw rank/score response.
5. **Graph extraction offline, never on first query.** Explicit Kestrel build command reads the same chunks, sends only chunk text/ID with a versioned evidence-only extraction prompt, validates outputs, records raw responses and costs, checkpoints by chunk hash/model/prompt/schema version, then atomically publishes a complete snapshot under ignored `data/graphs/`. No live rebuilding during evaluation. Package a portable graph snapshot/manifest and extraction-grade file in a deliberately versioned, nonignored V3 artifact directory for reproducible grading; do not accidentally commit raw keys or the whole runtime data directory.
6. **Small fixed schema.** Suggested entities: ErrorCode, Service, Team, Channel, Feature, Plan, PolicyVersion and PolicyRule. Suggested directed relations: RAISED_BY, OWNED_BY, CONTACT_CHANNEL, PROVIDES, AVAILABLE_ON, SUPERSEDES, HAS_RULE. Enforce relation endpoint types; expand schema deliberately for corpus facts rather than coercing unsupported concepts. Keep 2025/2026 policy rules separate. Store node IDs/type/label/aliases/source chunk IDs and edge IDs/source/target/type/source chunk IDs/support quotes. Preserve conditional escalation text/properties; do not turn a conditional escalation into an unconditional fact. A source quote's literal presence is a check, not semantic proof of a triple.
7. **Validation/resolution.** Pydantic strict output validation plus node-reference integrity, allowed relation direction, nonempty source IDs, membership in the supplied chunk, and literal support-quote checks. Allow at most one measured repair per invalid chunk, then quarantine and record failure; never silently accept invalid output or hide incomplete coverage. Normalize case/space and exact typed names; use explicit, logged aliases with supporting source. Do not fuzzy-merge codes or collapse historical services/policies. Deduplicate exact edges while unioning provenance; keep all merge/rejection events. Correct/wrong/missed examples in the final report must come from the actual build.
8. **Graph retrieval.** Deterministic longest alias/name/code matching seeds entities from the question; optionally local label-embedding matching only if exact seeds are insufficient, recorded as a separate decision/ablation. Traverse typed edges up to three edges, bounded fan-out/candidate budget and cycle prevention. The assignment calls q08 two-hop, but its operational chain is code -> service -> team -> channel, so a rigid two-edge cutoff would fail. Prefer stronger seed matches/shorter paths using a specified score (e.g. seed similarity divided by 1+path length, summing distinct path contributions); project every traversed edge/node's provenance into ranked chunks, retaining bridge and terminal evidence. Deduplicate paths/chunks deterministically. Use only selected-document provenance; no-seed returns empty with a visible reason. Never use gold answers to seed traversal.
9. **UI.** Three toggles in Ask and Evaluation; same selection sent to API/CLI; reject all-off clearly. Graph is Kestrel-only initially: disable/reject unsupported corpus combinations explicitly. Extend reference cards to display each origin/rank and fused score, and label cosine only for dense-origin results. For graph, render a small accessible node-arrow-edge path (plain DOM/SVG sufficient), detected entities and clickable source chunks for every edge. Show empty-path reasons. Keep answer citations strictly restricted to fused supplied evidence, with trace clearly indicating whether path chunks were supplied or fell below final k.

### Research and alternatives

These primary sources were consulted during the audit; this is design research, not evidence of repository compliance:

- [Microsoft GraphRAG indexing overview](https://microsoft.github.io/graphrag//index/overview/) describes an LLM-derived structured index. Its [local-search documentation](https://github.com/microsoft/graphrag/blob/main/docs/query/local_search.md) combines graph information and original text, with entities as entry points. Adopt the entity-to-source provenance principle; its broader pipeline would add unnecessary moving parts here.
- [LightRAG primary paper](https://arxiv.org/abs/2410.05779) proposes graph indexing and retrieval at detailed and abstract levels. The [official implementation](https://github.com/HKUDS/LightRAG) is another framework option. A custom bounded local traversal is easier to explain and independently measure for this small operational corpus; revisit framework adoption if corpus/requirements expand.

Storage alternatives: in-memory rebuild (fewest moving parts, less portable evidence); JSON snapshot plus adjacency dictionaries (recommended); SQLite node/edge/provenance tables (stronger transactions, more schema work); Neo4j/framework-managed storage (useful at scale, unnecessary dependency/operations here). Query alternatives: entity-seeded traversal (recommended), semantic entity/relation retrieval, LLM query planning (additional calls/non-determinism), global community summaries (poor fit for exact operational chains). These are engineering judgments based on the current corpus and requirements, not measured performance claims.

## Two additional Kestrel two-hop questions (proposals; no dataset edited)

Use new IDs q11/q12 in a separate V3 additions file, with `type=two_hop`, `answerable=true`; materialize the combined set through a V3 loader. Both require linking a service description to its owner and on-call channel; the questions omit the service/team names. Preserve q08 unchanged. Review the questions before freezing them; they are proposed evidence-backed tests, not measured results.

| ID | Question | Expected answer | Gold evidence, one item per link |
|---|---|---|---|
| q11 | Which team's on-call channel should support contact for the service that enforces the 120-second dataset query limit? | Analytics Engine, `#oncall-analytics`; the service is query-engine. | `service-catalog.md:24-27`: `Runs dataset queries, enforces the 120-second query time limit, and caches results for dashboards.` together with `Owner: **Analytics Engine**.`; `service-catalog.md:63`: `\| Analytics Engine \| Léa Fontaine \| #oncall-analytics \| 24/7 rotation \|`. |
| q12 | Which team's on-call channel should support contact for the service that generates invoice PDFs and runs automatic payment retries? | Payments Core, `#oncall-payments`; the service is ledger. | `service-catalog.md:46-49`: `Generates invoice PDFs, runs the automatic payment retries, and applies the grace period and read-only rules of the Billing and Refund Policy.` together with `Owner: **Payments Core**.`; `service-catalog.md:65`: `\| Payments Core \| Jonas Berg \| #oncall-payments \| 24/7 rotation \|`. |

The description/owner evidence is adjacent within each service section; the channel is a separate table entry farther away. Encode each gold quote literally from the source, without Markdown table escaping. For a strict graph-step assessment, retain separate quotes for description and ownership as well as the channel; group them by hop in additional metadata without rewriting q08. Do not assert that all three questions are equally difficult: q11/q12 are within one document, whereas q08 crosses files and includes severity/out-of-hours conditions.

## Risks and controls

| Priority | Risk / exact trigger | Control and acceptance evidence |
|---|---|---|
| High | Fusion of incompatible demo/app chunks corrupts deduplication/provenance (`bm25/...:64-71` vs `service.py:24-32`). | All retrievers use exact canonical IDs/windows; assert source substring and offsets for every result. |
| High | Dense-only regression from changed chunking/model/filtering or collection fingerprint. | Leave dense indexing identity/defaults intact; regression-test original rankings/metrics and selected-document exclusion. New retrieval options live outside chunk settings. |
| High | Index updates/deletes leave lexical/graph evidence stale; current delete only knows Chroma (`service.py:134-146`). | Version manifests, atomic publication, explicit invalidation on source deletion and selected-corpus change; orphan/provenance tests after restart. Old snapshot remains active only if it exactly matches requested sources. |
| High | Bad entity merges or relation direction creates convincing wrong paths; `mailman` predecessor (`service-catalog.md:39`) is not necessarily identical historical entity. | Conservative typed resolution, historical relation rather than automatic identity, provenance and merge log; manually inspect real failure and downstream answer effect. |
| High | Version contamination: two nearly identical billing policies. | Keep version-scoped policy facts separate, preserve both documents in evaluation; test q06/q07 and document current-policy selection. Temporal metadata optional; factual separation essential. |
| High | Adding questions/relabeling types changes denominators, or tuning against answers inflates results. | Append-only V3 extension, original-set and expanded-set tables, frozen hashes, fixed candidate-depth protocol and openly reported development-set tuning. No gold evidence available to retrieval/build prompts. |
| High | Cost/rate limits and non-deterministic graph re-extraction prevent repeatable evaluation. | Offline cached extraction with versioned manifest, bounded retries, per-call usage/time/failure log, fixed graph snapshot for every configuration. Separate build cost from query cost. |
| High | `evaluate()` retrieves to 10 then `ask()` retrieves again (`v2.py:69-81`); cost/ranking evidence may differ, especially above generation k=10. | V3 obtains one frozen candidate ranking to max(metric k, answer k), generates from its exact prefix, and stores that prefix. Count every actual call; preserve V2 evaluator unchanged. |
| Medium | UI crashes when BM25/graph-only references have no `similarity` (`app.js:155`). | Per-origin score display; tests for every nonempty toggle combination, including no dense results. |
| Medium | Graph path exists but only terminal evidence survives RRF. | Save pre/post-fusion ranks, graph-origin survival and hop coverage at each k; measure candidate-depth/constant changes. Do not silently force path chunks into plain RRF. |
| Medium | Long graph builds under current RLock/synchronous API block app; process-local lock is not multi-worker synchronization. | Explicit offline single-writer build, immutable read snapshots; retain documented local single-user deployment. No distributed job infrastructure needed. |
| Medium | Baseline overwritten by legacy command (`evaluation/run.py:41,48`); result files or grades mutated by new tools. | V3 CLI requires fresh output path in a new directory; checksum frozen V1/V2 artifacts; never run legacy default-output evaluator for V3. |
| Medium | Old suite's exact 10-question assertion breaks after in-place additions (`tests/test_v2.py:25`). | Separate additions file/loader; original tests remain unchanged and meaningful. |
| Medium | Installed-package/model availability not proven by dependency files; lock is platform-specific (`README.md:27-38`). | No installation needed for audit. During implementation verify existing environment, pin model revision/artifact checksum and record package versions. No API availability/pricing assumptions. |
| Medium | Citation membership validation mistaken for truth or path causality. | Preserve human answer grading and ten source-based triple reviews; distinguish followed edges, retrieved chunks and actually cited evidence. |
| Low | Historical documentation conflicts (`README.md:109` versus `:123-127`; earlier post-submission audit). | V3 docs describe current state and preserve historical V2 notes, without claiming old review flags are graph grades. |

### Cost and build-time planning (estimates, not measurements)

At 800/80, Kestrel has 43 chunks. One extraction per chunk means **43 initial hosted calls**; at most one repair per chunk caps extraction/repair calls at 86 before any separately budgeted transport retries. At 500/100 it is 76 initial calls, so do not rebuild multiple chunk settings casually. Prompt/schema tokens and output triples may dominate the roughly 34,400 maximum source characters across 43 windows; character counts are not provider token measurements.

If calls are spaced six seconds as in V2, 43 calls consume roughly 4.2-4.3 minutes of pacing alone, plus provider latency (and up to 45 seconds per timeout with the existing answer client). Repairs and quota waits increase this. Actual graph build time must be measured end to end; no precise duration or currency budget is asserted without a pilot/provider usage.

Minimum required retrieval-only evaluation entails 27 dense queries (12 Kestrel + 15 Vellora), 27 dense+BM25 queries and 12 dense+BM25+graph queries: **66 question/configuration executions**. With deterministic local query matching, retrieval needs zero hosted calls. One generated answer per execution adds up to 66 generation calls before errors/retries; no-context reruns are not newly required by V3. Existing V2 no-context evidence is preserved. Extra ablations/generation repeats add cost explicitly.

Log actual model ID, purpose, call count including failures/repairs, input/output/cached tokens when available, elapsed time, status, cache hit and graph ID. Per-question latency should separate local retrieval, fusion, hosted generation and total, plus cold/warm setup. Missing token usage is `unknown`, not zero. Optional money estimates use a dated, verified price schedule; no current prices were fetched or invented. Build cost is reported separately, with optional explicit amortization over N questions, not hidden inside query cost.

## Phased implementation plan and acceptance gates

All changes below are future implementation work; only this audit report is created now.

| Phase | Small deliverable and reusable V2 pieces | Acceptance criteria / meaningful tests |
|---|---|---|
| 0. Freeze contracts/baseline | Record HEAD, hashes, environment/model identity; define retrieval settings/result contract and V3 additions loader. Reuse chunk IDs, settings, source selection and old evaluator. | Original corpus/dataset/result hashes unchanged; V1/V2 suite passes in isolated storage without hosted APIs; dense-only saved metrics reproduce on the original questions. V3 defaults preserve existing clients. |
| 1. Integrated BM25, both corpora | Pure tokenizer/index/search, versioned snapshot/cache and update/delete policy; reuse exact service chunks and Words tokenizer. Add isolated `/bm25` HTML route. | Known-score small BM25 fixture; KST codes/hyphenated services/Unicode queries; empty/OOV/repeated terms/ties; no unselected/deleted document appears; restart/rebuild/invalidation checks. Both corpora return canonical ranked chunks. `/bm25` HTTP 200 displays exact large text; frontend sources have no route/text reference, link or referral. Existing `/about` remains. |
| 2. Plain RRF and toggles (before graph) | Dense/BM25 shared result contract; separate candidate/final depth; toggles in Ask/Evaluation and V3 CLI. Preserve existing generation validation. | Hand-calculated RRF fixture, duplicate suppression, stable ties, one-enabled equivalence and all-off rejection; selected-document isolation; no dense-score UI assumption. Save dense and dense+BM25 runs on both original corpora with per-origin ranks. Do not claim hybrid wins before measuring. |
| 3. V3 measurement foundation | Separate evaluator/output directory, one retrieval snapshot per answer, costs/traces, full grid at 1/3/5/10; reuse quote scoring and grading rules. Freeze/validate q11/q12 additions. | Gold quotes exist verbatim, unique IDs, old 10/15 rows unchanged; 12 Kestrel rows with >=3 two_hop. Synthetic split-hop fixture gives Hit=1/Recall=0.5 and full-hop=0; N/A denominators; errors retained; token-unknown behavior; refusing overwrite. Dense and dense+BM25 original/expanded comparisons agree on shared rows. |
| 4. Graph extraction and snapshot | Fixed typed schema, prompt, explicit offline builder, per-chunk checkpoint, validation/quarantine, conservative resolution/provenance; reuse Pydantic and client configuration pattern. Start with a few Kestrel pilot chunks, then all five files. | Stubbed valid/invalid/hallucinated-ID/direction/unsupported-quote outputs; bounded repair; resume avoids duplicate calls; every node/edge references existing chunks; changed prompt/model/schema/source invalidates cache. Real build has manifest, full coverage or explicit failures, counts/cost/time and actual correct/wrong-or-missed resolution examples. No real calls in unit tests. |
| 5. Ranked graph retrieval and path UI | Seed matching, bounded traversal and chunk projection; connect to RRF and toggles. Reuse citation lookup/cards. | Fixture code->service->team->channel returns bridge/terminal evidence, stable order and edge provenance; cycle/fan-out bounds; no seed/no path/unsupported corpus handled; graph only and all-enabled work. UI shows question entities, followed edges and clickable original chunks; reference origins/ranks match backend exactly and survive deduplication. |
| 6. Required experiments and human review | Required five corpus/configuration cells, full type grid, graph survival analysis and one controlled fusion-depth/constant adjustment if graph evidence is suppressed. Seeded random ten-triple sample and manual source grades. | Results/hashes/configurations stored without overwriting V2; same generation/context settings across combinations; original and expanded slices separate. Ten distinct sampled triples from frozen graph, saved RNG seed/graph hash/source IDs/quotes/reviewer/grade/reason and correct+wrong+unsupported=10. If graph has <10 triples, fix extraction coverage rather than sample duplicates. Document one real degradation from adding a retriever and one bad triple/merge/missed merge with observed consequence. A negative search is reported honestly if no degradation is observed; do not fabricate one to fill the table. |
| 7. Documentation and release readiness | Update README/REPORT and decision log with actual commands, index lifecycle, graph schema/resolution/retrieval/options/failures, cost, defaults and fusion results. | Fresh documented local build/load/eval steps work with frozen graph; final five-cell/type tables and artifacts present; default justified by actual trade-offs, not a required positive delta. Preserve V1/V2 artifacts/tags. Only in a later authorized release step create `v3`; owner handles submission email. No release action in this audit. |

For a three-person team only, add a final measured comparison of weighted RRF versus plain RRF across every question type, or path triples supplied as context versus chunks alone on two-hop questions (PDF page 11). Keep this conditional work out of the core path for the currently recorded sole-developer project.

## Final implementation acceptance checklist

- BM25 works on both corpora through the same app/evaluation paths, with documented tokenizer, storage and update semantics.
- `/bm25` meets exact text/font/absence-of-frontend-reference requirements.
- Graph is genuinely extracted by an LLM from Kestrel chunks offline; schema validation, node/edge provenance, resolution examples, build usage and replayable snapshot are present.
- Every enabled retriever returns ranked canonical chunks; RRF uses only enabled lists; UI and CLI controls agree; citations disclose origins/ranks and graph paths disclose supporting chunks.
- Required configurations, all k/type/denominator reporting, appended two-hop evidence, ten real manual triple grades, query/build costs, graph-fusion survival and adverse cases are documented with actual artifacts.
- V1/V2 remain reproducible and unmodified as evaluation evidence. README/REPORT explain commands and justified defaults; `v3` is a later release requirement, not an audit action.

No V3 performance gain, graph extraction quality, API availability, clean-machine compatibility or new passing test run is claimed by this report.
