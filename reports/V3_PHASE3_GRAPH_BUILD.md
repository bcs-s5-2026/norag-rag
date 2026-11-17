# RAG V3 Phase 3: Kestrel Concept Graph construction

> **Historical scope:** this document records an earlier V3 phase or the first graph. For the current recipe-v2 graph, completed 10-of-39 review, final metrics, existing release tag and latest checks, use [V3_SUBMISSION_AUDIT.md](V3_SUBMISSION_AUDIT.md) and the “V3 final” section of [REPORT.md](../REPORT.md). Earlier pending or incomplete statements below are historical, not the current submission status.

> **Superseded (8 Nov 2026, afternoon).** This file describes the first, partial v1 graph (gemini-3.5-flash-lite, 10 relations). The submitted V3 results, rebuilt graph (`concepts/kestrel_graph_v2/`) and the extraction-quality review (`evaluation/graph_review/kestrel-v2-10-triples.json`) are in REPORT.md, section "V3 final". The v1 grades below were AI-drafted reasons confirmed in chat, not an independent review.


Date: 7 November 2026 (Europe/Paris). Base HEAD remains `8e86a027eb45d528eba5a153fe9804015fda8fa8`; all Phase 1/2/3 changes remain local and uncommitted.

## Status and approval boundary

Pre-extraction verification update (8 November): model metadata access was checked with authenticated GET requests and no generation or corpus transfer. Default sources are now an explicit five-file allowlist and the 43-request ceiling cannot be raised by a CLI flag. See `V3_PHASE3_PRE_EXTRACTION_VERIFICATION.md` and the current `V3_PHASE3_APPROVAL_PLAN.json`; the earlier build ID below is a historical pre-tightening snapshot.

**Construction implementation is complete and tested; actual external extraction is pending explicit user approval.** No real LLM request was made, no Kestrel content was transmitted to a provider, and no production graph snapshot was fabricated. Actual entity/triple counts, extraction quality, successful/wrong real-world merges, hosted build latency and actual hosted token usage are unavailable until an approved run. Mock-based tests exercise the full persistence/build/resume lifecycle in temporary directories.

Final regression suite: **131 passed in 12.58 seconds**, comprising the previous 94 cases and 37 graph-construction cases. All 42 pre-existing files under `evaluation/` and `docs/` (excluding Python caches), including the V3 benchmark artifacts, are byte-unchanged. No original questions, application retrieval behavior, RRF, frontend, Git history or tags were changed. No graph retrieval or three-way fusion was implemented.

Read before implementation: the professor's full local V3 PDF, `V3_READINESS_AUDIT.md`, `V3_PHASE1_BM25.md`, `V3_PHASE2_RRF.md` and `V3_PHASE2_BENCHMARK.md`. The assignment's indexing-time LLM/schema/provenance/resolution/cost requirements are implemented as construction capabilities. Its later graph retrieval, two extra questions and ten graded triples remain separate work; no document instruction was treated as permission to send data or spend.

## Proposed real extraction: review before approval

| Item | Exact proposal |
|---|---|
| Provider | Google Gemini Developer API, via the existing installed OpenAI-compatible SDK. This is Google service/billing, not an OpenAI model or Vertex AI endpoint. |
| Model | `gemini-3.5-flash-lite`; explicit graph configuration, unaffected by `GOOGLE_MODEL`. No automatic model/provider fallback. |
| Endpoint | `https://generativelanguage.googleapis.com/v1beta/openai/` |
| Scope | All five original Kestrel Markdown documents; both billing-policy versions retained. |
| Chunking | Exact V2 windows: 800 characters, overlap 80; 43 canonical chunks. |
| Calls | 43 first-pass requests, one per pending chunk. Default lifetime budget is 43 reserved calls for this build ID; no hidden SDK retries or automatic per-chunk repair calls. |
| Output limit | Requested 4,096 tokens per response; incomplete/truncated output is quarantined. |
| Input estimate | Approximately 48,038 tokens, including the repeated prompt/schema, chunk envelope and estimated framing. |
| Output assumption | 1,024 output tokens per chunk, 44,032 total. Actual extraction/reasoning usage is not known. |
| Standard paid pricing | $0.30 per million input tokens; $2.50 per million output tokens, including thinking tokens. |
| Estimated first pass | $0.1244914 (about $0.12), using the stated output assumption. |
| Output-cap scenario | $0.4547314 (about $0.46), using 176,128 output tokens and the same estimated input count. This is not a guaranteed maximum bill. |
| Actual calls/cost now | Zero real extraction calls. No paid usage incurred by this implementation task. |

