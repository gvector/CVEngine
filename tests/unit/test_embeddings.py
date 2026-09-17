import pytest

from cvengine.config import EmbeddingSettings
from cvengine.embeddings.provider import OllamaEmbeddingProvider, build_embedding


def test_build_embedding_ollama_backend():
    settings = EmbeddingSettings(backend="ollama", model="embeddinggemma:300m")
    provider = build_embedding(settings)
    assert isinstance(provider, OllamaEmbeddingProvider)
    assert provider.model_name == "embeddinggemma:300m"
    assert provider.dimension == 768


def test_build_embedding_unknown_backend():
    with pytest.raises(ValueError):
        build_embedding(EmbeddingSettings(backend="nope"))
