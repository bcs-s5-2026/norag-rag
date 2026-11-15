import pytest


@pytest.fixture(autouse=True)
def isolated_llm_settings(monkeypatch):
    # Uploading must never call a real model during tests; graph tests inject a fake extractor.
    monkeypatch.setenv('RAG_GRAPH_AUTO', '0')
    # A developer's own .env (LLM_* values) must not leak into tests that check the "no key" paths.
    # Set-but-empty is not overridden when the app loads .env.
    for name in ('LLM_URL', 'LLM_API_KEY', 'LLM_MODEL'):
        monkeypatch.setenv(name, '')
