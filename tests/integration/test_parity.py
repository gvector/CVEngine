"""Parity test: synthetic CVs with known skills must rank first for their skills."""

from cvengine.ingestion.pipeline import IngestionPipeline
from cvengine.ingestion.sectioner import HeadingSectioner
from cvengine.search.graph import SearchGraph
from cvengine.synthetic.generator import generate_batch, generate_profiles


def test_parity_known_skills_rank_on_top(chroma_repo):
    profiles = generate_profiles(30, seed=42)
    pipeline = IngestionPipeline(repo=chroma_repo, sectioner=HeadingSectioner())
    for profile, text in generate_batch(30, seed=42):
        pipeline.ingest_text(text=text, resource_id=profile.resource_id)

    graph = SearchGraph(
        repo=chroma_repo,
        enricher=None,  # no expansion: strict per-skill parity check
        top_k_per_query=20,
    )

    hit_count = 0
    for profile in profiles:
        primary = profile.skills[0]
        state = graph.invoke({"skills": [primary], "top_k": 10})
        ids = [result.resource_id for result in state["results"]]
        if profile.resource_id in ids:
            hit_count += 1

    assert hit_count / len(profiles) >= 0.6, f"Only {hit_count}/{len(profiles)} known-skill CVs ranked in the top 10"
