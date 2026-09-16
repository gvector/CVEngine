from cvengine.cli.main import ndcg_at_k


def test_ndcg_perfect_ranking():
    assert ndcg_at_k([4, 3, 2, 1], k=4) == 1.0


def test_ndcg_worst_ranking_below_one():
    value = ndcg_at_k([1, 2, 3, 4], k=4)
    assert 0.0 < value < 1.0


def test_ndcg_empty_is_zero():
    assert ndcg_at_k([], k=10) == 0.0


def test_ndcg_penalizes_lower_positions():
    better = ndcg_at_k([4, 3, 1, 1], k=4)
    worse = ndcg_at_k([1, 1, 4, 3], k=4)
    assert better > worse
