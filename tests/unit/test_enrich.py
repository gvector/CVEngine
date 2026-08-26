from cvengine.search.enrich import QueryEnricher
from tests.fakes import EXPANSION_OK, SKILLS_OK, FakeLLM


def test_extract_skills_from_job_description():
    llm = FakeLLM({"Job description:": SKILLS_OK})
    skills = QueryEnricher(llm).extract_skills("We need a Python ML engineer")
    assert skills == ["Python", "Machine Learning"]


def test_extract_skills_returns_empty_on_failure():
    llm = FakeLLM({"Job description:": "not json"})
    assert QueryEnricher(llm).extract_skills("jd") == []


def test_extract_skills_ignores_blank():
    assert QueryEnricher(FakeLLM({})).extract_skills("   ") == []


def test_expand_queries_keeps_original_skills():
    llm = FakeLLM({"Skills:": EXPANSION_OK})
    queries = QueryEnricher(llm).expand_queries(["Python"])
    assert queries[0] == "Python"
    assert len(queries) == len(set(queries))


def test_expand_queries_falls_back_to_base():
    llm = FakeLLM({"Skills:": "broken"})
    queries = QueryEnricher(llm).expand_queries(["Python"])
    assert queries == ["Python"]
