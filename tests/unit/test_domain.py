from cvengine.synthetic.domain import (
    BRANCHES,
    LEVEL_ORDER,
    LEVEL_PROFILES,
    Level,
    all_role_cells,
    branches_by_code,
)


def test_six_branches_with_three_roles_each():
    assert len(BRANCHES) == 6
    assert all(len(branch.roles) == 3 for branch in BRANCHES)
    assert len(all_role_cells()) == 18


def test_branch_codes_unique():
    codes = [branch.code for branch in BRANCHES]
    assert len(codes) == len(set(codes))


def test_every_role_has_enough_primary_skills():
    for branch in BRANCHES:
        for role in branch.roles:
            assert len(role.primary_skills) >= 4, f"{branch.code}/{role.name} has too few skills"


def test_four_levels_ordered():
    assert set(LEVEL_PROFILES) == set(Level)
    assert [LEVEL_ORDER[level] for level in Level] == [1, 2, 3, 4]
    years = [LEVEL_PROFILES[level].years_min for level in Level]
    assert years == sorted(years)
    skills = [LEVEL_PROFILES[level].primary_skills[0] for level in Level]
    assert skills == sorted(skills)


def test_branches_by_code_lookup():
    lookup = branches_by_code()
    assert lookup["TECH"].name == "Technology & Digital"
    assert len(lookup) == 6
