"""Embedding providers for documents and queries."""

from __future__ import annotations

from typing import Protocol

from sentence_transformers import SentenceTransformer

from cvengine.constants import EMBEDDING_DOCUMENT_PREFIX, EMBEDDING_QUERY_PREFIX
from cvengine.observability import timeit


class EmbeddingProvider(Protocol):
    """Interface for embedding text into dense vectors."""

    @property
    def model_name(self) -> str: ...

    @property
    def dimension(self) -> int: ...

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class SentenceTransformerProvider:
    """Sentence-transformers based embedding provider (nomic-embed-text-v1.5)."""

    def __init__(self, model_name: str, dimension: int = 768) -> None:
        self._model = SentenceTransformer(model_name, trust_remote_code=True)
        self._model_name = model_name
        self._dimension = dimension

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        prefixed = [EMBEDDING_DOCUMENT_PREFIX + text for text in texts]
        return self._encode(prefixed)

    def embed_query(self, text: str) -> list[float]:
        return self._encode([EMBEDDING_QUERY_PREFIX + text])[0]

    @timeit("embedding_encode")
    def _encode(self, texts: list[str]) -> list[list[float]]:
        vectors = self._model.encode(texts, normalize_embeddings=True)
        return [vector.tolist() for vector in vectors]
