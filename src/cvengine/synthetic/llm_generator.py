"""LLM-based CV generation for the synthetic consulting dataset.

Given a controlled profile, the LLM writes a realistic English CV that must
preserve the provided skills verbatim and reflect the competence level. The
output is structured (per-section keywords) so every section carries search
keywords. Falls back to the deterministic template when the LLM fails.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from cvengine.ingestion.sectioner import HeadingSectioner, llm_sectioning
from cvengine.llm.base import LLMProvider
from cvengine.synthetic.domain import LEVEL_PROFILES, Level
from cvengine.synthetic.generator import SyntheticProfile, build_cv_text

SYSTEM_PROMPT = (
    "You are an expert CV writer for an international consulting firm. Write a "
    "realistic, professional English CV that faithfully reflects the provided "
    "consultant profile. Structure the CV into these canonical sections: summary, "
    "skills, experience, projects, education, certifications, languages.\n"
    "Rules:\n"
    "- The SKILLS section must list ONLY the provided skills, verbatim and "
    "comma-separated.\n"
    "- Summary, experience and projects must be consistent with the seniority and "
    "years of experience.\n"
    "- Use verbs appropriate to the level: professional -> architected/directed/"
    "established/owned; high -> led/designed/managed; medium -> contributed/"
    "implemented/delivered; low -> assisted/supported/participated.\n"
    "- Provide 3 to 6 short keywords for EVERY section that summarize its content "
    "(these keywords are used for search).\n"
    "- Do not invent skills, certifications or employers; use realistic consulting "
    "context appropriate to the business line.\n"
    "Respond only with valid JSON matching the schema."
)

_LEVEL_VERBS: dict[Level, str] = {
    Level.PROFESSIONAL: "expert with leadership and cross-functional ownership",
    Level.HIGH: "senior professional trusted to lead complex engagements",
    Level.MEDIUM: "solid professional delivering reliable results",
    Level.LOW: "junior professional eager to grow",
}


class LLMCVGenerator:
    """Generate structured, profile-faithful CVs with an LLM."""

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    def structure(self, profile: SyntheticProfile):
        """Generate a SectioningOutput for the given profile.

        :param profile: the controlled profile (skills, level, branch, ...)
        :return: the structured sections with per-section keywords
        """

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": self._build_user_prompt(profile)},
        ]
        return llm_sectioning(
            self._llm,
            messages,
            fallback=self._fallback(profile),
        )

    @staticmethod
    def _build_user_prompt(profile: SyntheticProfile) -> str:
        skills = ", ".join([*profile.primary_skills, *profile.secondary_skills])
        certifications = ", ".join(profile.certifications) if profile.certifications else "None"
        languages = ", ".join(profile.languages)
        level_profile = LEVEL_PROFILES[profile.level]
        return f"""Write a professional CV for the following consultant.

- Full name: {profile.name}
- Role: {profile.role}
- Business line (sector): {profile.branch_name} ({profile.branch})
- Seniority / level: {profile.seniority} ({profile.level.value})
- Level description: {_LEVEL_VERBS[profile.level]}
- Years of experience: {profile.years_experience}
- Number of projects to describe: {profile.projects}
- Skills (use ONLY these in the SKILLS section, verbatim): {skills}
- Certifications: {certifications}
- Languages: {languages}
- Education: {profile.education}
- Expected verb register: {", ".join(level_profile.verbs)}

Produce the CV now."""

    def _fallback(self, profile: SyntheticProfile) -> Callable[[], Any]:
        def _fallback() -> Any:
            text = build_cv_text(profile)
            return HeadingSectioner().structure(text)

        return _fallback
