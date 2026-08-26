"""Cross-encoder reranker for improved query-chunk relevance."""

from __future__ import annotations

import logging
import math

from sentence_transformers import CrossEncoder

from cvengine.db.schemas import ChunkHit
from cvengine.observability import timeit

logger = logging.getLogger("cvengine")

DEFAULT_RERANKER_MODEL = "BAAI/bge-reranker-base"


def _sigmoid(value: float) -> float:
    if value >= 0:
        return 1.0 / (1.0 + math.exp(-value))
    return math.exp(value) / (1.0 + math.exp(value))


class CrossEncoderReranker:
    """Rerank retrieved chunks with a cross-encoder over query-chunk pairs."""

    def __init__(self, model_name: str = DEFAULT_RERANKER_MODEL) -> None:
        self._model = CrossEncoder(model_name)
        self.model_name = model_name

    @timeit("rerank")
    def rerank(self, query: str, hits: list[ChunkHit]) -> list[ChunkHit]:
        """Assign a sigmoid-normalized relevance score to each chunk.

        :param query: the combined query text
        :param hits: chunks to rerank (mutated with ``rerank_score``)
        :return: the same hits with their rerank scores set
        """
        if not hits:
            return hits
        pairs = [(query, hit.text) for hit in hits]
        scores = self._model.predict(pairs)
        for hit, score in zip(hits, scores, strict=True):
            hit.rerank_score = round(_sigmoid(float(score)), 4)
        return hits
