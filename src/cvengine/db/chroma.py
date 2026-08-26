"""Chroma vector store repository."""

from __future__ import annotations

import json
import logging
from typing import Any

import chromadb
from chromadb.api.models.Collection import Collection

from cvengine.db.schemas import ChunkHit, ProcessedCV
from cvengine.embeddings.functions import NomicEmbeddingFunction
from cvengine.embeddings.provider import EmbeddingProvider
from cvengine.observability import log_event, timeit

logger = logging.getLogger("cvengine")

METADATA_KEYS = (
    "resource_id",
    "resource_name",
    "role",
    "company",
    "business_line",
    "email",
    "resume_date",
    "status",
    "y_in_pqe",
    "country_residenza",
    "city_residenza",
    "cv_docx_name",
    "id_db",
    "seniority",
    "years_experience",
    "source",
)


class ChromaRepository:
    """Repository over a versioned Chroma collection of CV chunks."""

    def __init__(
        self,
        host: str,
        port: int,
        collection_name: str,
        provider: EmbeddingProvider,
    ) -> None:
        self._client = chromadb.HttpClient(host=host, port=port)
        self._provider = provider
        self._collection: Collection | None = None
        self.collection_name = collection_name

    @property
    def _col(self) -> Collection:
        """Lazily bind the collection; the first call requires a live server."""
        if self._collection is None:
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=NomicEmbeddingFunction(self._provider),
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    def exists_hash(self, content_hash: str) -> bool:
        """Check whether a content hash is already indexed."""
        result = self._col.get(where={"content_hash": content_hash}, limit=1, include=[])
        return len(result["ids"]) > 0

    @timeit("chroma_upsert")
    def upsert_cv(self, cv: ProcessedCV) -> int:
        """Store every section of a processed CV as an indexed chunk.

        :param cv: the processed CV to persist
        :return: the number of stored chunks
        """
        if not cv.sections:
            log_event(logger, "cv has no sections, skipping", resource_id=cv.resource_id)
            return 0

        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[dict[str, Any]] = []

        for index, section in enumerate(cv.sections):
            ids.append(f"{cv.resource_id}::{index}::{cv.content_hash[:12]}")
            documents.append(section.text)
            metadata: dict[str, Any] = {
                "section": section.section.value,
                "keywords": json.dumps(section.keywords, ensure_ascii=False),
                "content_hash": cv.content_hash,
                "chunk_order": index,
            }
            for key in METADATA_KEYS:
                value = getattr(cv.metadata, key, None)
                if value is not None:
                    metadata[key] = value
            metadatas.append(metadata)

        embeddings = self._provider.embed_documents(documents)
        self._col.upsert(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)
        log_event(
            logger,
            "cv indexed",
            resource_id=cv.resource_id,
            chunks=len(documents),
            collection=self.collection_name,
        )
        return len(documents)

    def query(
        self,
        query_embeddings: list[list[float]],
        n_results: int,
        where: dict[str, Any] | None = None,
    ) -> list[list[ChunkHit]]:
        """Run a batch of vector queries against the collection.

        :param query_embeddings: one embedding per query
        :param n_results: number of chunks to retrieve per query
        :param where: optional metadata filter passed to Chroma
        :return: hits grouped by query
        """
        result = self._col.query(
            query_embeddings=query_embeddings,
            n_results=n_results,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        return self._parse_query_result(result)

    def query_text(
        self,
        queries: list[str],
        n_results: int,
        where: dict[str, Any] | None = None,
    ) -> list[list[ChunkHit]]:
        """Embed and query a list of raw query strings."""
        embeddings = [self._provider.embed_query(q) for q in queries]
        return self.query(query_embeddings=embeddings, n_results=n_results, where=where)

    @staticmethod
    def _parse_query_result(result: dict[str, Any]) -> list[list[ChunkHit]]:
        ids = result.get("ids", [])
        documents = result.get("documents", [])
        metadatas = result.get("metadatas", [])
        distances = result.get("distances", [])

        grouped: list[list[ChunkHit]] = []
        for i, query_ids in enumerate(ids):
            hits: list[ChunkHit] = []
            for j, chunk_id in enumerate(query_ids):
                meta = (metadatas[i][j] if i < len(metadatas) else {}) or {}
                distance = distances[i][j] if i < len(distances) else 1.0
                keywords_raw = meta.get("keywords", "[]")
                keywords: list[str] = []
                if isinstance(keywords_raw, str):
                    try:
                        keywords = json.loads(keywords_raw)
                    except json.JSONDecodeError:
                        keywords = []
                hits.append(
                    ChunkHit(
                        resource_id=meta.get("resource_id", chunk_id.split("::")[0]),
                        section=meta.get("section", "other"),
                        text=documents[i][j] if i < len(documents) else "",
                        keywords=keywords,
                        similarity=1.0 - float(distance),
                    )
                )
            grouped.append(hits)
        return grouped

    def get_resource_ids(self) -> list[str]:
        """Return the distinct indexed resource ids."""
        result = self._col.get(include=[])
        seen: set[str] = set()
        for chunk_id in result["ids"]:
            seen.add(chunk_id.split("::")[0])
        return sorted(seen)

    def get_resource_chunks(self, resource_id: str) -> list[tuple[int, str, dict[str, Any]]]:
        """Return the ordered chunks of a resource.

        :param resource_id: the resource identifier
        :return: list of ``(order, text, metadata)`` tuples sorted by insertion order
        """
        result = self._col.get(
            where={"resource_id": resource_id},
            include=["documents", "metadatas"],
        )
        chunks: list[tuple[int, str, dict[str, Any]]] = []
        for text, meta in zip(result["documents"], result["metadatas"], strict=True):
            order = int(meta.get("chunk_order", 0)) if meta else 0
            chunks.append((order, text, meta or {}))
        chunks.sort(key=lambda item: item[0])
        return chunks

    def get_resource_metadata(self, resource_id: str) -> dict[str, Any] | None:
        """Return the first chunk metadata of a resource, if present."""
        chunks = self.get_resource_chunks(resource_id)
        if not chunks:
            return None
        return chunks[0][2]

    def get_resource_body(self, resource_id: str) -> str | None:
        """Reconstruct a resource body from its ordered sections."""
        chunks = self.get_resource_chunks(resource_id)
        if not chunks:
            return None
        return "\n\n".join(text for _, text, _ in chunks)

    def count(self) -> int:
        """Return the number of indexed chunks."""
        return self._col.count()

    def reset(self) -> None:
        """Delete the underlying collection entirely."""
        self._client.delete_collection(self.collection_name)
