"""Application container wiring settings to the runtime components."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from cvengine.config import Settings
from cvengine.constants import DEFAULT_SECTION_MULTIPLIERS
from cvengine.db.chroma import ChromaRepository
from cvengine.embeddings.provider import SentenceTransformerProvider
from cvengine.ingestion.pipeline import IngestionPipeline
from cvengine.ingestion.sectioner import CVSectioner
from cvengine.llm.base import LLMProvider
from cvengine.llm.factory import build_llm
from cvengine.observability import log_event
from cvengine.search.enrich import QueryEnricher
from cvengine.search.graph import SearchGraph
from cvengine.search.reranker import CrossEncoderReranker

logger = logging.getLogger("cvengine")


class SummaryStore:
    """JSON-backed cache for LLM resource summaries."""

    def __init__(self, data_dir: str | Path) -> None:
        self._path = Path(data_dir) / "summaries.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._data: dict[str, str] = {}
        if self._path.exists():
            try:
                self._data = json.loads(self._path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                self._data = {}

    def get(self, resource_id: str) -> str | None:
        return self._data.get(resource_id)

    def save(self, resource_id: str, summary: str) -> None:
        self._data[resource_id] = summary
        self._path.write_text(json.dumps(self._data, indent=2, ensure_ascii=False), encoding="utf-8")


class CVEngine:
    """Top-level container exposing the composed application components."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()
        self.llm: LLMProvider = build_llm(self.settings.llm)
        self.embedding = SentenceTransformerProvider(
            model_name=self.settings.embedding.model,
            dimension=self.settings.embedding.dimension,
        )
        self.repo = ChromaRepository(
            host=self.settings.chroma.host,
            port=self.settings.chroma.port,
            collection_name=self.settings.chroma.collection,
            provider=self.embedding,
        )
        self.sectioner = CVSectioner(self.llm)
        self.ingestion = IngestionPipeline(
            repo=self.repo,
            sectioner=self.sectioner,
        )
        self.enricher = QueryEnricher(self.llm)
        self.summaries = SummaryStore(self.settings.data_dir)
        self._reranker: CrossEncoderReranker | None = None
        self._graph: SearchGraph | None = None

    @property
    def reranker(self) -> CrossEncoderReranker | None:
        """Lazily instantiate the cross-encoder reranker."""
        if self._reranker is None:
            try:
                self._reranker = CrossEncoderReranker()
                log_event(logger, "reranker loaded", model=self._reranker.model_name)
            except Exception as exc:  # noqa: BLE001 - search must degrade gracefully
                log_event(logger, "reranker unavailable", error=str(exc))
                self._reranker = None
        return self._reranker

    @property
    def graph(self) -> SearchGraph:
        """Lazily build the agentic search graph."""
        if self._graph is None:
            self._graph = SearchGraph(
                repo=self.repo,
                enricher=self.enricher,
                reranker=self.reranker,
                llm=self.llm,
                section_multipliers=DEFAULT_SECTION_MULTIPLIERS,
                alpha=self.settings.scoring.alpha,
                beta=self.settings.scoring.beta,
                top_k_per_query=self.settings.scoring.top_k_per_query,
                rerank_top_n=self.settings.scoring.rerank_top_n,
            )
        return self._graph

    def status(self) -> dict:
        """Return a summary of the runtime state without heavy model loads."""
        reranker = "BAAI/bge-reranker-base" if self._reranker is not None else "not loaded (lazy)"
        try:
            chunk_count = self.repo.count()
            resource_count = len(self.repo.get_resource_ids())
        except Exception as exc:  # noqa: BLE001
            return {
                "chroma": {"reachable": False, "error": str(exc)},
                "llm": {"provider": self.settings.llm.provider, "model": self.settings.llm.model},
                "embedding": {"model": self.settings.embedding.model, "dimension": self.settings.embedding.dimension},
                "reranker": reranker,
            }
        return {
            "chroma": {
                "reachable": True,
                "host": self.settings.chroma.host,
                "port": self.settings.chroma.port,
                "collection": self.repo.collection_name,
                "chunks": chunk_count,
                "resources": resource_count,
            },
            "llm": {"provider": self.settings.llm.provider, "model": self.settings.llm.model},
            "embedding": {"model": self.settings.embedding.model, "dimension": self.settings.embedding.dimension},
            "reranker": reranker,
        }
