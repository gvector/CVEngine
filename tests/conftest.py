from __future__ import annotations

import contextlib
import os
import tempfile

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
    """A repository on a throwaway collection, skipped if Chroma is not running."""
    settings = Settings()
    if not _chroma_reachable(settings.chroma.host, settings.chroma.port):
        pytest.skip("Chroma server not reachable; start with `docker compose up -d`")
    collection_name = (
        f"{settings.chroma.test_collection}__pytest__{os.getpid()}__{next(tempfile._get_candidate_names())}"
    )
    repo = ChromaRepository(
        host=settings.chroma.host,
        port=settings.chroma.port,
        collection_name=collection_name,
        provider=fake_provider,
    )
    yield repo
    with contextlib.suppress(Exception):
        repo.reset()
