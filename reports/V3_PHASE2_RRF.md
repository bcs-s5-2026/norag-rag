# RAG V3 Phase 2: dense + BM25 reciprocal rank fusion

Date: 7 November 2026 (Europe/Paris). Base commit remains `8e86a027eb45d528eba5a153fe9804015fda8fa8`; Phase 1 and Phase 2 changes are local/uncommitted.

## Outcome and scope

Phase 2 adds configurable plain RRF over dense, BM25, or both, with stable-ID deduplication, deterministic ties and per-chunk retrieval provenance. It is available through a new service method, a retrieval-only HTTP endpoint and a new evaluation CLI. Existing dense/BM25 implementations, V2 evaluator, API defaults, frontend, questions and frozen results are preserved.

Before implementation, read the professor's full local V3 PDF, `reports/V3_READINESS_AUDIT.md`, `reports/V3_PHASE1_BM25.md`, existing models/service/API/evaluator, and tests. The PDF requires RRF over enabled retrievers (pages 4/8) and evaluation-command selection (page 8). The remaining graph/UI requirements are outside this Phase 2 request and are not claimed complete.

**Final tests: 94 passed in 14.13 seconds. All four V2 baselines reproduced through both the original evaluator and the new dense-only evaluation path.** Six real CLI runs also succeeded, covering both corpora in every supported retrieval mode. All new runs were retrieval-only; no paid or other hosted LLM calls occurred.

## Architecture and changed files

Phase 2 extends the existing Python/FastAPI/Pydantic architecture without dependencies. Phase 1 files remain in the working tree and are not mistaken for new Phase 2 changes.

| File | Phase 2 change |
|---|---|
| `rag_app/fusion.py:7-38` (new) | Pure `reciprocal_rank_fusion()`; deduplication, source-integrity checks, standard scoring and deterministic ordering. |
| `rag_app/models.py:51-74` | Strict `RetrievalConfig` and `RetrievalQuestion`; retriever list, rank constant, candidate-depth validation; final top-k stays in existing `Settings`. |
| `rag_app/service.py:196-243` | Opt-in `_dense_candidates()` and `retrieve_configured()` orchestration. Reuses the dense `retrieve()` and BM25 `_bm25()`/`BM25Index.search()` components under the existing lock. |
| `rag_app/api.py` | New `POST /api/retrieve`, using the configurable service path. Existing search/ask/BM25 endpoints are unchanged. |
| `evaluation/v3.py` (new) | Retrieval-only evaluator and CLI using V2 datasets, corpus loaders and metric functions; fresh output, provenance/statuses, hashes, final selected prefix and retrieval timing. |
| `tests/test_rrf.py` (new) | 32 cases including parametrized cases; scoring, configuration, failures, integration, CLI guards and all four V2 baseline comparisons. |
| `README.md` | Current Phase 2 operations, API/CLI examples and behavior. Phase 1 implementation report remains unchanged as a historical record. |
| `reports/V3_PHASE2_RRF.md` | This implementation/verification report. |

Unchanged independent retrieval entry points:

- `RagService.retrieve(question, ids, settings)` remains the V2 dense implementation and response format.
- `RagService.retrieve_bm25(question, ids, settings)` remains the Phase 1 lexical implementation and response format.
- `RagService.retrieve_configured(...)` is opt-in. It does not replace either component or change their index identity. `Settings`, `collection_name()`, dense indexing, `ask()`, and generation behavior are unchanged.
- Existing `/api/search`, `/api/ask`, `/api/index`, `/api/bm25/index`, `/api/bm25/search` and `evaluation.v2` continue on their previous paths. The static frontend is unchanged and still uses dense retrieval.

## RRF details

For a chunk d, `RRF(d) = sum(1 / (rrf_k + rank_i(d)))`, using only enabled retrievers. Ranks are 1-based. Default `rrf_k=60`; configurable integer range is 0-1,000,000. Zero is safe because ranks begin at one. There are no weights, raw-score normalization, reranking models or graph contributions.

