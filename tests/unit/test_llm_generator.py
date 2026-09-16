import json

from cvengine.constants import Section
from cvengine.synthetic import generate_profiles
from cvengine.synthetic.llm_generator import LLMCVGenerator
from tests.fakes import FakeLLM

LLM_OUTPUT = {
    "resource_name": "Anna Rossi",
    "role": "Data Scientist",
    "business_line": "TECH",
    "seniority": "Lead",
    "years_experience": 12.0,
    "languages": ["English", "Italian"],
    "certifications": ["AWS"],
    "sections": [
        {
            "section": "summary",
            "text": "Lead Data Scientist with deep expertise.",
            "keywords": ["data science", "leadership"],
        },
        {
            "section": "skills",
            "text": "Python, Machine Learning, SQL",
            "keywords": ["Python", "Machine Learning", "SQL"],
        },
        {
            "section": "experience",
            "text": "Directed ML programs across clients.",
            "keywords": ["machine learning", "programs"],
        },
        {"section": "education", "text": "MSc in Computer Science", "keywords": ["education"]},
    ],
}


def _profile():
    return generate_profiles(1, seed=3)[0]


def test_llm_generator_produces_sections_with_keywords():
    llm = FakeLLM({"Write a professional CV for the following consultant": json.dumps(LLM_OUTPUT)})
    profile = _profile()
    output = LLMCVGenerator(llm).structure(profile)

    assert len(output.sections) == 4
    by_section = {s.section: s for s in output.sections}
    assert by_section[Section.SUMMARY].keywords == ["data science", "leadership"]
    assert by_section[Section.SKILLS].keywords == ["Python", "Machine Learning", "SQL"]
    assert by_section[Section.SUMMARY].keywords  # summary must NOT be empty


def test_llm_generator_falls_back_to_template_on_failure():
    llm = FakeLLM({"Write a professional CV for the following consultant": "{ invalid json"})
    profile = _profile()
    output = LLMCVGenerator(llm).structure(profile)

    sections = {s.section: s for s in output.sections}
    assert Section.SUMMARY in sections
    assert Section.SKILLS in sections
    # The fallback template still preserves the primary skill verbatim.
    assert profile.primary_skills[0].lower() in sections[Section.SKILLS].text.lower()


def test_llm_generator_uses_profile_skills_in_prompt():
    profile = _profile()
    prompt = LLMCVGenerator._build_user_prompt(profile)
    assert profile.name in prompt
    assert profile.branch in prompt
    assert profile.level.value in prompt
    for skill in profile.primary_skills[:2]:
        assert skill in prompt
