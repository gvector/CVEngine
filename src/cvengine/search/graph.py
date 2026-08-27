"""Agentic search pipeline built with LangGraph."""

from __future__ import annotations

import logging
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from cvengine.constants import DEFAULT_SECTION_MULTIPLIERS
from cvengine.db.chroma import ChromaRepository
from cvengine.db.schemas import ChunkHit, RankedResource
from cvengine.llm.base import LLMProvider
from cvengine.observability import log_event, timeit
from cvengine.search.enrich import QueryEnricher
from cvengine.search.reranker import CrossEncoderReranker
from cvengine.search.scoring import score_hits

logger = logging.getLogger("cvengine")


class SearchState(TypedDict, total=False):
    """State propagated through the search graph."""

    skills: list[str]
    weights: list[float] | None
    job_description: str | None
    filters: dict[str, Any] | None
    top_k: int
    synthesize: bool
    query_terms: list[str]
    filters_effective: dict[str, Any] | None
    grouped_hits: list[list[ChunkHit]]
    results: list[RankedResource]
    explanation: str | None


class SearchGraph:
    """LangGraph orchestration: enrich -> retrieve -> rerank -> score -> synthesize."""

    def __init__(
        self,
        repo: ChromaRepository,
        enricher: QueryEnricher,
        reranker: CrossEncoderReranker | None = None,
        llm: LLMProvider | None = None,
        section_multipliers: dict[str, float] | None = None,
        alpha: float = 0.8,
        beta: float = 0.2,
        top_k_per_query: int = 30,
        rerank_top_n: int = 100,
    ) -> None:
        self._repo = repo
        self._enricher = enricher
        self._reranker = reranker
        self._llm = llm
        self._multipliers = section_multipliers or DEFAULT_SECTION_MULTIPLIERS
        self._alpha = alpha
        self._beta = beta
        self._top_k_per_query = top_k_per_query
        self._rerank_top_n = rerank_top_n
        self._graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(SearchState)
        builder.add_node("enrich", self._enrich)
        builder.add_node("retrieve", self._retrieve)
        builder.add_node("score", self._score)
        builder.add_node("synthesize", self._synthesize)

        builder.add_edge(START, "enrich")
        builder.add_edge("enrich", "retrieve")
        if self._reranker is not None:
            builder.add_node("rerank", self._rerank_node)
            builder.add_edge("retrieve", "rerank")
            builder.add_edge("rerank", "score")
        else:
            builder.add_edge("retrieve", "score")
        builder.add_conditional_edges(
            "score",
            self._should_synthesize,
            {"synthesize": "synthesize", "end": END},
        )
        builder.add_edge("synthesize", END)
        return builder.compile()

    def invoke(self, state: SearchState) -> SearchState:
        """Run the search graph with the given input state.

        :param state: initial search state
        :return: the final state containing results
        """
        return self._graph.invoke(dict(state))

    def _should_synthesize(self, state: SearchState) -> str:
        return "synthesize" if state.get("synthesize") else "end"

    @timeit("graph_enrich")
    def _enrich(self, state: SearchState) -> dict[str, Any]:
        skills = list(state.get("skills") or [])
        query_terms = skills
        if self._enricher is not None:
            try:
                if state.get("job_description"):
                    extracted = self._enricher.extract_skills(state["job_description"])
                    skills = skills + [s for s in extracted if s not in skills]
                if skills:
                    query_terms = self._enricher.expand_queries(skills)
            except Exception as exc:  # noqa: BLE001 - enrichment is best-effort
                log_event(
                    logger,
                    "enrichment degraded to base skills",
                    error=str(exc),
                )
        if not skills:
            raise ValueError("No skills provided and no skills extracted from the job description")

        filters_effective: dict[str, Any] | None = None
        business_line = (state.get("filters") or {}).get("business_line")
        if business_line:
            filters_effective = {"business_line": business_line}

        log_event(
            logger,
            "search enriched",
            skills=skills,
            query_terms=query_terms,
            filters=filters_effective,
        )
        return {
            "skills": skills,
            "query_terms": query_terms,
            "filters_effective": filters_effective,
        }

    @timeit("graph_retrieve")
    def _retrieve(self, state: SearchState) -> dict[str, Any]:
        top_k = max(self._top_k_per_query, state.get("top_k") or self._top_k_per_query)
        grouped = self._repo.query_text(
            queries=state["query_terms"],
            n_results=top_k,
            where=state.get("filters_effective"),
        )
        return {"grouped_hits": grouped}

    @timeit("graph_rerank")
    def _rerank_node(self, state: SearchState) -> dict[str, Any]:
        flat: list[ChunkHit] = [hit for group in state["grouped_hits"] for hit in group]
        by_key: dict[tuple[str, str], ChunkHit] = {}
        for hit in flat:
            by_key.setdefault((hit.resource_id, hit.text), hit)
        deduped = sorted(by_key.values(), key=lambda hit: hit.similarity, reverse=True)[: self._rerank_top_n]
        if not deduped:
            return {}
        query_text = " ".join(state["skills"])
        if self._reranker is None:
            return {}
        self._reranker.rerank(query_text, deduped)
        return {"grouped_hits": state["grouped_hits"]}  # objects mutated in place

    @timeit("graph_score")
    def _score(self, state: SearchState) -> dict[str, Any]:
        top_k = state.get("top_k") or self._top_k_per_query
        results = score_hits(
            grouped_hits=state["grouped_hits"],
            skills=state["skills"],
            weights=state.get("weights"),
            section_multipliers=self._multipliers,
            alpha=self._alpha,
            beta=self._beta,
            top_k=top_k,
        )
        return {"results": results}

    @timeit("graph_synthesize")
    def _synthesize(self, state: SearchState) -> dict[str, Any]:
        if self._llm is None or not state.get("results"):
            return {"explanation": None}
        top = state["results"][:5]
        lines = "\n".join(
            f"- {item.resource_id}: score {item.score} — snippet: {item.best_chunk[:220]}" for item in top
        )
        messages = [
            {
                "role": "system",
                "content": (
                    "You summarize CV search results for a recruiter. Produce a concise "
                    "overview (max 6 sentences) explaining why the top resources match "
                    "the requested skills. Answer only from the provided data."
                ),
            },
            {"role": "user", "content": f"Top matching resources:\n{lines}"},
        ]
        try:
            response = self._llm.chat(messages)
            return {"explanation": response.content}
        except Exception as exc:  # noqa: BLE001 - synthesis must never break the search
            log_event(logger, "synthesis failed", error=str(exc))
            return {"explanation": None}
