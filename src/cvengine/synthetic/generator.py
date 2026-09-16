"""Synthetic CV generation for a consulting firm.

Builds a controlled, verifiable dataset: each resource has a branch, a role, a
competence level and a primary skill cluster. The CV text is generated from
deterministic templates (no LLM) so the ground truth is exact.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from faker import Faker

from cvengine.synthetic.domain import (
    BRANCHES,
    EDUCATION,
    LANGUAGES,
    LEVEL_ORDER,
    LEVEL_PROFILES,
    SECONDARY_SKILL_POOL,
    Branch,
    Level,
    Role,
    all_role_cells,
)

_LEVEL_SUMMARY = {
    Level.LOW: "Eager to grow and contribute to structured, well-scoped workstreams.",
    Level.MEDIUM: "Focused on delivering reliable results across multiple workstreams.",
    Level.HIGH: "Trusted to lead complex engagements and mentor junior colleagues.",
    Level.PROFESSIONAL: "Recognized expert driving strategy and cross-functional programs.",
}


@dataclass
class SyntheticProfile:
    """A controlled CV profile with its known ground truth."""

    resource_id: str
    name: str
    email: str
    city: str
    country: str
    branch: str
    branch_name: str
    role: str
    level: Level
    seniority: str
    years_experience: float
    primary_skills: list[str] = field(default_factory=list)
    secondary_skills: list[str] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    projects: int = 1
    education: str = "Master of Science"


def _cell_distribution(total: int, cells: int) -> list[int]:
    """Distribute ``total`` items across ``cells`` as evenly as possible."""
    base, remainder = divmod(total, cells)
    return [base + (1 if index < remainder else 0) for index in range(cells)]


def _make_fakers(seed: int) -> tuple[Faker, Faker]:
    italian = Faker("it_IT")
    english = Faker("en_US")
    italian.seed_instance(seed)
    english.seed_instance(seed)
    return italian, english


def _sample(rng: random.Random, pool: tuple[str, ...], k: int) -> list[str]:
    k = max(0, min(k, len(pool)))
    return rng.sample(list(pool), k=k)


def _build_profile(
    rng: random.Random,
    index: int,
    branch: Branch,
    role: Role,
    level: Level,
    italian: Faker,
    english: Faker,
) -> SyntheticProfile:
    level_profile = LEVEL_PROFILES[level]
    faker = italian if rng.random() < 0.5 else english
    name = faker.name()
    first, _, last = name.partition(" ")
    email = f"{first.lower()}.{last.lower().replace(' ', '')}@example.com"

    primary_k = rng.randint(*level_profile.primary_skills)
    secondary_k = rng.randint(*level_profile.secondary_skills)
    cert_k = rng.randint(*level_profile.certifications)

    return SyntheticProfile(
        resource_id=f"SYN-{index:04d}",
        name=name,
        email=email,
        city=faker.city(),
        country=faker.current_country() or ("Italy" if faker is italian else "United States"),
        branch=branch.code,
        branch_name=branch.name,
        role=role.name,
        level=level,
        seniority=level_profile.seniority,
        years_experience=round(rng.uniform(level_profile.years_min, level_profile.years_max), 1),
        primary_skills=_sample(rng, role.primary_skills, primary_k),
        secondary_skills=_sample(rng, SECONDARY_SKILL_POOL, secondary_k),
        certifications=_sample(rng, role.certifications, cert_k),
        languages=["English", *rng.sample([lang for lang in LANGUAGES if lang != "English"], k=rng.randint(0, 2))],
        projects=rng.randint(*level_profile.projects),
        education=rng.choice(EDUCATION),
    )


def generate_profiles(
    count: int = 400,
    seed: int = 42,
) -> list[SyntheticProfile]:
    """Generate a deterministic, evenly distributed list of synthetic profiles.

    :param count: total number of profiles
    :param seed: random seed for reproducibility
    :return: the generated profiles
    """
    rng = random.Random(seed)
    italian, english = _make_fakers(seed)

    cells = all_role_cells()
    levels = list(Level)
    # Build the full (branch, role, level) matrix and distribute the count over it.
    matrix = [(branch, role, level) for branch, role in cells for level in levels]
    distribution = _cell_distribution(count, len(matrix))

    profiles: list[SyntheticProfile] = []
    index = 1
    for (branch, role, level), amount in zip(matrix, distribution, strict=True):
        for _ in range(amount):
            profiles.append(_build_profile(rng, index, branch, role, level, italian, english))
            index += 1
    return profiles


def build_cv_text(profile: SyntheticProfile) -> str:
    """Render a synthetic CV body (English) that encodes the competence level.

    :param profile: the controlled profile
    :return: a plain-text CV with canonical section headings
    """
    level_profile = LEVEL_PROFILES[profile.level]
    skills = ", ".join([*profile.primary_skills, *profile.secondary_skills])
    certifications = ", ".join(profile.certifications) if profile.certifications else "None"
    languages = ", ".join(profile.languages)
    headline = ", ".join(profile.primary_skills[:3]) or profile.role

    experience_lines: list[str] = []
    for project_index in range(profile.projects):
        verb = level_profile.verbs[project_index % len(level_profile.verbs)]
        skill = profile.primary_skills[project_index % len(profile.primary_skills)]
        experience_lines.append(
            f"- {verb.capitalize()} {skill} activities for a {profile.branch_name} client, "
            f"delivering measurable outcomes across {project_index + 1} workstream(s)."
        )

    return f"""PROFESSIONAL SUMMARY
{profile.seniority} {profile.role} with {profile.years_experience:.0f} years of experience in {profile.branch_name}.
Specializing in {headline}. {_LEVEL_SUMMARY[profile.level]}

SKILLS
{skills}

PROFESSIONAL EXPERIENCE
{profile.role} - Consulting Firm
{chr(10).join(experience_lines)}

EDUCATION
{profile.education} in a relevant field

CERTIFICATIONS
{certifications}

LANGUAGES
{languages}
"""


def generate_batch(
    count: int = 400,
    seed: int = 42,
) -> list[tuple[SyntheticProfile, str]]:
    """Generate profiles paired with their rendered CV text."""
    return [(profile, build_cv_text(profile)) for profile in generate_profiles(count, seed=seed)]


def build_manifest(profiles: list[SyntheticProfile], seed: int = 42) -> dict:
    """Build the ground-truth manifest used by the ranking evaluation."""
    return {
        "seed": seed,
        "count": len(profiles),
        "levels": {level.value: LEVEL_ORDER[level] for level in Level},
        "branches": [branch.code for branch in BRANCHES],
        "resources": [
            {
                "resource_id": profile.resource_id,
                "name": profile.name,
                "branch": profile.branch,
                "role": profile.role,
                "level": profile.level.value,
                "seniority": profile.seniority,
                "years_experience": profile.years_experience,
                "primary_skills": profile.primary_skills,
                "secondary_skills": profile.secondary_skills,
                "certifications": profile.certifications,
                "languages": profile.languages,
            }
            for profile in profiles
        ],
    }


def profile_metadata(profile: SyntheticProfile) -> dict:
    """Map a profile onto the chunk metadata schema used by ingestion."""
    return {
        "resource_name": profile.name,
        "email": profile.email,
        "city_residenza": profile.city,
        "country_residenza": profile.country,
        "role": profile.role,
        "business_line": profile.branch,
        "seniority": profile.seniority,
        "years_experience": profile.years_experience,
        "languages": profile.languages,
        "certifications": profile.certifications,
        "source": "synthetic",
    }
