# RAG V2 final submission

Deadline: November 3, 2026, 11:59 a.m., Europe/Paris.

## Commits, branch and remote

- Final verified implementation SHA: `c7b4c1deee2629b67e6ffd31edf4fa92e64a23ca`.
- Branch: `main`.
- Origin: `https://github.com/Ferasmich/norag-rag.git`.
- Implementation push: **PASS**, remote main matched that exact SHA after push.
- Final release commit includes this documentation-only follow-up and is identified by annotated tag `v2`. Its exact SHA is `git rev-parse 'v2^{commit}'`; tag-object SHA is `git rev-parse v2`. A committed report cannot embed its own commit hash or the hash of a tag created afterward. The final delivery message supplies the literal verified release SHA, and the commands below reproduce both hashes from GitHub.

## Tests and security

**PASS:** 40 tests passed in 8.32 seconds; real MiniLM/Chroma with mocked hosted generation. JavaScript syntax, dependency consistency, staged diff whitespace, all result JSON/JSONL parsing and staged secret-value/path scans passed. Frozen V1 service, corpus, dataset, baseline and report compare unchanged. No Tasks files, environments, credentials or local database files staged. Kestrel documents and starter questions are byte-identical copies of supplied material.

## Evaluation completeness

**PASS:** both corpora, two configurations, k=1/3/5/10, overall/per-type HitRate and quote recall; real evidence and settings/hashes saved. Vellora Hit@5: 800/80 = 7/12 (58.3%), 500/100 = 8/12 (66.7%). Kestrel: 7/8 (87.5%) versus 6/8 (75.0%). Original V1 baseline preserved and reproduced. No universal improvement claimed.

**PASS:** Kestrel's 10 human reviews verified against downloaded and runtime results: 6 correct, 3 partial, 1 wrong, 0 unsupported; every row has notes, reviewer, timestamp and no-context flag. The original evidence and answers are unchanged. Human no-context matches: 0/10.

**PASS — human verification complete:** all 15 Vellora no-context judgments were initially AI-assisted, then personally verified and confirmed by **Feras M**. q09/q10 are true; the other 13 flags are false. The initial AI-only assessment remains preserved in `evaluation/results/vellora-ai-assessed.json`, including its historical `human_reviewed: false` metadata. `evaluation/results/vellora-reviewed.json` and `evaluation/results/vellora-no-context.jsonl` record Feras M’s subsequent human confirmation, timestamp, rationale and two-stage review history. No original responses, results or provenance were overwritten. This completed no-context verification is distinct from RAG-answer hand grading, fulfilled separately by Kestrel. All questions are retained.

**PASS:** shared CLI/frontend evaluator, optional validated generation/no-context, saved reviews/export, Words corpus/question modes and exact chunk counts/offsets. API tests and actual HTTP workflow passed. Two measured lexical miss diagnoses and failure-stage analysis are in REPORT and the complete implementation report.

## Limitations and submission status

**PARTIAL:** complete browser click-through and responsive visual QA unavailable after browser access timed out; native browser smoke reached tabs/corpus loading/evaluation launch, and HTTP routes passed. Owner report review/personalization remains separate from Vellora no-context human verification, which Feras M completed and recorded for all 15 judgments. Exact identifiers and two-hop evidence still fail in measured cases; citation schema validity is not semantic proof. Earlier hosted errors are preserved; paced final runs completed with no recorded errors. No full Vellora RAG-answer accuracy measurement claimed.

GitHub publication is the authorized submission artifact. Submission email to the professor was **not sent**; the owner remains responsible for that action and any team-policy confirmation. No force push, upstream push or v1 modification is permitted. The original release verified main and v2 at the same commit. The human-confirmation follow-up advances main only; v2 and v1 remain unchanged.

```bash
git rev-parse HEAD v2 'v2^{commit}'
git ls-remote origin refs/heads/main refs/tags/v2 'refs/tags/v2^{}' refs/tags/v1 'refs/tags/v1^{}'
git status --short
```

## Run and reproduce

```bash
source .venv/bin/activate
python -m uvicorn rag_app.api:app --host 127.0.0.1 --port 8000
# http://127.0.0.1:8000 — Evaluation and Words tabs
python -m pytest -q
python -m evaluation.v2 --corpus kestrel --output /tmp/kestrel-fresh.json
python -m evaluation.v2 --corpus vellora --chunk-size 500 --chunk-overlap 100 --output /tmp/vellora-fresh.json
```

Use fresh output paths. Optional `--answers --no-context` requires configured Gemini credentials and sends only the relevant questions/evidence, not expected answers. See README and `RAG_V2_IMPLEMENTATION_REPORT.md` for exact methodology and grading rules.


## Post-release Vellora human confirmation

Feras M completed human verification and explicitly confirmed all 15 proposed no-context judgments in chat after reviewing the question/expected-answer/response summary table: **Yes for q09 and q10, No for the other 13**. The confirmation concerns the no-context flags, not a new Vellora RAG-answer grading experiment. `evaluation/results/vellora-reviewed.json` and `vellora-no-context.jsonl` now record the verifier, confirmation timestamp, rationale and review history. Original AI assessor metadata remains unchanged, including its historical `human_reviewed: false` value at the time of the AI-only assessment; the subsequent `human_verification` event records the later confirmation. `vellora-ai-assessed.json` remains byte-for-byte intact. All 10 Kestrel human reviews are unchanged. The original v2 release snapshot contains the initial AI-only assessments; the subsequent human confirmation is recorded in the follow-up artifacts. Final V2 documentation reflects completed human verification by Feras M.

This is a follow-up on main, not a new release. The existing annotated v2 tag remains object `07ff1e7d3262b4fbbb589eb97921cfa1803d1d20`, pointing to release commit `2a223476c8df74ae6e0464fada5c277f39aaa984`. Main is expected to advance beyond that tag. No evaluation questions, model responses, retrieval metrics or application code changed.

Follow-up validation: 40 tests passed in 8.26 seconds; all 15 confirmations and original AI/Kestrel artifact integrity checked; git diff whitespace check passed.
