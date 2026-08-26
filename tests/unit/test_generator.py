from cvengine.synthetic.generator import (
    BUSINESS_LINES,
    SKILL_POOL,
    build_cv_text,
    generate_batch,
    generate_profiles,
)


def test_generate_profiles_is_deterministic():
    first = generate_profiles(20, seed=7)
    second = generate_profiles(20, seed=7)
    assert first == second


def test_generate_profiles_count_and_fields():
    profiles = generate_profiles(10, seed=1)
    assert len(profiles) == 10
    assert all(profile.resource_id for profile in profiles)
    assert all(profile.business_line in BUSINESS_LINES for profile in profiles)
    assert all(profile.skills for profile in profiles)


def test_skills_come_from_pool():
    pool_skills = {skill for group in SKILL_POOL.values() for skill in group}
    profiles = generate_profiles(5, seed=3)
    for profile in profiles:
        assert set(profile.skills) <= pool_skills


def test_build_cv_text_contains_skills():
    profile = generate_profiles(1, seed=1)[0]
    text = build_cv_text(profile)
    assert "PROFESSIONAL SUMMARY" in text
    assert profile.skills[0] in text


def test_generate_batch_pairs_profiles_with_text():
    batch = generate_batch(5, seed=2)
    assert len(batch) == 5
    for profile, text in batch:
        assert profile.skills[0] in text
