"""Embedding providers for documents and queries."""

from __future__ import annotations

import logging
import warnings
from typing import Protocol

from sentence_transformers import SentenceTransformer

from cvengine.constants import EMBEDDING_DOCUMENT_PREFIX, EMBEDDING_QUERY_PREFIX
from cvengine.observability import timeit

_model_logging_quiet = False


def quiet_model_logging() -> None:
    """Silence the noisy HuggingFace/transformers messages at model load time."""
    global _model_logging_quiet
    if _model_logging_quiet:
        return
    logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
    logging.getLogger("transformers_modules").setLevel(logging.ERROR)
    warnings.filterwarnings(
        "ignore",
        message=".*get_extended_attention_mask.*",
        category=DeprecationWarning,
    )
    try:
        from transformers.utils import logging as tf_logging

        tf_logging.set_verbosity_error()
    except ImportError:
        pass
    _model_logging_quiet = True


class EmbeddingProvider(Protocol):
    """Interface for embedding text into dense vectors."""

    @property
    def model_name(self) -> str: ...

    @property
    def dimension(self) -> int: ...

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class SentenceTransformerProvider:
    """Sentence-transformers based embedding provider.

    Task prefixes are applied when configured (e.g. nomic uses
    ``search_document:``/``search_query:``); embeddinggemma needs none.
    """

    def __init__(
        self,
        model_name: str,
        dimension: int = 768,
        query_prefix: str | None = None,
        document_prefix: str | None = None,
    ) -> None:
        quiet_model_logging()
        self._model = SentenceTransformer(model_name, trust_remote_code=True)
        self._model_name = model_name
        self._dimension = dimension
        self._query_prefix = query_prefix if query_prefix is not None else EMBEDDING_QUERY_PREFIX
        self._document_prefix = document_prefix if document_prefix is not None else EMBEDDING_DOCUMENT_PREFIX

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        prefixed = [self._document_prefix + text for text in texts]
        return self._encode(prefixed)

    def embed_query(self, text: str) -> list[float]:
        return self._encode([self._query_prefix + text])[0]

    @timeit("embedding_encode")
    def _encode(self, texts: list[str]) -> list[list[float]]:
        vectors = self._model.encode(texts, normalize_embeddings=True)
        return [vector.tolist() for vector in vectors]


class OllamaEmbeddingProvider:
    """Embedding provider backed by the local Ollama /api/embed endpoint.

    Used for models pulled into Ollama (e.g. ``embeddinggemma:300m``) that may
    be gated on HuggingFace or already present locally.
    """

    def __init__(self, base_url: str, model: str, dimension: int = 768) -> None:
        import ollama

        self._client = ollama.Client(host=base_url)
        self._model = model
        self._dimension = dimension

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed(list(texts))

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text])[0]

    @timeit("embedding_encode")
    def _embed(self, texts: list[str]) -> list[list[float]]:
        response = self._client.embed(model=self._model, input=texts)
        return [list(vector) for vector in response["embeddings"]]


def build_embedding(settings) -> EmbeddingProvider:
    """Instantiate the configured embedding provider.

    :param settings: the embedding configuration section
    :return: a ready-to-use provider
    :raises ValueError: for an unknown backend
    """
    if settings.backend == "ollama":
        return OllamaEmbeddingProvider(
            base_url=settings.base_url,
            model=settings.model,
            dimension=settings.dimension,
        )
    if settings.backend == "sentence-transformers":
        return SentenceTransformerProvider(
            model_name=settings.model,
            dimension=settings.dimension,
            query_prefix=settings.query_prefix,
            document_prefix=settings.document_prefix,
        )
    raise ValueError(f"Unknown embedding backend: {settings.backend!r}")
