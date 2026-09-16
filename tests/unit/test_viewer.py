from fastapi import FastAPI
from fastapi.testclient import TestClient

from cvengine.api.app import create_app
from cvengine.api.viewer import build_viewer_router
from cvengine.config import Settings


class FakeBrowser:
    def list_collections(self):
        return [{"name": "col_a", "count": 3}, {"name": "col_b", "count": 1}]

    def get_chunks(self, collection, limit=20, resource_id=None):
        return [
            {
                "id": "a::0::hash",
                "resource_id": "RES-1",
                "section": "skills",
                "keywords": ["python"],
                "document": "Python pandas",
                "metadata": {"section": "skills", "resource_id": "RES-1"},
            }
        ]

    def query(self, collection, query_text, n_results):
        return [
            {
                "id": "a::0::hash",
                "score": 0.95,
                "resource_id": "RES-1",
                "section": "skills",
                "keywords": ["python"],
                "document": "Python pandas",
                "metadata": {"section": "skills"},
            }
        ]


def _viewer_client():
    app = FastAPI()
    app.include_router(build_viewer_router(FakeBrowser()))
    return TestClient(app)


def test_viewer_index_returns_html():
    client = _viewer_client()
    response = client.get("/viewer")
    assert response.status_code == 200
    assert "Chroma Viewer" in response.text


def test_viewer_collections():
    client = _viewer_client()
    data = client.get("/viewer/api/collections").json()
    assert data == [{"name": "col_a", "count": 3}, {"name": "col_b", "count": 1}]


def test_viewer_chunks():
    client = _viewer_client()
    data = client.get("/viewer/api/chunks", params={"collection": "col_a"}).json()
    assert data[0]["resource_id"] == "RES-1"
    assert data[0]["keywords"] == ["python"]


def test_viewer_query():
    client = _viewer_client()
    data = client.post(
        "/viewer/api/query",
        json={"collection": "col_a", "query_text": "Python", "n_results": 5},
    ).json()
    assert data[0]["score"] == 0.95


def _fake_engine(viewer_enabled: bool):
    settings = Settings()
    settings.viewer_enabled = viewer_enabled
    return type(
        "Engine",
        (),
        {
            "settings": settings,
            "repo": None,
            "ingestion": None,
            "summaries": None,
            "llm": None,
            "graph": None,
            "enricher": None,
            "status": lambda self: {},
        },
    )()


def test_create_app_mounts_viewer_when_enabled():
    engine = _fake_engine(viewer_enabled=True)
    client = TestClient(create_app(engine, viewer=FakeBrowser()))
    assert client.get("/viewer").status_code == 200
    assert client.get("/viewer/api/collections").status_code == 200


def test_create_app_omits_viewer_when_disabled():
    engine = _fake_engine(viewer_enabled=False)
    client = TestClient(create_app(engine, viewer=FakeBrowser()))
    assert client.get("/viewer").status_code == 404
