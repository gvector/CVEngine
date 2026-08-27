from cvengine.ingestion.pipeline import IngestionPipeline
from cvengine.ingestion.sectioner import HeadingSectioner
from cvengine.search.enrich import QueryEnricher
from cvengine.search.graph import SearchGraph
from tests.fakes import EXPANSION_OK, FakeLLM


def _ingest(chroma_repo, resources: dict[str, str]):
    pipeline = IngestionPipeline(repo=chroma_repo, sectioner=HeadingSectioner())
    for resource_id, text in resources.items():
        pipeline.ingest_text(text=text, resource_id=resource_id)


def test_graph_full_pipeline_without_rerank(chroma_repo):
    _ingest(
        chroma_repo,
        {
            "RES-PY": "PROFESSIONAL SUMMARY\nPython developer.\n\nSKILLS\nPython pandas NumPy scikit-learn",
            "RES-JAVA": "PROFESSIONAL SUMMARY\nJava developer.\n\nSKILLS\nJava Spring Maven",
            "RES-DS": "PROFESSIONAL SUMMARY\nData scientist.\n\nSKILLS\nPython Machine Learning PyTorch",
        },
    )
    llm = FakeLLM({"Skills:": EXPANSION_OK})
    graph = SearchGraph(
        repo=chroma_repo,
        enricher=QueryEnricher(llm),
        reranker=None,
        top_k_per_query=5,
    )
    state = graph.invoke({"skills": ["Python"], "top_k": 3})
    ids = [result.resource_id for result in state["results"]]
    assert "RES-PY" in ids[:2]
    assert "RES-JAVA" not in ids[:1]


def test_graph_job_description_extracts_skills(chroma_repo):
    _ingest(
        chroma_repo,
        {
            "RES-PY": "PROFESSIONAL SUMMARY\nPython dev.\n\nSKILLS\nPython Flask",
            "RES-NODE": "PROFESSIONAL SUMMARY\nNode dev.\n\nSKILLS\nNode.js JavaScript",
        },
    )
    llm = FakeLLM(
        {
            "Job description:": '{"skills": ["Python"]}',
            "Skills:": EXPANSION_OK,
        }
    )
    graph = SearchGraph(
        repo=chroma_repo,
        enricher=QueryEnricher(llm),
        reranker=None,
        top_k_per_query=5,
    )
    state = graph.invoke({"job_description": "We need a Python backend engineer", "top_k": 3})
    assert state["skills"] == ["Python"]
    assert state["results"][0].resource_id == "RES-PY"


def test_graph_synthesize_runs_when_requested(chroma_repo):
    _ingest(
        chroma_repo,
        {"RES-1": "PROFESSIONAL SUMMARY\nA.\n\nSKILLS\nPython pandas"},
    )
    llm = FakeLLM(
        {
            "Skills:": EXPANSION_OK,
            "Top matching resources:": "Good match on Python.",
        }
    )
    graph = SearchGraph(
        repo=chroma_repo,
        enricher=QueryEnricher(llm),
        reranker=None,
        llm=llm,
        top_k_per_query=5,
    )
    state = graph.invoke({"skills": ["Python"], "top_k": 3, "synthesize": True})
    assert state["explanation"] == "Good match on Python."


class _UnreachableEnricher:
    def extract_skills(self, job_description):
        raise ConnectionError("Ollama is down")

    def expand_queries(self, skills):
        raise ConnectionError("Ollama is down")


def test_graph_degrades_to_base_skills_when_llm_unavailable(chroma_repo):
    _ingest(chroma_repo, {"RES-1": "PROFESSIONAL SUMMARY\nA.\n\nSKILLS\nPython pandas"})
    graph = SearchGraph(
        repo=chroma_repo,
        enricher=_UnreachableEnricher(),  # type: ignore[arg-type]
        reranker=None,
        top_k_per_query=5,
    )
    state = graph.invoke({"skills": ["Python"], "top_k": 3})
    assert state["query_terms"] == ["Python"]
    assert state["results"][0].resource_id == "RES-1"
