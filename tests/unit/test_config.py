from cvengine.config import Settings


def test_defaults():
    settings = Settings()
    assert settings.llm.provider == "ollama"
    assert settings.llm.model == "llama3.1:8b"
    assert settings.embedding.model == "nomic-ai/nomic-embed-text-v1.5"
    assert settings.embedding.dimension == 768
    assert settings.chroma.port == 8000
    assert settings.scoring.alpha == 0.8
    assert settings.scoring.beta == 0.2
    assert settings.chroma.test_collection.endswith("__test")


def test_env_override(monkeypatch):
    monkeypatch.setenv("CVENGINE_LLM_PROVIDER", "openai")
    monkeypatch.setenv("CVENGINE_LLM_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("CVENGINE_SCORING_ALPHA", "0.9")
    settings = Settings()
    assert settings.llm.provider == "openai"
    assert settings.llm.model == "gpt-4o-mini"
    assert settings.scoring.alpha == 0.9
