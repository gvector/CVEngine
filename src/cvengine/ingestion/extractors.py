"""Text extraction from CV file formats and raw text."""

from __future__ import annotations

import logging
from pathlib import Path

import docx2txt
from pypdf import PdfReader

from cvengine.observability import log_event

logger = logging.getLogger("cvengine")

SUPPORTED_EXTENSIONS = {".docx", ".txt", ".pdf"}


class ExtractionError(RuntimeError):
    """Raised when a CV document cannot be converted to text."""


class TextExtractor:
    """Extract plain text from docx, txt, pdf files or raw strings."""

    def extract_file(self, path: str | Path) -> str:
        """Extract text from a single file by extension.

        :param path: path to the CV document
        :return: the extracted plain text
        :raises ExtractionError: for unsupported formats or conversion failures
        """
        file_path = Path(path)
        suffix = file_path.suffix.lower()
        if suffix == ".docx":
            text = self._from_docx(file_path)
        elif suffix == ".txt":
            text = self._from_txt(file_path)
        elif suffix == ".pdf":
            text = self._from_pdf(file_path)
        else:
            raise ExtractionError(f"Unsupported file format: {suffix}")

        if not text.strip():
            raise ExtractionError(f"Empty text extracted from {file_path.name}")
        log_event(logger, "text extracted", file=file_path.name, length=len(text))
        return text

    def extract_text(self, text: str) -> str:
        """Validate and normalize a raw text input."""
        if not text or not text.strip():
            raise ExtractionError("Empty text provided")
        return text.strip()

    @staticmethod
    def _from_docx(path: Path) -> str:
        try:
            return docx2txt.process(str(path))
        except Exception as exc:  # noqa: BLE001 - surface any docx2txt failure
            raise ExtractionError(f"Failed to extract {path.name}: {exc}") from exc

    @staticmethod
    def _from_txt(path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:  # noqa: BLE001
            raise ExtractionError(f"Failed to read {path.name}: {exc}") from exc

    @staticmethod
    def _from_pdf(path: Path) -> str:
        try:
            reader = PdfReader(str(path))
            pages = [page.extract_text() or "" for page in reader.pages]
            return "\n".join(pages)
        except Exception as exc:  # noqa: BLE001
            raise ExtractionError(f"Failed to extract {path.name}: {exc}") from exc
