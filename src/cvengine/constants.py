from enum import StrEnum


class Section(StrEnum):
    """Canonical CV section types produced by the LLM sectioning step."""

    SUMMARY = "summary"
    SKILLS = "skills"
    EXPERIENCE = "experience"
    PROJECTS = "projects"
    CERTIFICATIONS = "certifications"
    EDUCATION = "education"
    LANGUAGES = "languages"
    OTHER = "other"


SECTION_NAMES = [s.value for s in Section]

DEFAULT_SECTION_MULTIPLIERS: dict[str, float] = {
    Section.SKILLS.value: 1.0,
    Section.EXPERIENCE.value: 0.9,
    Section.PROJECTS.value: 0.8,
    Section.CERTIFICATIONS.value: 0.7,
    Section.SUMMARY.value: 0.7,
    Section.EDUCATION.value: 0.6,
    Section.LANGUAGES.value: 0.6,
    Section.OTHER.value: 0.5,
}

SECTION_KEYWORD_LIMIT = 8

EMBEDDING_QUERY_PREFIX = "search_query: "
EMBEDDING_DOCUMENT_PREFIX = "search_document: "

MAX_SECTIONING_RETRIES = 3
