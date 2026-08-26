"""Test doubles: fake embedding provider, fake LLM, fake engine."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from cvengine.llm.base import LLMProvider, LLMResponse

_TOKEN = re.compile(r"[a-z0-9]+")


class FakeEmbeddingProvider:
    """Deterministic bag-of-words embedding for tests (no model download).

    Cosine similarity is proportional to shared token overlap, which is enough
    to verify retrieval and ranking logic on synthetic data.
    """

    model_name = "fake-bow"
    dimension = 2048

    def _vectorize(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        for token in _TOKEN.findall(text.lower()):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            vector[index] += 1.0
        norm = sum(v * v for v in vector) ** 0.5
        if norm:
            vector = [v / norm for v in vector]
        return vector

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vectorize(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vectorize(text)


class FakeLLM(LLMProvider):
    """LLM stub responding from a substring -> JSON-content mapping."""

    name = "fake"
    model = "fake-model"

    def __init__(self, responses: dict[str, str]) -> None:
        self._responses = responses
        self.calls: list[list[dict[str, str]]] = []

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        json_schema: dict | None = None,
        temperature: float | None = None,
    ) -> LLMResponse:
        self.calls.append(messages)
        all_content = " ".join(m.get("content", "") for m in messages)
        for substring, payload in self._responses.items():
            if substring in all_content:
                return LLMResponse(content=payload)
        raise AssertionError(f"No fake response configured for content: {all_content[:120]!r}")


SECTIONING_OK = """{
  "resource_name": "Anna Rossi",
  "role": "Data Scientist",
  "business_line": "IT",
  "seniority": "Senior",
  "years_experience": 6.0,
  "languages": ["English", "Italian"],
  "certifications": [],
  "sections": [
    {"section": "summary", "text": "Senior Data Scientist.", "keywords": ["data scientist"]},
    {"section": "skills", "text": "Python pandas NumPy", "keywords": ["python", "pandas"]},
    {"section": "experience", "text": "Built ML models.", "keywords": ["machine learning"]}
  ]
}"""

SKILLS_OK = """{"skills": ["Python", "Machine Learning"]}"""

EXPANSION_OK = """{"queries": ["Python", "Machine Learning", "scikit-learn", "PyTorch"]}"""

EXPLANATION_OK = "The top resources match because of their deep Python expertise."


class FakeEngine:
    """Minimal stand-in for CVEngine exposing the attributes used by the API."""

    def __init__(
        self,
        repo: Any,
        ingestion: Any,
        enricher: Any,
        summaries: Any,
        llm: Any,
        graph: Any,
    ) -> None:
        self.repo = repo
        self.ingestion = ingestion
        self.enricher = enricher
        self.summaries = summaries
        self.llm = llm
        self.graph = graph
        self.settings = None
