"""Data models shared across the ingestion and search layers."""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel, Field

from cvengine.constants import Section


class PersonMetadata(BaseModel):
    """Metadata attached to a resource (person) and to each chunk."""

    model_config = {"extra": "ignore"}

    resource_id: str
    resource_name: str | None = None
    role: str | None = None
    company: str | None = None
    business_line: str | None = None
    email: str | None = None
    resume_date: str | None = None
    status: str | None = None
    y_in_pqe: float | None = None
    country_residenza: str | None = None
    city_residenza: str | None = None
    cv_docx_name: str | None = None
    id_db: int | None = None
    seniority: str | None = None
    years_experience: float | None = None
    languages: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    source: str = "text"


@dataclass
class CVSection:
    """A single section of a processed CV with its keywords."""

    section: Section
    text: str
    keywords: list[str] = field(default_factory=list)


@dataclass
class ProcessedCV:
    """The output of the ingestion pipeline for a single resource."""

    resource_id: str
    body: str
    content_hash: str
    sections: list[CVSection]
    metadata: PersonMetadata


@dataclass
class ChunkHit:
    """A retrieved chunk with its cosine similarity and optional rerank score."""

    resource_id: str
    section: str
    text: str
    keywords: list[str]
    similarity: float
    rerank_score: float | None = None


@dataclass
class RankedResource:
    """A resource ranked by the search pipeline."""

    resource_id: str
    score: float
    best_chunk: str
    skills_hit: dict[str, float]
    explanation: str | None = None
