"""Consulting-firm domain ontology for synthetic CV generation.

Describes the service lines (branches), their roles, the primary skill clusters
and the four competence levels used to build a verifiable synthetic dataset.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Level(StrEnum):
    """The four competence levels of a resource."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    PROFESSIONAL = "professional"


#: Numeric relevance used by the ranking evaluation (professional is best).
LEVEL_ORDER: dict[Level, int] = {
    Level.LOW: 1,
    Level.MEDIUM: 2,
    Level.HIGH: 3,
    Level.PROFESSIONAL: 4,
}


@dataclass(frozen=True)
class LevelProfile:
    """Parameters that make a generated CV express its competence level."""

    level: Level
    seniority: str
    years_min: float
    years_max: float
    primary_skills: tuple[int, int]
    secondary_skills: tuple[int, int]
    projects: tuple[int, int]
    certifications: tuple[int, int]
    verbs: tuple[str, ...]


LEVEL_PROFILES: dict[Level, LevelProfile] = {
    Level.LOW: LevelProfile(
        level=Level.LOW,
        seniority="Junior",
        years_min=1.0,
        years_max=3.0,
        primary_skills=(2, 3),
        secondary_skills=(1, 2),
        projects=(1, 1),
        certifications=(0, 0),
        verbs=("assisted with", "supported", "participated in"),
    ),
    Level.MEDIUM: LevelProfile(
        level=Level.MEDIUM,
        seniority="Mid",
        years_min=3.0,
        years_max=6.0,
        primary_skills=(4, 6),
        secondary_skills=(2, 3),
        projects=(2, 3),
        certifications=(0, 1),
        verbs=("contributed to", "implemented", "delivered"),
    ),
    Level.HIGH: LevelProfile(
        level=Level.HIGH,
        seniority="Senior",
        years_min=6.0,
        years_max=10.0,
        primary_skills=(6, 8),
        secondary_skills=(3, 4),
        projects=(3, 4),
        certifications=(1, 2),
        verbs=("led", "designed", "managed"),
    ),
    Level.PROFESSIONAL: LevelProfile(
        level=Level.PROFESSIONAL,
        seniority="Lead",
        years_min=10.0,
        years_max=18.0,
        primary_skills=(8, 12),
        secondary_skills=(4, 6),
        projects=(4, 6),
        certifications=(2, 3),
        verbs=("architected", "directed", "established", "owned"),
    ),
}


@dataclass(frozen=True)
class Role:
    """A role within a branch with its primary skill cluster."""

    name: str
    primary_skills: tuple[str, ...]
    certifications: tuple[str, ...] = ()


@dataclass(frozen=True)
class Branch:
    """A service line (business line) of the consulting firm."""

    code: str
    name: str
    roles: tuple[Role, ...]


