from cvengine.db.chroma import build_where


def test_build_where_none_for_empty():
    assert build_where(None) is None
    assert build_where({}) is None


def test_build_where_single_condition():
    assert build_where({"business_line": "PV"}) == {"business_line": "PV"}


def test_build_where_multiple_conditions():
    where = build_where({"business_line": "PV", "role": "Specialist"})
    assert where == {"$and": [{"business_line": "PV"}, {"role": "Specialist"}]}


def test_build_where_ignores_unknown_and_blank():
    assert build_where({"unknown_field": "x", "business_line": ""}) is None
    assert build_where({"unknown_field": "x", "business_line": "PV"}) == {"business_line": "PV"}