Processing rules:

1. Each enabled retriever produces its independent candidate list using the same selected documents and canonical chunk settings.
2. Each list is deduplicated by stable canonical chunk ID. First occurrence wins; unique entries receive contiguous 1-based ranks. One retriever contributes at most once per ID. Duplicated input cannot inflate its vote.
3. The same ID must have the same source fields across lists; conflicting text/name/document/offset/line information is rejected as an integrity error, not arbitrarily selected.
4. Contributions are summed with `math.fsum` in stable retriever order. Raw dense similarity and BM25 scores are retained only for provenance; they do not enter the formula.
5. Sort by descending RRF score, then ascending full canonical chunk ID. Assign `fused_rank` and select the final top-k.

Single-retriever mode applies the same formula to that one list; scores become reciprocal ranks and list order is preserved. This makes provenance uniform without pretending a BM25 score is a cosine score.

### Deterministic dense candidates

Sorting only the returned dense top-N cannot resolve an equal-score tie where some tied chunks were excluded at the cutoff. The new path therefore queries all chunks in the selected corpus through the original dense retriever, sorts by descending similarity and ascending ID, then keeps `candidate_depth`. This preserves the retrieval component and handles boundary ties consistently. The old dense endpoint/evaluator keeps its existing query behavior.

At current corpus sizes (43 chunks at 800/80), the cost is small. It is deliberately not a scalable high-volume ANN strategy. Floating-point/model/package changes can still affect rankings across environments; no cross-platform/model-revision bitwise guarantee is claimed.

### Result and status contract

Each `results` entry carries canonical source fields plus:

```json
{
  "id": "DOCUMENT_SHA256:START:END",
  "origins": {
    "dense": {"rank": 2, "raw_score": 0.8},
    "bm25": {"rank": 1, "raw_score": 7.0}
  },
  "fused_rank": 1,
  "rrf_score": 0.03252247488101534
}
```

This is an illustrative score (`1/62 + 1/61`), not a measured corpus row. Only retrievers that found the chunk within their candidate list appear in `origins`; absence means no contribution at the configured depth. The service response also contains configuration, final `top_k`, and per-enabled-retriever `status`/`candidate_count`. BM25 status includes its snapshot fingerprint and `index_rebuilt`.

RRF scores are not confidence values. Canonical text and metadata are supplied by the retrievers, never by an LLM. This phase returns retrieval provenance; rendering it in answer citation cards is future UI/answer-integration work.

## Configuration and commands

| Setting | Default / validation |
|---|---|
| `retrievers` / `--retrievers` | `dense`; select `dense`, `bm25`, or `dense bm25`. Empty, duplicate and unknown entries are rejected. Input order is normalized. |
| `candidate_depth` / `--candidate-depth` | 20 candidates per enabled list; integer 1-10,000. Must be >= final top-k; evaluation additionally requires >=max(10, final top-k). |
| `rrf_k` / `--rrf-k` | 60; independent of final top-k. |
| `settings.top_k` / `--top-k` | Existing final-k convention, default 5 and range 1-20. |
| Chunk size/overlap | Existing 800/80 defaults and validation, unchanged. |

Examples (choose new output filenames; no command calls an LLM):

```bash
python -m evaluation.v3 --corpus kestrel --retrievers dense \
  --output evaluation/results/v3/kestrel-dense.json

python -m evaluation.v3 --corpus vellora --retrievers bm25 \
  --output evaluation/results/v3/vellora-bm25.json

python -m evaluation.v3 --corpus kestrel --retrievers dense bm25 \
  --candidate-depth 20 --rrf-k 60 --top-k 5 \
  --output evaluation/results/v3/kestrel-rrf.json

# An explicitly separate sensitivity run, not an assumed improvement:
python -m evaluation.v3 --corpus vellora --retrievers dense bm25 \
  --chunk-size 500 --chunk-overlap 100 --candidate-depth 30 --rrf-k 30 --top-k 10 \
  --output evaluation/results/v3/vellora-rrf-500-100-depth30-k30.json
```