BRANCHES: tuple[Branch, ...] = (
    Branch(
        code="STRATEGY",
        name="Strategy & Management",
        roles=(
            Role(
                "Business Analyst",
                ("market analysis", "requirements gathering", "process mapping", "business planning", "KPI definition"),
                ("CBAP", "Lean Six Sigma Green Belt"),
            ),
            Role(
                "Strategy Consultant",
                (
                    "business strategy",
                    "M&A due diligence",
                    "competitive analysis",
                    "change management",
                    "business modeling",
                ),
                ("PMP", "Lean Six Sigma Black Belt"),
            ),
            Role(
                "Engagement Manager",
                ("PMO", "project management", "stakeholder management", "budgeting", "risk management"),
                ("PMP", "PRINCE2"),
            ),
        ),
    ),
    Branch(
        code="FINANCE",
        name="Finance & Accounting",
        roles=(
            Role(
                "Accountant",
                ("bookkeeping", "IFRS", "GAAP", "tax compliance", "reconciliation"),
                ("ACCA", "CPA"),
            ),
            Role(
                "Financial Controller",
                ("controlling", "budgeting", "forecasting", "financial reporting", "SAP", "cost accounting"),
                ("CIMA", "ACCA"),
            ),
            Role(
                "Tax Consultant",
                ("corporate tax", "VAT", "transfer pricing", "tax compliance", "fiscal planning"),
                ("CTA", "ACCA"),
            ),
        ),
    ),
    Branch(
        code="TECH",
        name="Technology & Digital",
        roles=(
            Role(
                "Software Engineer",
                ("Python", "Java", "REST APIs", "unit testing", "software design", "Git", "microservices"),
                ("AWS Certified Developer", "Oracle Certified Professional"),
            ),
            Role(
                "Data Scientist",
                ("Python", "Machine Learning", "statistics", "SQL", "data visualization", "feature engineering", "NLP"),
                ("TensorFlow Developer", "Azure Data Scientist"),
            ),
            Role(
                "Cloud Engineer",
                ("AWS", "Azure", "Docker", "Kubernetes", "Terraform", "CI/CD", "Linux"),
                ("AWS Solutions Architect", "CKA"),
            ),
        ),
    ),
    Branch(
        code="COMPLIANCE",
        name="Compliance & Quality",
        roles=(
            Role(
                "Quality Consultant",
                ("QMS", "GMP", "ISO 9001", "CAPA", "internal audit", "risk assessment"),
                ("ISO 9001 Lead Auditor", "Six Sigma"),
            ),
            Role(
                "Regulatory Affairs Specialist",
                ("regulatory submissions", "MDR", "IVDR", "EMA", "FDA", "technical documentation"),
                ("RAC",),
            ),
            Role(
                "Validation Engineer",
                ("CSV", "GAMP 5", "IQ/OQ/PQ", "GxP", "data integrity", "qualification"),
                ("GAMP 5", "ISO 13485"),
            ),
        ),
    ),
    Branch(
        code="HR",
        name="Human Resources",
        roles=(
            Role(
                "HR Specialist",
                ("recruiting", "onboarding", "HRIS", "labor law", "personnel administration"),
                ("CIPD",),
            ),
            Role(
                "Talent Acquisition Specialist",
                ("sourcing", "interviewing", "employer branding", "ATS", "talent pipeline"),
                ("CIPD", "AIRS"),
            ),
            Role(
                "HR Business Partner",
                (
                    "performance management",
                    "employee relations",
                    "organizational design",
                    "compensation",
                    "workforce planning",
                ),
                ("CIPD", "SHRM"),
            ),
        ),
    ),
    Branch(
        code="OPS",
        name="Internal Services",
        roles=(
            Role(
                "Legal Counsel",
                ("contract law", "corporate law", "GDPR", "compliance", "negotiation"),
                (),
            ),
            Role(
                "Marketing Specialist",
                ("digital marketing", "SEO", "CRM", "content strategy", "campaign management"),
                ("Google Analytics", "HubSpot"),
            ),
            Role(
                "IT Support Specialist",
                ("helpdesk", "networking", "Windows", "Linux", "ticketing", "hardware troubleshooting"),
                ("CompTIA A+", "ITIL"),
            ),
        ),
    ),
)

#: Cross-cutting secondary skills sampled across resources.
SECONDARY_SKILL_POOL: tuple[str, ...] = (
    "Agile",
    "Scrum",
    "communication",
    "stakeholder management",
    "documentation",
    "teamwork",
    "problem solving",
    "presentation",
    "Jira",
    "Confluence",
    "time management",
    "analytical thinking",
)

LANGUAGES: tuple[str, ...] = ("English", "Italian", "French", "Spanish", "German")

EDUCATION: tuple[str, ...] = (
    "Master of Science",
    "Bachelor of Science",
    "Master's degree",
    "PhD",
)


def branches_by_code() -> dict[str, Branch]:
    """Return the branches indexed by their business-line code."""
    return {branch.code: branch for branch in BRANCHES}


def all_role_cells() -> list[tuple[Branch, Role]]:
    """Return every (branch, role) pair."""
    return [(branch, role) for branch in BRANCHES for role in branch.roles]
