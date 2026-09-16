import pytest

from cvengine.db.schemas import ChunkHit
from cvengine.search.scoring import (
    chunk_score,
    competence_from_metadata,
    keyword_overlap,
    score_hits,
)


def _hit(resource_id, section, text, keywords, similarity, rerank=None):
    return ChunkHit(
        resource_id=resource_id,
        section=section,
        text=text,
        keywords=keywords,
        similarity=similarity,
        rerank_score=rerank,
    )


def test_keyword_overlap_basic():
    assert keyword_overlap(["Python", "ML"], ["python", "pandas"]) == 0.5
    assert keyword_overlap(["Python"], ["pandas"]) == 0.0
    assert keyword_overlap(["Python"], []) == 0.0


def test_keyword_overlap_normalizes_accents_and_case():
    assert keyword_overlap(["Python"], ["PYTHON"]) == 1.0
    assert keyword_overlap(["café"], ["cafe"]) == 1.0


def test_chunk_score_uses_rerank_when_available():
    hit = _hit("r1", "skills", "text", ["python"], 0.3, rerank=0.8)
    score = chunk_score(hit, ["python"], {"skills": 1.0}, alpha=0.8, beta=0.2)
    assert score == pytest.approx(0.8 * 0.8 + 0.2 * 1.0)


def test_chunk_score_applies_section_multiplier():
    hit = _hit("r1", "education", "text", ["python"], 1.0)
    score = chunk_score(hit, ["python"], {"education": 0.6}, alpha=0.8, beta=0.2)
    assert score == pytest.approx(0.6 * (0.8 * 1.0 + 0.2 * 1.0))


def test_score_hits_ranks_by_weighted_best_per_skill():
    hits = [
        [_hit("a", "skills", "ta", ["python"], 1.0), _hit("b", "skills", "tb", ["python"], 0.2)],
        [_hit("a", "skills", "ta2", ["ml"], 0.1), _hit("b", "skills", "tb2", ["ml"], 0.95)],
    ]
    results = score_hits(hits, ["python", "ml"], None, top_k=10)
    assert results[0].resource_id == "b"
    assert results[1].resource_id == "a"


def test_score_hits_respects_weights():
    hits = [
        [_hit("a", "skills", "ta", ["python"], 0.2), _hit("b", "skills", "tb", ["python"], 1.0)],
    ]
    results = score_hits(hits, ["python"], [10.0], top_k=10)
    assert results[0].resource_id == "b"


def test_score_hits_attaches_person_metadata_from_best_chunk():
    hits = [
        [
            ChunkHit(
                resource_id="a",
                section="skills",
                text="Python",
                keywords=["python"],
                similarity=1.0,
                metadata={"resource_name": "Anna", "role": "Engineer", "business_line": "PV"},
            )
        ]
    ]
    results = score_hits(hits, ["python"], None, top_k=10)
    assert results[0].person == {"resource_name": "Anna", "role": "Engineer", "business_line": "PV"}


def test_score_hits_mismatched_weights_raise():
    with pytest.raises(ValueError):
        score_hits([[]], ["python"], [1.0, 2.0])


def test_competence_from_seniority():
    assert competence_from_metadata({"seniority": "Lead"}) == 1.0
    assert competence_from_metadata({"seniority": "junior"}) == 0.25
    assert competence_from_metadata({}) == 0.0


def test_competence_from_years_fallback():
    assert competence_from_metadata({"years_experience": 10}) == 0.5
    assert competence_from_metadata({"years_experience": 5}) == 0.25
    assert competence_from_metadata({"years_experience": 0}) == 0.0


def test_competence_boost_raises_senior_score():
    junior = _hit("r1", "skills", "Python", ["python"], 0.5, rerank=0.5)
    junior.metadata = {"seniority": "Junior"}
    expert = _hit("r2", "skills", "Python", ["python"], 0.5, rerank=0.5)
    expert.metadata = {"seniority": "Lead"}

    base_junior = chunk_score(junior, ["python"], {"skills": 1.0}, alpha=0.8, beta=0.2)
    base_expert = chunk_score(expert, ["python"], {"skills": 1.0}, alpha=0.8, beta=0.2)
    assert base_junior == base_expert

    boost_junior = chunk_score(junior, ["python"], {"skills": 1.0}, alpha=0.8, beta=0.2, competence_weight=0.2)
    boost_expert = chunk_score(expert, ["python"], {"skills": 1.0}, alpha=0.8, beta=0.2, competence_weight=0.2)
    assert boost_expert > boost_junior


def test_competence_boost_off_by_default():
    hit = _hit("r1", "skills", "Python", ["python"], 0.5)
    hit.metadata = {"seniority": "Lead"}
    assert chunk_score(hit, ["python"], {"skills": 1.0}, alpha=0.8, beta=0.2) == pytest.approx(0.6)
