"""Synthetic CV generation for testing and evaluation."""

from __future__ import annotations

import random
from dataclasses import dataclass, field

BUSINESS_LINES = ["PV", "C&Q", "CSV", "GCP", "RA", "COMP", "DG", "ENG", "MD", "IT"]

SKILL_POOL: dict[str, list[str]] = {
    "python": ["Python", "pandas", "NumPy", "scikit-learn", "FastAPI", "Pytest"],
    "machine_learning": [
        "Machine Learning",
        "Deep Learning",
        "PyTorch",
        "TensorFlow",
        "NLP",
        "Transformers",
    ],
    "data_analysis": ["SQL", "Tableau", "Power BI", "Excel", "Data Analysis", "ETL"],
    "pharmacovigilance": [
        "Adverse Event",
        "PBRER",
        "PSMF",
        "EU GVP Module VI",
        "Argus",
        "Signal Detection",
    ],
    "validation": ["IQ", "OQ", "PQ", "Computer System Validation", "GAMP 5", "GxP"],
    "audit": ["GMP Audit", "GLP Audit", "GCP Inspection", "ISO 19011", "QMS"],
    "devops": ["Docker", "Kubernetes", "CI/CD", "Terraform", "AWS", "Linux"],
}

NAMES = [
    "Anna Rossi",
    "Marco Bianchi",
    "Luca Verdi",
    "Giulia Neri",
    "Paolo Gallo",
    "Elena Moretti",
    "Francesco Greco",
    "Sara Conti",
    "Davide Fontana",
    "Chiara Marino",
]

ROLES = [
    "Data Scientist",
    "Machine Learning Engineer",
    "Pharmacovigilance Specialist",
    "Validation Engineer",
    "QA Auditor",
    "Data Analyst",
    "DevOps Engineer",
]

SENIORITIES = ["Junior", "Mid", "Senior", "Lead"]


@dataclass
class SyntheticProfile:
    """A controlled CV profile used to verify ranking behaviour."""

    resource_id: str
    name: str
    role: str
    business_line: str
    seniority: str
    years_experience: float
    skills: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)


def build_cv_text(profile: SyntheticProfile) -> str:
    """Render a synthetic CV body from a profile.

    :param profile: the controlled profile
    :return: a plain-text CV
    """
    skills = ", ".join(profile.skills)
    languages = ", ".join(profile.languages) or "Italian (native), English (professional)"
    certifications = ", ".join(profile.certifications) or "None"
    company = "Acme Solutions"
    return f"""PROFESSIONAL SUMMARY
{profile.seniority} {profile.role} with {profile.years_experience:.0f} years of experience in {profile.business_line}.
Passionate about delivering high quality results and continuously improving processes.

SKILLS
{skills}

PROFESSIONAL EXPERIENCE
{profile.role} - {company}
- Applied {skills} daily to deliver projects in the {profile.business_line} domain.
- Collaborated with cross-functional teams and stakeholders.
- Improved process efficiency and quality of deliverables.

EDUCATION
Master of Science in Computer Science
Bachelor of Science in Engineering

CERTIFICATIONS
{certifications}

LANGUAGES
{languages}
"""


def generate_profiles(count: int, seed: int = 42, business_lines: list[str] | None = None) -> list[SyntheticProfile]:
    """Generate a deterministic list of synthetic CV profiles.

    :param count: number of profiles to generate
    :param seed: random seed for reproducibility
    :param business_lines: allowed business lines (defaults to all)
    :return: the generated profiles
    """
    rng = random.Random(seed)
    lines = business_lines or BUSINESS_LINES
    profiles: list[SyntheticProfile] = []
    for index in range(count):
        profile_skills = [rng.choice(list(SKILL_POOL.keys()))]
        if rng.random() < 0.5 and len(SKILL_POOL) > 1:
            second = rng.choice([k for k in SKILL_POOL if k != profile_skills[0]])
            profile_skills.append(second)
        skills = [
            skill
            for key in profile_skills
            for skill in rng.sample(SKILL_POOL[key], k=rng.randint(2, len(SKILL_POOL[key])))
        ]
        profiles.append(
            SyntheticProfile(
                resource_id=f"RES-{index + 1:04d}",
                name=rng.choice(NAMES),
                role=rng.choice(ROLES),
                business_line=rng.choice(lines),
                seniority=rng.choice(SENIORITIES),
                years_experience=round(rng.uniform(1.0, 15.0), 1),
                skills=skills,
                languages=rng.sample(["English", "Italian", "French", "Spanish"], k=rng.randint(1, 3)),
                certifications=rng.sample(
                    ["ISTQB", "PMP", "GCP Certificate", "Six Sigma", "AWS Solutions Architect"],
                    k=rng.randint(0, 2),
                ),
            )
        )
    return profiles


def generate_batch(
    count: int,
    seed: int = 42,
    business_lines: list[str] | None = None,
) -> list[tuple[SyntheticProfile, str]]:
    """Generate profiles paired with their CV text bodies."""
    return [
        (profile, build_cv_text(profile))
        for profile in generate_profiles(count, seed=seed, business_lines=business_lines)
    ]
