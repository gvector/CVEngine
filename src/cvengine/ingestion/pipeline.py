"""Ingestion pipeline: source -> sections -> embeddings -> Chroma."""

from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path

from pydantic import BaseModel

from cvengine.db.chroma import ChromaRepository
from cvengine.db.schemas import PersonMetadata, ProcessedCV
from cvengine.ingestion.extractors import SUPPORTED_EXTENSIONS, TextExtractor
from cvengine.ingestion.sectioner import CVSectioner, to_cv_sections
from cvengine.observability import log_event, timeit

logger = logging.getLogger("cvengine")

_WS = re.compile(r"\s+")


class IngestionResult(BaseModel):
    """Outcome of ingesting a single resource."""

    resource_id: str
    status: str
    chunks: int = 0
    error: str | None = None


class IngestionSummary(BaseModel):
    """Aggregate outcome of a batch ingestion."""

    total: int
    indexed: int
    skipped: int
    failed: int
    results: list[IngestionResult]


class IngestionPipeline:
    """Orchestrates the full ingestion flow for text, files and folders."""

    def __init__(
        self,
        repo: ChromaRepository,
        sectioner: CVSectioner,
        extractor: TextExtractor | None = None,
    ) -> None:
        self._repo = repo
        self._sectioner = sectioner
        self._extractor = extractor or TextExtractor()

    @staticmethod
    def content_hash(text: str) -> str:
        """Compute a stable content hash of a CV body for idempotency."""
        normalized = _WS.sub(" ", text.strip()).lower()
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @timeit("ingest_text")
    def ingest_text(
        self,
        text: str,
        resource_id: str | None = None,
        extra_metadata: dict | None = None,
    ) -> IngestionResult:
        """Ingest a raw CV text string.

        :param text: the CV body
        :param resource_id: optional explicit resource id
        :param extra_metadata: authoritative person fields (e.g. from a pkl migration)
        :return: the ingestion outcome
        """
        return self._ingest(
            text=self._extractor.extract_text(text),
            resource_id=resource_id,
            extra_metadata=extra_metadata,
        )

    @timeit("ingest_file")
    def ingest_file(
        self,
        path: str | Path,
        resource_id: str | None = None,
        extra_metadata: dict | None = None,
    ) -> IngestionResult:
        """Ingest a single CV document from disk.

        :param path: path to a docx/txt/pdf file
        :param resource_id: optional explicit resource id
        :param extra_metadata: authoritative person fields
        :return: the ingestion outcome
        """
        file_path = Path(path)
        fallback_id = re.sub(r"[^A-Za-z0-9_.-]", "_", file_path.stem)
        return self._ingest(
            text=self._extractor.extract_file(file_path),
            resource_id=resource_id or fallback_id,
            extra_metadata=extra_metadata,
        )

    @timeit("ingest_batch")
    def ingest_batch(self, folder: str | Path) -> IngestionSummary:
        """Ingest every supported CV file inside a folder.

        :param folder: directory containing CV documents
        :return: aggregate ingestion summary
        """
        folder_path = Path(folder)
        if not folder_path.is_dir():
            raise FileNotFoundError(f"Not a directory: {folder_path}")

        files = sorted(p for p in folder_path.iterdir() if p.suffix.lower() in SUPPORTED_EXTENSIONS)
        results: list[IngestionResult] = []
        for file_path in files:
            try:
                results.append(self.ingest_file(file_path))
            except Exception as exc:  # noqa: BLE001 - per-file isolation
                log_event(
                    logger,
                    "batch item failed",
                    file=str(file_path),
                    error=str(exc),
                )
                results.append(
                    IngestionResult(
                        resource_id=file_path.name,
                        status="failed",
                        error=str(exc),
                    )
                )

        counts = {status: 0 for status in ("indexed", "skipped", "failed")}
        for result in results:
            counts[result.status] += 1
        log_event(logger, "batch completed", **counts)
        return IngestionSummary(
            total=len(results),
            indexed=counts["indexed"],
            skipped=counts["skipped"],
            failed=counts["failed"],
            results=results,
        )

    def _ingest(
        self,
        text: str,
        resource_id: str | None,
        extra_metadata: dict | None,
    ) -> IngestionResult:
        extra_metadata = extra_metadata or {}
        content_hash = self.content_hash(text)

        if self._repo.exists_hash(content_hash):
            log_event(logger, "cv already indexed, skipping", hash=content_hash[:12])
            return IngestionResult(
                resource_id=resource_id or f"cv_{content_hash[:12]}",
                status="skipped",
            )

        sectioning = self._sectioner.structure(text)
        sections = to_cv_sections(sectioning)

        metadata = self._merge_metadata(
            resource_id=resource_id or f"cv_{content_hash[:12]}",
            content_hash=content_hash,
            sectioning=sectioning,
            extra_metadata=extra_metadata,
        )
        cv = ProcessedCV(
            resource_id=metadata.resource_id,
            body=text,
            content_hash=content_hash,
            sections=sections,
            metadata=metadata,
        )
        chunks = self._repo.upsert_cv(cv)
        return IngestionResult(
            resource_id=cv.resource_id,
            status="indexed",
            chunks=chunks,
        )

    def _merge_metadata(
        self,
        resource_id: str,
        content_hash: str,
        sectioning,
        extra_metadata: dict,
    ) -> PersonMetadata:
        """Merge authoritative (SQL/pkl) metadata with LLM-extracted fields."""
        fields = {
            "resource_id": resource_id,
            "resource_name": None,
            "role": None,
            "business_line": None,
            "company": None,
            "email": None,
            "resume_date": None,
            "status": None,
            "y_in_pqe": None,
            "country_residenza": None,
            "city_residenza": None,
            "cv_docx_name": None,
            "id_db": None,
            "seniority": None,
            "years_experience": None,
            "languages": [],
            "certifications": [],
            "source": "text",
        }
        for key in fields:
            if key in extra_metadata and extra_metadata[key] is not None:
                fields[key] = extra_metadata[key]

        if fields["resource_name"] is None and sectioning.resource_name:
            fields["resource_name"] = sectioning.resource_name
        if fields["role"] is None and sectioning.role:
            fields["role"] = sectioning.role
        if fields["business_line"] is None and sectioning.business_line:
            fields["business_line"] = sectioning.business_line
        if fields["seniority"] is None and sectioning.seniority:
            fields["seniority"] = sectioning.seniority
        if fields["years_experience"] is None and sectioning.years_experience is not None:
            fields["years_experience"] = sectioning.years_experience
        if not fields["languages"] and sectioning.languages:
            fields["languages"] = sectioning.languages
        if not fields["certifications"] and sectioning.certifications:
            fields["certifications"] = sectioning.certifications

        return PersonMetadata.model_validate(fields)
