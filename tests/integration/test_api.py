from fastapi.testclient import TestClient

from cvengine.api.app import create_app
from cvengine.db.schemas import RankedResource
from cvengine.ingestion.pipeline import IngestionResult
from cvengine.services import SummaryStore
from tests.fakes import FakeLLM


class FakeGraph:
    def invoke(self, state):
        return {
            "query_terms": ["Python"],
            "results": [
                RankedResource(
                    resource_id="RES-1",
                    score=0.93,
                    best_chunk="Python expert",
                    skills_hit={"Python": 0.95},
                )
            ],
            "explanation": None,
        }


class FakeIngestion:
    def ingest_text(self, text, resource_id=None):
        return IngestionResult(resource_id=resource_id or "cv_hash", status="indexed", chunks=3)

    def ingest_batch(self, folder):
        return {
            "total": 1,
            "indexed": 1,
            "skipped": 0,
            "failed": 0,
            "results": [],
        }


class FakeRepo:
    def __init__(self) -> None:
        self.metadata = {
            "resource_id": "RES-1",
            "business_line": "PV",
            "role": "Specialist",
        }
        self.body = "Some body"

    def get_resource_metadata(self, resource_id):
        return self.metadata if resource_id == "RES-1" else None

    def get_resource_body(self, resource_id):
        return self.body if resource_id == "RES-1" else None


def _client(tmp_path):
    engine = type(
        "Engine",
        (),
        {
            "repo": FakeRepo(),
            "ingestion": FakeIngestion(),
            "enricher": None,
            "summaries": SummaryStore(tmp_path),
            "llm": FakeLLM({"CV:": "Summary text."}),
            "graph": FakeGraph(),
            "settings": None,
            "status": lambda self: {"chroma": {"reachable": True, "resources": 1}},
        },
    )()
    return TestClient(create_app(engine))


def test_search_endpoint(tmp_path):
    client = _client(tmp_path)
    response = client.post("/v1/search", json={"skills": ["Python"], "top_k": 5})
    assert response.status_code == 200
    data = response.json()
    assert data["results"][0]["resource_id"] == "RES-1"
    assert data["query_terms"] == ["Python"]


def test_search_requires_input(tmp_path):
    client = _client(tmp_path)
    response = client.post("/v1/search", json={"skills": [], "job_description": None})
    assert response.status_code == 400


def test_ingest_cv_endpoint(tmp_path):
    client = _client(tmp_path)
    response = client.post("/v1/cvs", json={"text": "some cv", "resource_id": "RES-2"})
    assert response.status_code == 200
    assert response.json()["status"] == "indexed"


def test_get_cv_not_found(tmp_path):
    client = _client(tmp_path)
    response = client.get("/v1/cvs/NOPE")
    assert response.status_code == 404


def test_summary_endpoint_caches(tmp_path):
    client = _client(tmp_path)
    first = client.get("/v1/cvs/RES-1/summary")
    assert first.status_code == 200
    second = client.get("/v1/cvs/RES-1/summary")
    assert second.json() == first.json()


def test_status_endpoint(tmp_path):
    client = _client(tmp_path)
    response = client.get("/v1/status")
    assert response.status_code == 200
    assert response.json()["chroma"]["reachable"] is True
