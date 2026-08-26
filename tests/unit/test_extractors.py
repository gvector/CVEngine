import pytest

from cvengine.ingestion.extractors import ExtractionError, TextExtractor


def test_extract_text_ok():
    extractor = TextExtractor()
    assert extractor.extract_text("  hello  ") == "hello"


def test_extract_text_empty_raises():
    with pytest.raises(ExtractionError):
        TextExtractor().extract_text("   ")


def test_extract_txt(tmp_path):
    path = tmp_path / "cv.txt"
    path.write_text("Plain text CV", encoding="utf-8")
    assert TextExtractor().extract_file(path) == "Plain text CV"


def test_extract_unsupported_extension(tmp_path):
    path = tmp_path / "cv.odt"
    path.write_text("x")
    with pytest.raises(ExtractionError, match="Unsupported"):
        TextExtractor().extract_file(path)


def test_extract_missing_file_raises(tmp_path):
    with pytest.raises(ExtractionError):
        TextExtractor().extract_file(tmp_path / "nope.docx")
