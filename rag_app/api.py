import logging

from fastapi import FastAPI, File, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from .models import Settings, Question, Selection, WordsRequest, EvaluationRequest, GradeRequest, RetrievalQuestion, V3EvaluationRequest
from .service import MAX_BYTES, ROOT, PipelineError, RagService


def create_app(service=None):
    app = FastAPI(title='Evidence / RAG final release')
    app.state.rag = service or RagService()

    @app.exception_handler(PipelineError)
    async def pipeline_error(request, exc):
        content = {'error': str(exc)}
        if hasattr(exc, 'trace_id'):
            content['trace_id'] = exc.trace_id  # the UI can open the trace of a failed request
        return JSONResponse(status_code=exc.status, content=content)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, exc):
        return JSONResponse(status_code=422, content={'error': 'Invalid input. Select documents, enter a question and check retrieval settings.'})

    @app.exception_handler(Exception)
    async def unexpected(request, exc):
        logging.getLogger(__name__).exception('Unhandled request error')
        return JSONResponse(status_code=500, content={'error': 'Operation failed. Check server logs and retry.'})

    @app.get('/api/documents')
    def documents():
        with app.state.rag.lock:
            return app.state.rag.list_documents()

    @app.post('/api/documents')
    def upload(file: UploadFile = File(...)):
        result = app.state.rag.upload(file.filename or '', file.file.read(MAX_BYTES + 1))
        # The concept graph is built right after the upload (one model call per passage, size-capped).
        # A failure never fails the upload: the answer says what happened.
        result['graph'] = app.state.rag.auto_graph(result['id'])
        return result

    @app.get('/api/graphs')
    def graphs():
        rag = app.state.rag
        with rag.lock:
            return {d['id']: rag.graph_status(d['id']) | {'name': d['name']} for d in rag.list_documents()
                    if rag.graph_files(d['id'])}

    @app.post('/api/documents/{doc_id}/graph')
    def build_graph(doc_id: str, settings: Settings | None = None):
        return app.state.rag.build_graph(doc_id, settings)

    @app.delete('/api/documents/{doc_id}')
    def delete(doc_id: str):
        app.state.rag.delete(doc_id)
        return {'deleted': doc_id}

    @app.post('/api/index')
    def index(body: Selection):
        return app.state.rag.index_run(body.document_ids, body.settings)

    @app.post('/api/ask')
    def ask(body: RetrievalQuestion):
        if 'retrieval' not in body.model_fields_set:
            return app.state.rag.ask(body.question, body.document_ids, body.settings)
        return app.state.rag.ask_configured(body.question, body.document_ids, body.settings, body.retrieval)

    @app.get('/api/traces')
    def traces(kind: str | None = None, limit: int = 20):
        return app.state.rag.traces.recent(max(1, min(limit, 100)), kind)

    @app.get('/api/traces/{trace_id}')
    def trace(trace_id: str):
        found = app.state.rag.traces.get(trace_id)
        if found is None:
            raise PipelineError('Trace not found. Traces are kept for 30 days.', 404)
        return found

    @app.get('/api/metrics')
    def metrics():
        from .metrics import summarize
        return summarize(app.state.rag.traces.all())

    @app.get('/metrics', response_class=HTMLResponse, include_in_schema=False)
    def metrics_page():
        return (ROOT / 'rag_app' / 'static' / 'index.html').read_text(encoding='utf-8')  # opens on the Metrics tab

    @app.get('/api/concepts')
    def concepts(documents: str | None = None):
        return app.state.rag.concepts(documents.split(',') if documents else None)

    @app.get('/api/concepts/{concept_id}')
    def concept(concept_id: str, documents: str | None = None):
        return app.state.rag.concept(concept_id, documents.split(',') if documents else None)

    @app.get('/api/evaluation')
    def evaluation():
        import json
        path = ROOT / 'evaluation' / 'baseline.json'
        return json.loads(path.read_text()) if path.exists() else {'status': 'Run python -m evaluation.run first.'}

    @app.post('/api/search')
    def search(body: Question):
        return app.state.rag.retrieve(body.question, body.document_ids, body.settings)

    @app.post('/api/words')
    def words(body: WordsRequest):
        from .words import analyze
        return analyze(app.state.rag, body.document_ids, body.settings, body.question, body.word)

    @app.post('/api/retrieve')
    def retrieve_configured(body: RetrievalQuestion):
        return app.state.rag.retrieve_configured(body.question, body.document_ids,
                                                body.settings, body.retrieval)

    @app.post('/api/bm25/index')
    def index_bm25(body: Selection, rebuild: bool = False):
        return app.state.rag.index_bm25(body.document_ids, body.settings, rebuild)

    @app.post('/api/bm25/search')
    def search_bm25(body: Question):
        return app.state.rag.retrieve_bm25(body.question, body.document_ids, body.settings)

    @app.get('/api/question-sets')
    def question_sets():
        from evaluation.v2 import questions
        return {name: questions(name) for name in ('kestrel', 'vellora')}

    @app.post('/api/evaluations/v3')
    def evaluate_v3(body: V3EvaluationRequest):
        from evaluation.v3 import run
        from evaluation.v2 import save
        result = run(body.corpus, body.settings, body.retrieval, body.question_set, app.state.rag.graph_path)
        run_id = save(result, app.state.rag.root/'evaluations')
        return dict(run_id=run_id, result=result)

    @app.post('/api/corpora/{corpus}')
    def load_corpus(corpus: str):
        from evaluation.v2 import corpus_dir, questions
        questions(corpus)  # Validate before resolving paths.
        files = sorted(corpus_dir(corpus).glob('*.md')) if corpus == 'kestrel' else [ROOT/'docs'/'vellora-duo-espresso-machine.txt']
        return [app.state.rag.upload(p.name, p.read_bytes()) for p in files]

    def measured_files():
        import json
        root = ROOT/'evaluation/results'
        allowed = {}
        for p in root.rglob('*.json'):
            if not p.resolve().is_relative_to(root.resolve()): continue
            try:
                data = json.loads(p.read_text())
                if isinstance(data, dict) and isinstance(data.get('results'), list) and data.get('corpus') in ('kestrel', 'vellora'):
                    allowed[p.relative_to(root).as_posix()] = p
            except (OSError, ValueError):
                continue
        return allowed

    @app.get('/api/measured-runs')
    def measured_runs():
        return sorted(measured_files())

    @app.post('/api/measured-runs/{filename:path}')
    def open_measured_run(filename: str):
        import json
        from evaluation.v2 import save
        allowed = measured_files()
        if filename not in allowed:
            raise PipelineError('Measured run not found.', 404)
        result = json.loads(allowed[filename].read_text())
        run_id = save(result, app.state.rag.root/'evaluations')
        return dict(run_id=run_id, result=result)

    @app.post('/api/evaluations')
    def evaluate(body: EvaluationRequest):
        from evaluation.v2 import run, save
        result = run(body.corpus, body.settings, body.answers, body.no_context)
        run_id = save(result, app.state.rag.root/'evaluations')
        return dict(run_id=run_id, result=result)

    def result_path(run_id):
        import re
        if not re.fullmatch(r'[0-9a-f]{32}', run_id):
            raise PipelineError('Evaluation not found.', 404)
        path = app.state.rag.root/'evaluations'/f'{run_id}.json'
        if not path.exists():
            raise PipelineError('Evaluation not found.', 404)
        return path

    @app.get('/api/evaluations/{run_id}')
    def saved_evaluation(run_id: str):
        import json
        with app.state.rag.lock:
            return json.loads(result_path(run_id).read_text())

    @app.post('/api/evaluations/{run_id}/grades')
    def grade(run_id: str, body: GradeRequest):
        import json
        from datetime import datetime, timezone
        with app.state.rag.lock:
            path = result_path(run_id)
            result = json.loads(path.read_text())
            row = next((r for r in result['results'] if r['id'] == body.question_id), None)
            if row is None:
                raise PipelineError('Question not found.', 404)
            if body.grade is not None and 'response' not in row:
                raise PipelineError('Generate an answer before grading it.', 400)
            if body.no_context_correct is not None and 'no_context_answer' not in row:
                raise PipelineError('Run a no-context check before reviewing it.', 400)
            row.update(grade=body.grade, grade_notes=body.notes, reviewer=body.reviewer,
                       no_context_correct=body.no_context_correct, graded_at=datetime.now(timezone.utc).isoformat())
            temporary = path.with_suffix('.tmp')
            temporary.write_text(json.dumps(result, indent=2)+'\n')
            temporary.replace(path)
        return {'saved': True}

    @app.get('/about', response_class=HTMLResponse)
    def about():
        return '<!doctype html><html lang="en"><meta charset="utf-8"><title>About</title><p style="font-size:2rem">Denis Amselemovitch is an intriguing character who likes to make impromptu appearances in incongruous places.</p></html>'

    @app.get('/bm25', response_class=HTMLResponse, include_in_schema=False)
    def bm25_page():
        return '<!doctype html><html lang="en"><meta charset="utf-8"><title>BM25</title><p style="font-size:3rem">Watch your sources!</p></html>'

    app.mount('/', StaticFiles(directory=ROOT / 'rag_app' / 'static', html=True), name='frontend')
    return app


app = create_app()