Add `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1` to use an already-cached embedding model without downloads, as in verification. BM25-only needs no embedding model/Chroma initialization. Dense needs the existing cached/downloadable model and writable local storage.

Service example:

```python
from rag_app.models import RetrievalConfig, Settings

response = service.retrieve_configured(
    question, document_ids, Settings(top_k=5),
    RetrievalConfig(retrievers=['dense', 'bm25'], candidate_depth=20, rrf_k=60))
```

HTTP: `POST /api/retrieve` with:

```json
{
  "document_ids": ["UPLOADED_DOCUMENT_ID"],
  "question": "What does KST-2044 mean?",
  "settings": {"chunk_size": 800, "chunk_overlap": 80, "top_k": 5},
  "retrieval": {"retrievers": ["dense", "bm25"], "candidate_depth": 20, "rrf_k": 60}
}
```

Load source IDs through the existing corpus/upload endpoints. Include all five Kestrel IDs for the full corpus. A successful API request returns the configured final top-k directly.

### Evaluation depth versus final selection

Following V2 conventions, metrics always score prefixes 1,3,5,10, even if final top-k is 5. The V3 evaluator obtains **one** fused ranking of depth `max(10, final_top_k)` per question. It stores that ranking as `retrieved` and its final top-k prefix as `selected`. Candidate lists are still truncated independently before fusion. This prevents a second retrieval from producing different evidence for selection versus metrics.

The evaluator reuses original literal `(source, quote)` hits, macro quote recall, type labels and unanswerable exclusions. No old question is relabeled or edited. It records corpus/dataset hashes, settings/configuration, per-retriever status, timing, and `llm_calls=0`. Timing includes any on-demand indexing in that request, so first-question cold latency should not be treated as warmed query latency.

The CLI uses an isolated temporary data directory, as V2 does. This avoids contamination from normal library uploads, but it rebuilds temporary indexes for each run. Normal app/service BM25 usage still persists at `data/bm25/` or `$RAG_DATA_DIR/bm25/` and reuses snapshots after restart. Existing output files are refused before running; exclusive file creation also prevents overwriting a concurrently created output.

## Empty results, index recovery and failures

| Condition | Explicit behavior |
|---|---|
| Enabled retriever finds no candidates | Status `empty`, count 0, no contribution. If every enabled list is empty, `results=[]`. This is a successful empty result, not an index failure. |
| Missing/corrupt BM25 snapshot | Phase 1's deterministic on-demand rebuild; response records `index_rebuilt=true`. A valid snapshot load records false. Recovery remains within BM25, not a switch to dense. |
| BM25 storage/build failure | `PipelineError`, identifying `bm25`; whole retrieval request fails. No partial dense-only answer/result is returned. |
| Dense embedding/vector/index failure | `PipelineError`, identifying `dense`; whole request fails. BM25 is not substituted. |
| Missing selected source | Error status 404 is preserved with the failing retriever identified. |
| Conflicting source fields for one ID | Fusion integrity error (HTTP 502), no arbitrary metadata merge. |
| Invalid/all-off/duplicate configuration | Pydantic/API validation error; CLI nonzero exit before evaluation. |
| Retrieval failure during CLI evaluation | Run aborts with nonzero exit and no result file, rather than counting an infrastructure failure as a retrieval miss or producing mixed-configuration metrics. |

The BM25 status currently reports whether recovery rebuilt the snapshot, not a separate missing-versus-corrupt reason. Detailed storage exceptions are not exposed through retrieval errors. Single-process locking covers source/index operations as before; no cross-process mutation support was added.

## Actual verification

Executed with existing dependencies and offline embedding flags:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/python -m pytest -q tests/test_rrf.py
# 32 passed in 9.52s

HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/python -m pytest -q
# 94 passed in 14.13s
```

The 94 cases comprise 40 original V1/V2 cases, 22 Phase 1 BM25 cases and 32 Phase 2 cases. New coverage includes numeric RRF values, constant changes including zero, duplicate IDs, conflicting source data, raw-score independence, mapping-order/tie determinism, empty results, invalid settings, enabled-component dispatch, candidate depth, single modes, two-retriever fusion, no fallback after either failure, missing/corrupt BM25 recovery, storage failure, API provenance/errors/legacy response, corpus isolation, independent component order, retrieval-only evaluation, output guards and baseline reproduction.

Additional actual checks:

- Six subprocess invocations of `python -m evaluation.v3`, for Kestrel/Vellora × dense/BM25/dense+BM25, at 800/80, depth 20, rank constant 60, final k=5: all successful; saved JSON configurations and zero LLM calls checked. Output files/indexes were in temporary directories and removed afterwards. The measured tables below are preserved here; CLI commands reproduce full per-question/type artifacts at fresh paths.
- A focused Kestrel dense-versus-RRF run inspected q01/q05 origin and fused ranks, described below.
- SHA-256 comparison confirms every pre-existing file under `evaluation/` and `docs/` is byte-unchanged (excluding Python caches). Only new evaluator source `evaluation/v3.py` was added there. Existing V1/V2 tests are unchanged.
- `git diff --check`: passed. `node --check rag_app/static/app.js`: passed. `.venv/bin/pip check`: no broken requirements. No dependencies installed.
- No hosted-generation calls, live browser interaction, clean-machine installation, commit, push or tag operation. Existing untracked Phase 1/readiness/post-submission reports are preserved.

### Four V2 baseline comparisons

The parametrized regression test runs both `evaluation.v2.evaluate()` and `evaluation.v3.evaluate(..., retrievers=['dense'])` against each frozen result. It compares **all** overall/per-type/per-question hit and quote-recall values and corpus/dataset hashes, not just the summary below.

| Frozen file under `evaluation/results/` | Hit@1 | Hit@3 | Hit@5 | Hit@10 | Quote Recall@10 | Legacy V2 / new dense-only |
|---|---:|---:|---:|---:|---:|---|
| `kestrel-800-80.json` | 5/8 | 7/8 | 7/8 | 8/8 | 93.75% | Exact metric match / exact metric match |
| `kestrel-500-100.json` | 2/8 | 6/8 | 6/8 | 8/8 | 90.625% | Exact metric match / exact metric match |
| `vellora-800-80.json` | 6/12 | 6/12 | 7/12 | 10/12 | 83.333% | Exact metric match / exact metric match |
| `vellora-500-100.json` | 2/12 | 6/12 | 8/12 | 10/12 | 83.333% | Exact metric match / exact metric match |

An exact metric match is not byte-identical run JSON: new timestamps, timing, schema and provenance fields intentionally differ. The frozen artifacts themselves are unchanged.

### Phase 2 CLI measurements

These measurements use unchanged V2 questions and 800/80 chunks. Hit denominators exclude 2 Kestrel and 3 Vellora unanswerable questions. Recall is V2's macro literal-evidence recall, not answer accuracy.

| Corpus | Retrievers | Hit@1 | Hit@3 | Hit@5 | Hit@10 | Recall@5 | Recall@10 |
|---|---|---:|---:|---:|---:|---:|---:|
| Kestrel | dense | 5/8 | 7/8 | 7/8 | 8/8 | 81.25% | 93.75% |
| Kestrel | BM25 | 3/8 | 6/8 | 6/8 | 7/8 | 53.125% | 71.875% |
| Kestrel | dense+BM25 | 4/8 | 6/8 | 7/8 | 8/8 | 71.875% | 93.75% |
| Vellora | dense | 6/12 | 6/12 | 7/12 | 10/12 | 58.333% | 83.333% |
| Vellora | BM25 | 8/12 | 11/12 | 11/12 | 11/12 | 91.667% | 91.667% |
| Vellora | dense+BM25 | 7/12 | 9/12 | 11/12 | 11/12 | 91.667% | 91.667% |

Selected per-type detail at k=5, format HitRate / Recall (all at depth 20, constant 60):

| Corpus / type | Answerable n | Dense | BM25 | Dense+BM25 |
|---|---:|---|---|---|
| Kestrel exact_identifier | 2 | 50% / 50% | 50% / 25% | 100% / 100% |
| Kestrel split_answer | 2 | 100% / 100% | 100% / 62.5% | 100% / 62.5% |
| Kestrel vocabulary | 1 | 100% / 100% | 0% / 0% | 0% / 0% |
| Kestrel versions | 2 | 100% / 100% | 100% / 100% | 100% / 100% |
| Kestrel two_hop | 1 | 100% / 50% | 100% / 50% | 100% / 50% |
| Vellora exact_identifier | 4 | 50% / 50% | 100% / 100% | 100% / 100% |
| Vellora vocabulary | 4 | 50% / 50% | 100% / 100% | 100% / 100% |
| Vellora other (original label) | 4 | 75% / 75% | 75% / 75% | 75% / 75% |

`not_in_corpus` has no answerable gold evidence: retrieval HitRate/Recall are N/A, not zero accuracy. Vellora types absent from the original dataset are not fabricated or silently relabeled.

### One improvement and one regression

Kestrel q01 asks about KST-2044. Its gold chunk ranks 7 in dense and 7 in BM25; agreement moves it to fused rank 5, changing Hit@5 from false to true. It contains both required gold quotes.

Kestrel q05 asks about losing a phone and being unable to log in. The chunk containing the backup-code/second-factor-reset quotes ranks 1 in dense, receives no BM25 contribution within depth 20, and falls to fused rank 8. Hit@5 changes from true to false. This is an observed adverse effect of adding a retriever: multiple chunks with two-list agreement outrank a strong semantic-only candidate. The mismatch between the question's wording and the corpus's authenticator/second-factor terminology explains why lexical agreement is unhelpful here; the saved origin ranks directly establish the fusion mechanism.

Consequently Kestrel Hit@5 stays 7/8 overall while evidence recall decreases. Hybrid is not universally better. No default endpoint/UI was changed to hybrid, and no candidate-depth/constant tuning was performed to conceal the regression.

## Limitations and recommended next steps

- **UI and answers:** retriever controls and citation-origin rendering are not added in this phase; use the new API/CLI. Existing answer generation remains dense-only. A later integration should feed the exact selected fused snapshot to generation and preserve origins through citation lookup, with no hidden re-query.
- **Graph:** extraction, graph retrieval, path visualization, two new questions and ten triple grades remain unimplemented. No graph code or question changes were made here.
- **Scale:** deterministic dense tie membership queries the entire selected corpus. This is appropriate for current course data, not a large ANN deployment. For larger collections, design a bounded, tested deterministic candidate strategy before changing the current behavior.
- **Persistence/recovery:** Phase 1 BM25 storage/rebuilding rules are unchanged. The benchmark intentionally uses fresh temporary indexes; app persistence does not imply that separate benchmark runs share an index cache.
- **Evaluation:** no answer-quality/abstention grading or hosted cost experiment is performed. Local timing includes cold setup. Question sets are small, q08 still has only half its gold evidence in top 10, and no generalization claim follows from these tables.
- **Reproducibility:** model/Chroma/package revisions and floating-point implementations can affect rankings. Existing frozen baseline hashes are retained; a future release should record a fully pinned environment/model artifact identity.
- **Failure policy:** fail-fast evaluation produces no partial result file. This prevents infrastructure failures from contaminating metric denominators; resumable failure artifacts would be a separate operational enhancement.
- **Recommended next work after review:** integrate UI/answer provenance, then implement the Concept Graph according to the audit. Any RRF sensitivity study should keep questions/corpus/chunk settings fixed, record depth/constant, report all type deltas and adverse examples, and remain separate from plain default-RRF results. Weighted RRF is not implemented.

Phase 2 is complete and stops here for review. No Phase 3 work or release action was started.
