from cvengine.synthetic import (
    BRANCHES,
    LEVEL_ORDER,
    build_cv_text,
    build_manifest,
    generate_batch,
    generate_profiles,
    profile_metadata,
)
from cvengine.synthetic.domain import LEVEL_PROFILES, Level, branches_by_code


def test_generate_profiles_is_deterministic():
    assert generate_profiles(30, seed=7) == generate_profiles(30, seed=7)


def test_generate_profiles_count_and_fields():
    profiles = generate_profiles(20, seed=1)
    assert len(profiles) == 20
    assert all(profile.resource_id.startswith("SYN-") for profile in profiles)
    assert all(profile.branch in branches_by_code() for profile in profiles)
    assert all(profile.primary_skills for profile in profiles)
    assert all(profile.level in LEVEL_PROFILES for profile in profiles)


def test_primary_skills_come_from_role_cluster():
    role_skills = {(branch.code, role.name): set(role.primary_skills) for branch in BRANCHES for role in branch.roles}
    for profile in generate_profiles(60, seed=3):
        assert set(profile.primary_skills) <= role_skills[(profile.branch, profile.role)]


def test_all_branches_and_levels_represented():
    profiles = generate_profiles(400, seed=42)
    assert {profile.branch for profile in profiles} == {branch.code for branch in BRANCHES}
    assert {profile.level for profile in profiles} == set(Level)


def test_professional_profiles_have_more_skills_than_juniors():
    profiles = generate_profiles(400, seed=42)
    low = [len(p.primary_skills) for p in profiles if p.level == Level.LOW]
    pro = [len(p.primary_skills) for p in profiles if p.level == Level.PROFESSIONAL]
    assert min(pro) >= max(low)


def test_build_cv_text_contains_sections_and_skills():
    profile = generate_profiles(1, seed=1)[0]
    text = build_cv_text(profile)
    assert "PROFESSIONAL SUMMARY" in text
    assert "SKILLS" in text
    assert profile.primary_skills[0] in text
    assert profile.seniority in text


def test_build_cv_text_encodes_level_via_experience_verbs():
    professional = next(p for p in generate_profiles(400, seed=42) if p.level == Level.PROFESSIONAL)
    text = build_cv_text(professional).lower()
    assert any(verb in text for verb in LEVEL_PROFILES[Level.PROFESSIONAL].verbs)


def test_generate_batch_pairs_profiles_with_text():
    batch = generate_batch(5, seed=2)
    assert len(batch) == 5
    for profile, text in batch:
        assert profile.primary_skills[0] in text


def test_profile_metadata_maps_branch():
    profile = generate_profiles(1, seed=1)[0]
    metadata = profile_metadata(profile)
    assert metadata["business_line"] == profile.branch
    assert metadata["role"] == profile.role
    assert metadata["source"] == "synthetic"


def test_build_manifest_structure():
    profiles = generate_profiles(10, seed=5)
    manifest = build_manifest(profiles, seed=5)
    assert manifest["count"] == 10
    assert manifest["seed"] == 5
    assert manifest["levels"] == {level.value: LEVEL_ORDER[level] for level in Level}
    assert len(manifest["resources"]) == 10
    assert "primary_skills" in manifest["resources"][0]
