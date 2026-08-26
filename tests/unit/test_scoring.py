import pytest

from cvengine.db.schemas import ChunkHit
from cvengine.search.scoring import chunk_score, keyword_overlap, score_hits


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


def test_score_hits_mismatched_weights_raise():
    with pytest.raises(ValueError):
        score_hits([[]], ["python"], [1.0, 2.0])
