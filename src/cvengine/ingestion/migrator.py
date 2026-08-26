"""Migrate legacy pickle archives into the Chroma vector store."""

from __future__ import annotations

import logging
import pickle
from pathlib import Path

from cvengine.ingestion.pipeline import IngestionPipeline, IngestionSummary
from cvengine.observability import log_event

logger = logging.getLogger("cvengine")


class _StubPerson:
    """Lightweight stand-in for the legacy Person class during unpickling."""


class _StubSkill:
    """Lightweight stand-in for the legacy Skill class during unpickling."""


class _StubCV:
    """Lightweight stand-in for the legacy CVperson class during unpickling."""

    def __init__(self) -> None:
        self.idx: str = ""
        self.body: str = ""
        self.person: _StubPerson | None = None
        self.skill: _StubSkill | None = None


class _MigratingUnpickler(pickle.Unpickler):
    """Unpickler that maps legacy class paths onto lightweight stubs."""

    _STUBS = {
        ("components.cv", "CVperson"): _StubCV,
        ("components.person", "Person"): _StubPerson,
        ("components.skill", "Skill"): _StubSkill,
    }

    def find_class(self, module: str, name: str) -> type:
        stub = self._STUBS.get((module, name))
        if stub is not None:
            return stub
        return super().find_class(module, name)


def load_legacy_archive(path: str | Path) -> list[_StubCV]:
    """Load a legacy pkl archive as a list of stub CV objects.

    :param path: path to the pickle file
    :return: the list of CVs (or ``None`` if the file holds a collection object)
    """
    with open(path, "rb") as handle:
        data = _MigratingUnpickler(handle).load()

    cvs: list[_StubCV] = []
    if isinstance(data, list):
        cvs = [item for item in data if isinstance(item, _StubCV)]
    elif isinstance(data, dict):
        for key, value in data.items():
            cv = _StubCV()
            cv.idx = str(key)
            if isinstance(value, dict):
                cv.body = value.get("body", "") or value.get("cv", "") or ""
            else:
                cv.body = getattr(value, "body", "")
            cvs.append(cv)
    else:
        raise ValueError(f"Unsupported legacy archive structure: {type(data)}")

    log_event(logger, "legacy archive loaded", count=len(cvs), path=str(path))
    return cvs


def migrate_pkl(
    path: str | Path,
    pipeline: IngestionPipeline,
) -> IngestionSummary:
    """Re-index every CV in a legacy pkl archive through the ingestion pipeline.

    :param path: path to the legacy pickle archive
    :param pipeline: the ingestion pipeline used to re-structure and embed
    :return: the aggregate ingestion summary
    """
    cvs = load_legacy_archive(path)
    results = []
    for cv in cvs:
        extra_metadata: dict = {}
        if cv.person is not None:
            for field in (
                "resource_name",
                "business_line",
                "role",
                "company",
                "email",
                "resume_date",
                "status",
                "y_in_pqe",
                "country_residenza",
                "city_residenza",
                "cv_docx_name",
                "id_db",
            ):
                value = getattr(cv.person, field, None)
                if value is not None:
                    extra_metadata[field] = value
            extra_metadata["source"] = "pkl"
        try:
            result = pipeline.ingest_text(
                text=cv.body,
                resource_id=cv.idx or None,
                extra_metadata=extra_metadata,
            )
        except Exception as exc:  # noqa: BLE001 - per-resource isolation
            log_event(logger, "migration item failed", resource_id=cv.idx, error=str(exc))
            result = type("R", (), {"resource_id": cv.idx or "?", "status": "failed", "chunks": 0})()
        results.append(result)

    counts = {status: 0 for status in ("indexed", "skipped", "failed")}
    for result in results:
        counts[result.status] += 1
    log_event(logger, "pkl migration completed", **counts)
    return IngestionSummary(
        total=len(results),
        indexed=counts["indexed"],
        skipped=counts["skipped"],
        failed=counts["failed"],
        results=[result for result in results if result.status != "indexed"],
    )
