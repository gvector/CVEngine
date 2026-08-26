from __future__ import annotations

from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

from cvengine.embeddings.provider import EmbeddingProvider


class NomicEmbeddingFunction(EmbeddingFunction[Documents]):
    """Chroma-compatible embedding function backed by the nomic provider.

    Chroma still requires an embedding function on collection creation; the
    provider is used directly by the repository for explicit embedding
    computation, while this class satisfies the server-side contract.
    """

    def __init__(self, provider: EmbeddingProvider) -> None:
        self._provider = provider

    def __call__(self, input: Documents) -> Embeddings:
        return self._provider.embed_documents(list(input))
