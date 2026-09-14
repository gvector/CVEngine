from __future__ import annotations

import contextlib

import pytest

from cvengine.config import Settings
from cvengine.db.chroma import ChromaRepository
from cvengine.observability import setup_logging

setup_logging()


@pytest.fixture
def fake_provider():
    from tests.fakes import FakeEmbeddingProvider

    return FakeEmbeddingProvider()


@pytest.fixture
def tmp_data_dir(tmp_path):
    return tmp_path


@pytest.fixture
def settings(tmp_data_dir):
    return Settings(data_dir=str(tmp_data_dir), log_level="ERROR")


def _chroma_reachable(host: str, port: int) -> bool:
    import chromadb

    try:
        client = chromadb.HttpClient(host=host, port=port)
        client.heartbeat()
        return True
    except Exception:
        return False


@pytest.fixture
def chroma_repo(fake_provider):
    """A repository on a fixed throwaway collection, skipped if Chroma is not running.

    A single collection name is reused and recreated fresh before every test to
    avoid create/delete churn that makes the Chroma server flaky.
    """
    settings = Settings()
    if not _chroma_reachable(settings.chroma.host, settings.chroma.port):
        pytest.skip("Chroma server not reachable; start with `docker compose up -d`")
    name = f"{settings.chroma.test_collection}__pytest"
    repo = ChromaRepository(
        host=settings.chroma.host,
        port=settings.chroma.port,
        collection_name=name,
        provider=fake_provider,
    )
    with contextlib.suppress(Exception):
        repo.reset()
    repo = ChromaRepository(
        host=settings.chroma.host,
        port=settings.chroma.port,
        collection_name=name,
        provider=fake_provider,
    )
    yield repo
    with contextlib.suppress(Exception):
        repo.reset()
