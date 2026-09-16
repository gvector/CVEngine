"""Hybrid scoring: rerank/cosine base + keyword metadata boost with section weights."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from cvengine.constants import DEFAULT_SECTION_MULTIPLIERS
from cvengine.db.schemas import ChunkHit, RankedResource, person_from_metadata

_ALNUM = re.compile(r"[^a-z0-9]+")

#: Normalized competence rank per seniority label (1..4 -> 0.25..1.0).
SENIORITY_RANK: dict[str, float] = {
    "junior": 0.25,
    "mid": 0.5,
    "senior": 0.75,
    "lead": 1.0,
    "principal": 1.0,
    "expert": 1.0,
    "manager": 0.75,
    "director": 1.0,
}


def competence_from_metadata(metadata: dict[str, Any]) -> float:
    """Derive a normalized competence value in [0, 1] from chunk metadata.

    Uses the ``seniority`` label when present, otherwise falls back to
    ``years_experience`` (capped at 20 years).

    :param metadata: chunk metadata (Person fields)
    :return: a competence value in [0, 1]
    """
    seniority = metadata.get("seniority")
    if isinstance(seniority, str) and seniority.strip():
        normalized = seniority.strip().lower()
        if normalized in SENIORITY_RANK:
            return SENIORITY_RANK[normalized]
    years = metadata.get("years_experience")
    if isinstance(years, (int, float)) and years > 0:
        return max(0.0, min(1.0, float(years) / 20.0))
    return 0.0


def _normalize(term: str) -> str:
    text = unicodedata.normalize("NFKD", term.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return _ALNUM.sub(" ", text).strip()


def keyword_overlap(query_terms: list[str], keywords: list[str]) -> float:
    """Fraction of normalized query terms appearing in the section keywords.

    :param query_terms: the original search skills
    :param keywords: the keywords metadata of a chunk
    :return: a value in [0, 1]
    """
    if not keywords:
        return 0.0
    query_set = {_normalize(term) for term in query_terms if _normalize(term)}
    if not query_set:
        return 0.0
    keyword_set = {_normalize(word) for word in keywords if _normalize(word)}
    overlap = query_set & keyword_set
    return len(overlap) / len(query_set)


def chunk_score(
    hit: ChunkHit,
    query_terms: list[str],
    section_multipliers: dict[str, float],
    alpha: float,
    beta: float,
    competence_weight: float = 0.0,
) -> float:
    """Compute the blended score of a single chunk.

    ``score = section_weight * (alpha * base + beta * keyword_overlap) +
    competence_weight * competence`` where ``base`` is the rerank score when
    available, else the cosine similarity, and ``competence`` is the normalized
    seniority/experience of the resource.

    :param hit: the retrieved chunk
    :param query_terms: the original search skills
    :param section_multipliers: per-section weights
    :param alpha: weight of the semantic base score
    :param beta: weight of the keyword metadata boost
    :param competence_weight: weight of the competence (seniority) boost
    :return: the blended score in [0, 1]
    """
    base = hit.rerank_score if hit.rerank_score is not None else hit.similarity
    boost = keyword_overlap(query_terms, hit.keywords)
    multiplier = section_multipliers.get(hit.section, DEFAULT_SECTION_MULTIPLIERS["other"])
    score = multiplier * (alpha * base + beta * boost)
    if competence_weight:
        score += competence_weight * competence_from_metadata(hit.metadata)
    return max(0.0, min(1.0, score))


def score_hits(
    grouped_hits: list[list[ChunkHit]],
    skills: list[str],
    weights: list[float] | None,
    section_multipliers: dict[str, float] | None = None,
    alpha: float = 0.8,
    beta: float = 0.2,
    competence_weight: float = 0.0,
    top_k: int = 20,
) -> list[RankedResource]:
    """Rank resources from per-query grouped hits.

    For each query skill the best chunk score per resource is kept; resources are
    then scored with the (weighted) average across skills.

    :param grouped_hits: hits grouped by query, in the same order as ``skills``
    :param skills: the query skills
    :param weights: optional per-skill weights (defaults to uniform)
    :param section_multipliers: optional per-section multipliers
    :param alpha: semantic weight
    :param beta: keyword boost weight
    :param competence_weight: weight of the competence (seniority) boost
    :param top_k: number of resources to return
    :return: ranked resources, descending by score
    """
    multipliers = section_multipliers or DEFAULT_SECTION_MULTIPLIERS
    weights = weights or [1.0] * len(skills)
    if len(weights) != len(skills):
        raise ValueError("weights and skills must have the same length")

    per_resource: dict[str, dict[str, Any]] = {}
    for skill_index, skill in enumerate(skills):
        for hit in grouped_hits[skill_index]:
            entry = per_resource.setdefault(
                hit.resource_id,
                {"bests": {}, "best_chunk": "", "best_score": -1.0, "person": {}},
            )
            value = chunk_score(hit, skills, multipliers, alpha, beta, competence_weight)
            previous = entry["bests"].get(skill, 0.0)
            if value > previous:
                entry["bests"][skill] = value
            if value > entry["best_score"]:
                entry["best_score"] = value
                entry["best_chunk"] = hit.text
                entry["person"] = person_from_metadata(hit.metadata)

    weight_sum = sum(weights)
    ranked: list[RankedResource] = []
    for resource_id, entry in per_resource.items():
        score = sum(weight * entry["bests"].get(skill, 0.0) for skill, weight in zip(skills, weights, strict=True))
        score = score / weight_sum if weight_sum else 0.0
        ranked.append(
            RankedResource(
                resource_id=resource_id,
                score=round(score, 4),
                best_chunk=entry["best_chunk"],
                skills_hit={skill: round(entry["bests"].get(skill, 0.0), 4) for skill in skills},
                person=entry["person"],
            )
        )

    ranked.sort(key=lambda item: item.score, reverse=True)
    return ranked[:top_k]
