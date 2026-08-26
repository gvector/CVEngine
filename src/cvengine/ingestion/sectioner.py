"""LLM-based CV sectioning and keyword extraction."""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from cvengine.constants import (
    MAX_SECTIONING_RETRIES,
    SECTION_KEYWORD_LIMIT,
    SECTION_NAMES,
    Section,
)
from cvengine.db.schemas import CVSection
from cvengine.llm.base import LLMProvider
from cvengine.observability import log_event

logger = logging.getLogger("cvengine")

SECTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "resource_name": {"type": ["string", "null"]},
        "role": {"type": ["string", "null"]},
        "business_line": {"type": ["string", "null"]},
        "seniority": {"type": ["string", "null"]},
        "years_experience": {"type": ["number", "null"]},
        "languages": {"type": "array", "items": {"type": "string"}},
        "certifications": {"type": "array", "items": {"type": "string"}},
        "sections": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "section": {"type": "string", "enum": SECTION_NAMES},
                    "text": {"type": "string"},
                    "keywords": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["section", "text", "keywords"],
            },
        },
    },
    "required": ["sections"],
}

SYSTEM_PROMPT = (
    "You are a CV structuring engine. Split the provided CV into sections using ONLY "
    f"the canonical section types: {', '.join(SECTION_NAMES)}. "
    "For each section provide the exact, verbatim text taken from the CV (do not "
    "paraphrase, summarize or invent content) and up to "
    f"{SECTION_KEYWORD_LIMIT} keywords that describe it. "
    "Extract the resource metadata (name, role, business line, seniority, years of "
    "experience, languages, certifications) only when present in the CV; otherwise use "
    "null or an empty list. Do not invent information. "
    "Split the CV so that the concatenation of section texts reproduces the original "
    "content as faithfully as possible. Answer only with valid JSON matching the schema."
)


class SectionEntry(BaseModel):
    """A single structured section as returned by the model."""

    section: Section
    text: str = Field(min_length=1)
    keywords: list[str] = Field(default_factory=list)


class SectioningOutput(BaseModel):
    """The full structured representation of a CV."""

    resource_name: str | None = None
    role: str | None = None
    business_line: str | None = None
    seniority: str | None = None
    years_experience: float | None = None
    languages: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    sections: list[SectionEntry] = Field(min_length=1)


class CVSectioner:
    """Structure a CV into sections and extract keywords via the LLM."""

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    def structure(self, text: str) -> SectioningOutput:
        """Run the LLM sectioning with validation and retries.

        :param text: the CV plain text
        :return: the validated structured output; falls back to a single
            ``other`` section if the model never returns valid JSON
        """
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"CV:\n{text}"},
        ]
        error_feedback: list[str] = []
        for attempt in range(1, MAX_SECTIONING_RETRIES + 1):
            prompt_messages = list(messages)
            if error_feedback:
                prompt_messages.append(
                    {
                        "role": "user",
                        "content": (
                            "Your previous answer was rejected for the following reason: "
                            f"{error_feedback[-1]}. Return a corrected valid JSON response."
                        ),
                    }
                )
            try:
                response = self._llm.chat(prompt_messages, json_schema=SECTION_SCHEMA)
                output = self._parse(response.content)
                log_event(
                    logger,
                    "cv sectioned",
                    sections=len(output.sections),
                    attempt=attempt,
                    model=self._llm.model,
                )
                return output
            except (ValidationError, json.JSONDecodeError, ValueError) as exc:
                error_feedback.append(str(exc))
                log_event(
                    logger,
                    "sectioning retry",
                    attempt=attempt,
                    error=str(exc),
                )
        log_event(
            logger,
            "sectioning failed, using fallback",
            attempts=MAX_SECTIONING_RETRIES,
        )
        return SectioningOutput(sections=[SectionEntry(section=Section.OTHER, text=text)])

    def _parse(self, content: str) -> SectioningOutput:
        data = json.loads(content)
        if not isinstance(data, dict) or "sections" not in data:
            raise ValueError("Response is missing the 'sections' key")
        return SectioningOutput.model_validate(data)


def to_cv_sections(output: SectioningOutput) -> list[CVSection]:
    """Convert a structured sectioning output into domain CVSection objects."""
    return [
        CVSection(
            section=entry.section,
            text=entry.text,
            keywords=[k for k in entry.keywords if k.strip()],
        )
        for entry in output.sections
        if entry.text.strip()
    ]


HEADING_MAP: dict[str, Section] = {
    "PROFESSIONAL SUMMARY": Section.SUMMARY,
    "SUMMARY": Section.SUMMARY,
    "PROFILE": Section.SUMMARY,
    "SKILLS": Section.SKILLS,
    "TECHNICAL SKILLS": Section.SKILLS,
    "EXPERIENCE": Section.EXPERIENCE,
    "PROFESSIONAL EXPERIENCE": Section.EXPERIENCE,
    "WORK EXPERIENCE": Section.EXPERIENCE,
    "PROJECTS": Section.PROJECTS,
    "EDUCATION": Section.EDUCATION,
    "CERTIFICATIONS": Section.CERTIFICATIONS,
    "CERTIFICATION": Section.CERTIFICATIONS,
    "LANGUAGES": Section.LANGUAGES,
}


class HeadingSectioner:
    """Deterministic sectioner that splits a CV on uppercase heading lines.

    Used for evaluation and tests where an LLM dependency is not desired.
    """

    def __init__(self) -> None:
        self._heading_pattern = None

    def structure(self, text: str) -> SectioningOutput:
        sections: list[SectionEntry] = []
        current_section = Section.OTHER
        current_lines: list[str] = []

        def flush() -> None:
            body = "\n".join(current_lines).strip()
            if body:
                sections.append(SectionEntry(section=current_section, text=body, keywords=[]))

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.isupper() and len(line) < 60 and line.replace(" ", "").isalpha():
                flush()
                current_lines = []
                current_section = HEADING_MAP.get(line, Section.OTHER)
            else:
                current_lines.append(line)
        flush()

        non_empty = [s for s in sections if s.text]
        if not non_empty:
            non_empty = [SectionEntry(section=Section.OTHER, text=text)]
        return SectioningOutput(sections=non_empty)