Rates and model identity were checked against [Google's official pricing](https://ai.google.dev/gemini-api/docs/pricing) and [model documentation](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite), accessed 7 November 2026. Standard paid rates are used rather than assuming this account qualifies for free usage. Existing keys, model access, quota and a live response were not tested. The [compatibility documentation](https://ai.google.dev/gemini-api/docs/openai) supports reuse of the existing SDK/Google endpoint.

Token estimation is entirely local: `ceil(UTF-8 message-content bytes/4) + 32` framing tokens per request. It does not call an external token-count endpoint and is not a provider tokenizer. The output-cap scenario assumes estimated input and provider enforcement/accounting of the requested output cap; prices, actual input/thinking tokens and billing details can differ. No strict monetary budget is claimed. Unknown pricing for an overridden model is reported as null, not zero.

The saved machine-readable estimate is `reports/V3_PHASE3_DRY_RUN.json`. Its proposed build ID is `cdb696d0e105c8619e3cbc38a2738ff5ecdc5b79c074721f56a3619a3015f527`. A changed model, prompt, schema, implementation, source or alias configuration can change the plan/build identity; review a fresh plan before authorizing different work.

### Content that would leave the machine

Each approved request contains the fixed extraction instructions/JSON schema and one canonical chunk object: exact text, source filename, document content hash, chunk ID, starting line and character offsets. The chunk text includes whatever operational policies, service/team names and on-call channels occur there. Across the full run this covers the complete Kestrel corpus, repeated where windows overlap.

| Source | Decoded characters | Chunks |
|---|---:|---:|
| `docs/kestrel/billing-policy-2025.md` | 4,123 | 6 |
| `docs/kestrel/billing-policy-2026.md` | 5,132 | 8 |
| `docs/kestrel/product-guide.md` | 8,519 | 12 |
| `docs/kestrel/service-catalog.md` | 3,899 | 6 |
| `docs/kestrel/support-runbook-errors.md` | 7,895 | 11 |
| Total | 29,568 | 43 |

Window text totals 32,608 characters including overlap, plus schema/instructions/metadata in every request. Questions, expected answers, annotated evaluation evidence, Vellora, benchmark results and reports are not sent. The `.env` file is not sent as prompt content; an approved adapter uses `GOOGLE_API_KEY` only for authentication to Google. Public documentation was consulted without including corpus text.

**Approval is required by the user's Phase 3 instruction before either paid calls or any corpus transfer, even if an account happens to have a free tier.** The build/resume CLI requires the explicit `--approve-external` flag when pending work would invoke the provider. The adapter independently enforces its approval flag before loading credentials/initializing the SDK. Merely finding an API key cannot enable calls. No such real build command was run during this task.

## Architecture and changed files

| File | Responsibility |
|---|---|
| `rag_app/graph_schema.py` | Fixed entity/relation types, allowed endpoint directions, strict extraction/provider/alias models, label normalization, literal quotation and alias validation. |
| `rag_app/graph_build.py` | Explicit Google adapter, canonical source collection, prompts/cache fingerprints, dry-run estimation, durable journal/budgets, validation/quarantine, entity resolution, graph materialization, atomic persistence and inspection. |
| `rag_app/graph.py` | `plan`, `build`, `resume`, `inspect`; dry-run/cache-only/approval controls; nonzero partial/error exits. |
| `tests/test_graph.py` | 37 mocked construction/validation/storage/recovery/approval/CLI tests. |
| `README.md` | Phase 3 entry points, storage and approval boundary. |
| `reports/V3_PHASE3_DRY_RUN.json` | Local current work/cost estimate; zero calls. |
| `reports/V3_PHASE3_GRAPH_BUILD.md` | This report. |

There are no new dependencies. Pydantic and the Google-compatible OpenAI SDK are already installed project dependencies; the rest uses Python's standard library. Graph modules import the existing `Settings`, `ROOT` and `chunks()` without starting the web app, initializing dense/BM25 storage or generating answers. Original Kestrel files are the offline graph inputs; uploaded-library source mutation is not a graph-build trigger.

## Fixed schema and rationale

A fixed schema makes relations explainable, permits endpoint/direction checks, and limits type drift on the small operational corpus. Open-ended LLM types were rejected for this phase because near-duplicate type names and unbounded relations complicate evaluation/resolution. Unsupported facts must be skipped, not forced into a misleading type. Coverage trade-offs require inspection after an approved build.

Entity types: `ErrorCode`, `Service`, `Team`, `Channel`, `Feature`, `Plan`, `Role`, `Policy`, `Rule`, `Value`. ErrorCode labels must be complete `KST-` plus four-digit identifiers; wildcard area headings are not concrete codes.

| Relation | Subject type(s) | Object type(s) |
|---|---|---|
| `RAISED_BY` | ErrorCode | Service |
| `OWNED_BY` | Service, Policy | Team |
| `CONTACT_CHANNEL` | Team | Channel |
| `ESCALATE_TO` | ErrorCode | Team |
| `PROVIDES` | Service | Feature |
| `AVAILABLE_ON` | Feature | Plan |
| `HAS_RULE` | Policy, Feature, Plan, Role | Rule |
| `HAS_VALUE` | Rule | Value |
| `REQUIRES` | Feature | Feature, Role |
| `REPLACED_BY` | Service | Service |

The extraction response requires `triples` and `aliases` arrays, with at most 60 triples and 20 alias declarations per chunk. Empty arrays are valid and are counted explicitly in coverage metadata. A triple has typed subject/object mentions, a relation, an exact `evidence_quote`, and optional exact `condition_quote`. Fixed types do not establish semantic truth by themselves.

`Policy` and `Rule` entity keys include the source content ID. Thus identical labels in 2025/2026 billing policies remain separate rather than overwriting one another. Other types are Kestrel-scoped and can join across documents when typed names match. No temporal interval inference or policy supersession logic is added. Conditional clauses are preserved as quoted edge qualifiers; there is no silent conversion into unconditional escalation.

## Extraction, validation and provenance

For each canonical chunk, the provider is asked to extract only explicitly supported relations, treat source text as untrusted data, copy names from evidence, preserve conditions and skip unsupported facts. The full Pydantic JSON schema and allowed endpoint pairs are included in the system prompt; compatible JSON-object output mode is requested. The model never receives gold answers or question annotations.

Every response passes local strict Pydantic validation (`extra='forbid'`, strict types), relation endpoint checks and then evidence checks:

1. The supporting quote must be a nonblank exact contiguous substring of that chunk, with no invented paraphrase.
2. Both endpoint labels must occur in the normalized quotation with word boundaries, preventing `auth` from being accepted merely inside `author`.
3. An optional condition must be a nonblank exact substring of the quote.
4. Aliases have the additional equivalence/replacement checks below.
5. Provider finish reason must be `stop`; truncated, blocked or otherwise incomplete output is rejected.

Any failing triple/alias rejects the **whole chunk response**; the valid-looking subset is not quietly accepted. Raw rejected text, usage, source chunk and validation diagnostics are quarantined, with a durable rejection counter. There is no automatic repair call. Provider failures halt further external dispatch in that invocation; valid responses already cached remain reusable. Local credential/SDK preflight failures are logged without reserving a dispatched call.

Entities and relations each link to `provenance_ids`; the referenced provenance records retain canonical source chunk/document IDs, filename, exact quote and source offsets, requested and returned model identifiers, provider, schema/prompt identity, cache key, extraction time and provider response ID when available. Both endpoints inherit their supporting proof records. Deduplicated edges union all supporting proofs rather than losing a source.

The snapshot also contains source chunk text and extraction summaries (model, tokens, response hash, response ID, timing and cache key), so provenance can be inspected locally without re-contacting a model. Raw successful output remains in its validated cache entry. Literal quote/name validation is an integrity check, **not proof that the quote logically entails a relation**; same-type direction mistakes or inferred semantics can still require human rejection.

## Conservative entity resolution

Resolution is deterministic and local:

- Normalize Unicode compatibility forms, case, repeated whitespace, typographic dash variants and curly apostrophes. Preserve digits, accents, word order and substantive punctuation. `KST-2044` and `KST-2040` remain different; no embeddings, edit distance or semantic similarity are used.
- Merge typed names only when normalized label and scope are identical, or a validated explicit alias links them.
- Alias declarations must quote both names and an explicit positive equivalence cue such as “also called” or “also known as”. Co-occurrence alone, negated/distinct-entity language, and historical replacement/predecessor wording are rejected. `mailman` versus `postroom` can be a `REPLACED_BY` relation, never an automatic alias merge.
- Additional manually supplied aliases use `--aliases FILE`: a JSON array of `SourcedAlias` objects with `canonical` (typed mention), `alias`, `evidence_quote` and canonical `chunk_id`. They undergo the same source/equivalence checks; a manual file cannot silently override missing evidence.
- Explicit alias components use a lexicographically stable normalized representative. The declaration's `canonical` field identifies one member of the equivalence pair; it is not a display-name preference override. Entity IDs remain independent of declaration/processing order.
- Store normalized-exact and explicit-alias merge decisions, names, type/scope, reason and supporting proof IDs. Repeated observations accumulate provenance.

Mocked tests demonstrate a formatting merge (`Postroom`/`postroom`), an explicitly supported alias merge (`mail delivery`/`postroom`), rejection of a co-occurrence merge and preservation of predecessor services/policy versions. These are **synthetic test cases, not observed real extraction-quality claims**. Real correct/wrong/missed merge examples and counts remain unavailable until a real build is approved. Conservative rules can miss legitimate abbreviations/parenthetical aliases or “Platform team” versus “Platform”; no weak matching is added to hide that limitation.

## Persistence, deterministic IDs and resume

Physical root: `<RAG_DATA_DIR>/graphs/`, default `<repository>/data/graphs/`; explicit `--data-dir` takes precedence. `data/` is already Git-ignored. No real graph directory was created by the dry run; default inspection currently reports that extraction has not been run.

| Location below graph root | Contents |
|---|---|
| `cache/<key>.json` | Validated raw response, parsed extraction, source chunk, extraction recipe, checksum, provider usage/model/time/response ID. |
| `attempts/<id>.json` | Durable reservation before dispatch, status, chunk/build/run IDs, token usage or unknown markers, timings and failures. |
| `quarantine/<id>.json` | Rejected responses/diagnostics; corrupt cache bytes are preserved before that invalid cache entry is removed. |
| `builds/<build_id>/manifest.json` | Source hashes/chunks, generation settings, model/provider/endpoint, schema/prompt versions/hashes, implementation file hashes, Python/Pydantic versions and manual aliases. |
| `builds/<build_id>/runs/*.json` | Invocation status/timing, approval/cache-only flags, limits, cache hits/rejections, dispatched reservations and pending work. |
| `builds/<build_id>/graph.json` | Entities, relations, provenance, resolution decisions, chunk snapshots, extraction summaries, coverage, usage and explicit complete/partial status. |
| `builds/<build_id>/state.json` | Local checkpoint/index of valid cache keys and remaining work. |
| `latest.json` | Pointer published only after all selected chunks have valid extraction responses. |
| `.build.lock` | Nonblocking OS advisory writer lock, released on process exit/crash. |

Files are written via unique same-directory temporary files, flush/fsync and atomic replacement. A failed write preserves an existing complete file; a killed process can leave an unused `.tmp` file. The implementation targets the project's macOS/Linux environment (`fcntl`); Windows portability is not claimed.

Sources process in sorted filename order, then increasing offset. Canonical IDs exactly match V2: SHA-256 of decoded source plus start/end. Duplicate source content is rejected rather than producing ambiguous identical IDs under different filenames. Entity IDs hash type/scope/normalized representative; relation IDs hash resolved endpoints/type/condition. Provenance IDs derive from source/evidence/extraction identity. Collections and decisions are sorted before persistence.

Validated responses are cached by the actual chunk plus provider/model/generation/prompt/schema recipe. New or changed source documents create a new manifest/build ID; unchanged chunks from other documents reuse their valid extraction cache. Content-hashed canonical IDs mean editing one document invalidates that document's chunk cache. Changed prompts/models/output limits invalidate the relevant extraction recipe. Manual alias-only changes rematerialize the graph from cached extractions without new calls. No incremental graph mutation carries removed-document facts into a new build: each snapshot is assembled only from its current selected source chunks.

Resume trusts revalidated caches and the attempt ledger, not just the last state file. Successful chunk caches are committed immediately, so even an interruption before graph publication does not discard completed extraction. An interrupted request remains an unresolved reserved attempt with unknown usage. It is not silently assumed free or retried beyond the budget. Partial snapshots have `complete=false` and explicit pending reasons; `complete=true` means response coverage, not verified semantic correctness. Empty valid responses are reported as empty extractions, not proof of a useful graph.

## Budgets and usage accounting

Default controls: a hard maximum of 43 lifetime reserved requests per build ID, at most two attempts per chunk across invocations, 4,096 requested output tokens, one request per pending chunk per invocation, SDK retries disabled, 45-second request timeout. A first pass can use all 43 slots. Once those slots are spent, pending repairs remain blocked; raising `--max-calls` above 43 is rejected. Raising `--max-attempts` alone cannot bypass the overall call budget.

A durable reservation precedes each dispatch. The conservative `reserved_llm_calls` count includes ambiguous crash/transport cases, which may have reached the provider. Successful responses record provider prompt/completion tokens; missing usage stays **null**, with separate known-token sums and unknown-call counters. Provider failures, validation rejections, unresolved calls, preflight failures, actual/referenced model IDs, per-call latency and completed-run latency are recorded. A build reusing prior cache can make zero new calls while still referencing earlier extraction summaries; those earlier calls are not relabeled as newly incurred cost.

Known-usage monetary estimates use the recorded standard rates; missing usage makes `cost_complete=false`. This is not an invoice reconciliation. Build/run timing covers the measured construction body, including extraction/validation/resolution; upfront CLI/planning and final metadata-publication overhead are not separately instrumented. Actual hosted build time is currently unavailable; mock-test timing is not presented as hosted performance.

## CLI operations

Use the existing virtual environment; system Python may lack this project's dependencies. No installation was needed for this task.

```bash
# Read-only work/cost plan. Does not load keys or contact a provider.
.venv/bin/python -m rag_app.graph plan
.venv/bin/python -m rag_app.graph build --dry-run

# Save a fresh local estimate (refuses an existing output filename).
.venv/bin/python -m rag_app.graph build --dry-run \
  --estimate-output reports/V3_PHASE3_DRY_RUN_NEW.json

# Local-only assembly/inspection; partial cache-only completion returns exit 2.
.venv/bin/python -m rag_app.graph resume --cache-only
.venv/bin/python -m rag_app.graph inspect
.venv/bin/python -m rag_app.graph inspect --full
.venv/bin/python -m rag_app.graph inspect --build-id BUILD_SHA256 --full
```

**The following commands are proposals only and were not executed. They require the user's explicit approval of the above provider/model, data transfer and budget first:**

```bash
.venv/bin/python -m rag_app.graph build \
  --model gemini-3.5-flash-lite --max-output-tokens 4096 \
  --max-calls 43 --max-attempts 2 --approve-external

# After reviewing a new plan: reuses valid responses and only schedules pending chunks.
.venv/bin/python -m rag_app.graph resume \
  --model gemini-3.5-flash-lite --max-calls 43 --max-attempts 2 --approve-external
```

When the lifetime budget is spent, resume records remaining chunks as budget-blocked and makes no additional requests. The 43-request ceiling cannot be raised by a CLI flag. `build` and `resume` use the same resumable engine. Partial completion returns exit code 2; complete coverage returns 0. Inspection without a built snapshot fails explicitly instead of presenting a placeholder graph. Changing sources/configuration derives a different build ID and requires a fresh approval; `--build-id` allows inspection of an older stored snapshot.

## Tests and preservation

Final command:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/python -m pytest -q
```

**131 passed in 12.58 seconds.** All 37 graph cases use mocked responses or no-call paths. The provider-adapter test replaces the SDK client factory; the approved-preflight-failure test uses an empty mocked credential environment and makes no request. Existing dense tests use cached local embeddings, and generation remains mocked in the old suite.

Graph coverage includes strict whole-response rejection, endpoint directions and identifier validation, quote/word-boundary/condition checks, alias equivalence/replacement rules, exact source IDs, zero-call dry runs, API-key-independent approval gating, stable graph IDs, source/version isolation, full entity/edge provenance, cache-only replay, incremental source rebuilds, model/prompt invalidation, quarantine, output truncation, provider halt/resume, unknown usage, durable call limits, interrupted-request accounting, writer locking, atomic-write failure, inspection checksums and CLI controls.

The final full suite includes all four V2 dense-baseline comparisons. Byte SHA-256 checks confirmed all **42** pre-existing corpus/evaluation files unchanged, including all raw/derived Phase 2.5 benchmark artifacts. `git diff --check`, JavaScript syntax and dependency consistency checks passed. No dependencies were installed; no commit, push or tag was created.

## Remaining evidence and stop point

The engine/schema/storage/CLI/dry-run/mock-test deliverables are ready. A real persistent Kestrel graph, real model usage/build latency, real merge examples and ten manually graded triples are **not yet available** because external extraction has not been approved. No test fixtures were passed off as the course graph.

After approval, run only the bounded construction above, inspect coverage and quarantines, and report actual counts/usage before deciding whether any extra calls are warranted. Semantic quotation support, omitted conditional qualifiers, fixed-schema coverage, aliases and versioned facts still need human inspection. Graph retrieval and graph fusion remain explicitly out of scope.

The requested approval now is for **at most 43 requests** to Google Gemini Developer API `gemini-3.5-flash-lite`, sending the 43 chunks/metadata/schema described above, with a 4,096-token output limit and the stated cost estimates. This request comes from the user's explicit Phase 3 safety/cost instructions. Work stops here pending that approval; no external extraction or next-phase implementation is started automatically.


## Final follow-up — 8 November 2026

The user subsequently approved extraction. All 43 approved attempts are complete and the lifetime budget is exhausted. The published partial graph contains 17 entities / 10 relations, including nine transparently documented offline quotation-context repairs. Feras M graded the ten retained triples: 10 correct, 0 wrong, 0 unsupported. See [final integration](V3_FINAL_INTEGRATION.md) and [final verification](V3_FINAL_VERIFICATION.md) for actual usage, failures, metrics and limitations. Earlier pending-approval statements describe the historical pre-extraction state. No further real API calls are authorized by this follow-up.
