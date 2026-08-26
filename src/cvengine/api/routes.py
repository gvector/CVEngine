"""FastAPI /v1 routes for the CVEngine backend."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from cvengine.observability import log_event
from cvengine.services import CVEngine

logger = logging.getLogger("cvengine")


class SearchRequest(BaseModel):
    """Input for the agentic search endpoint."""

    skills: list[str] = Field(default_factory=list)
    weights: list[float] | None = None
    job_description: str | None = None
    filters: dict[str, Any] | None = None
    top_k: int = Field(default=20, ge=1, le=200)
    synthesize: bool = False


class IngestRequest(BaseModel):
    """Input for single-CV text ingestion."""

    text: str
    resource_id: str | None = None


class BatchIngestRequest(BaseModel):
    """Input for folder-based batch ingestion."""

    folder: str


class CVEngineRouter:
    """Factory for the /v1 router bound to a CVEngine instance."""

    def __init__(self, engine: CVEngine) -> None:
        self._engine = engine

    def build(self) -> APIRouter:
        router = APIRouter(prefix="/v1")
        engine = self._engine

        @router.post("/search")
        def search(request: SearchRequest) -> dict[str, Any]:
            if not request.skills and not request.job_description:
                raise HTTPException(status_code=400, detail="Provide 'skills' or 'job_description'")
            state = engine.graph.invoke(
                {
                    "skills": request.skills,
                    "weights": request.weights,
                    "job_description": request.job_description,
                    "filters": request.filters,
                    "top_k": request.top_k,
                    "synthesize": request.synthesize,
                }
            )
            log_event(
                logger,
                "search executed",
                skills=state.get("skills"),
                top_results=len(state.get("results", [])),
                synthesize=request.synthesize,
            )
            return {
                "query_terms": state.get("query_terms", []),
                "results": state.get("results", []),
                "explanation": state.get("explanation"),
            }

        @router.post("/cvs")
        def ingest_cv(request: IngestRequest) -> dict[str, Any]:
            result = engine.ingestion.ingest_text(
                text=request.text,
                resource_id=request.resource_id,
            )
            if result.status == "failed":
                raise HTTPException(status_code=422, detail=result.error)
            return result.model_dump()

        @router.post("/cvs/batch")
        def ingest_batch(request: BatchIngestRequest) -> dict[str, Any]:
            try:
                summary = engine.ingestion.ingest_batch(request.folder)
            except FileNotFoundError as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc
            return summary.model_dump()

        @router.get("/cvs/{resource_id}")
        def get_cv(resource_id: str) -> dict[str, Any]:
            metadata = engine.repo.get_resource_metadata(resource_id)
            if metadata is None:
                raise HTTPException(status_code=404, detail=f"Resource {resource_id!r} not found")
            body = engine.repo.get_resource_body(resource_id)
            return {"resource_id": resource_id, "metadata": metadata, "body": body}

        @router.get("/cvs/{resource_id}/summary")
        def get_summary(resource_id: str) -> dict[str, str]:
            cached = engine.summaries.get(resource_id)
            if cached is not None:
                return {"answer": cached}
            body = engine.repo.get_resource_body(resource_id)
            if body is None:
                raise HTTPException(status_code=404, detail=f"Resource {resource_id!r} not found")
            response = engine.llm.chat(
                [
                    {
                        "role": "system",
                        "content": (
                            "You produce a concise professional summary of a candidate CV "
                            "(max 6 sentences). Answer only from the provided content."
                        ),
                    },
                    {"role": "user", "content": f"CV:\n{body}"},
                ]
            )
            engine.summaries.save(resource_id, response.content)
            return {"answer": response.content}

        @router.get("/status")
        def status() -> dict[str, Any]:
            return engine.status()

        return router


def build_router(engine: CVEngine) -> APIRouter:
    """Build the /v1 router for a given engine instance."""
    return CVEngineRouter(engine).build()
