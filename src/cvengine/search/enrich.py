"""Query enrichment: skill extraction from job descriptions and query expansion."""

from __future__ import annotations

import json
import logging
from typing import Any

from cvengine.llm.base import LLMProvider
from cvengine.observability import log_event

logger = logging.getLogger("cvengine")

SKILL_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"skills": {"type": "array", "items": {"type": "string"}}},
    "required": ["skills"],
}

EXPANSION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"queries": {"type": "array", "items": {"type": "string"}}},
    "required": ["queries"],
}

EXTRACT_PROMPT = (
    "Extract the skills strictly required for the following job description. "
    "Return the original skills verbatim, do not add or infer skills that are not "
    "explicitly mentioned. Ignore language requirements and years of experience. "
    "Answer only with valid JSON."
)

EXPAND_PROMPT = (
    "You are a search query expansion assistant. Given the list of skills below, "
    "produce a list of search queries for a semantic CV search. Keep every original "
    "skill verbatim as the first queries, then add concise related terms, synonyms "
    "and common tooling abbreviations that a candidate CV would contain. "
    "Return at most 12 queries in total. Answer only with valid JSON."
)


class QueryEnricher:
    """Extract skills from a job description and expand them into search queries."""

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    def extract_skills(self, job_description: str) -> list[str]:
        """Extract a skill list from a raw job description.

        :param job_description: the raw job description text
        :return: the extracted skills (or an empty list on failure)
        """
        if not job_description.strip():
            return []
        messages = [
            {"role": "system", "content": EXTRACT_PROMPT},
            {"role": "user", "content": f"Job description:\n{job_description}"},
        ]
        try:
            response = self._llm.chat(messages, json_schema=SKILL_SCHEMA)
            data = json.loads(response.content)
            skills = [skill.strip() for skill in data.get("skills", []) if skill.strip()]
            log_event(logger, "skills extracted", count=len(skills), model=self._llm.model)
            return skills
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            log_event(logger, "skill extraction failed", error=str(exc))
            return []

    def expand_queries(self, skills: list[str]) -> list[str]:
        """Expand a skill list into an enriched set of search queries.

        The original skills are always preserved; expansions are appended.

        :param skills: the base skills
        :return: the deduplicated list of search queries
        """
        if not skills:
            return []
        messages = [
            {"role": "system", "content": EXPAND_PROMPT},
            {"role": "user", "content": "Skills:\n" + "\n".join(f"- {skill}" for skill in skills)},
        ]
        queries = list(skills)
        try:
            response = self._llm.chat(messages, json_schema=EXPANSION_SCHEMA)
            data = json.loads(response.content)
            for query in data.get("queries", []):
                if isinstance(query, str) and query.strip():
                    queries.append(query.strip())
            log_event(
                logger,
                "queries expanded",
                base=len(skills),
                expanded=len(queries),
                model=self._llm.model,
            )
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            log_event(logger, "query expansion failed", error=str(exc))
        return list(dict.fromkeys(queries))
