from cvengine.db.schemas import ProcessedCV
from cvengine.ingestion.pipeline import IngestionPipeline
from cvengine.ingestion.sectioner import HeadingSectioner


class FakeRepo:
    def __init__(self) -> None:
        self.stored: list[ProcessedCV] = []
        self.hashes: set[str] = set()

    def exists_hash(self, content_hash: str) -> bool:
        return content_hash in self.hashes

    def upsert_cv(self, cv: ProcessedCV) -> int:
        self.stored.append(cv)
        self.hashes.add(cv.content_hash)
        return len(cv.sections)


def _pipeline():
    return IngestionPipeline(repo=FakeRepo(), sectioner=HeadingSectioner())


CV_TEXT = """PROFESSIONAL SUMMARY
Experienced engineer.

SKILLS
Python pandas

EXPERIENCE
Built pipelines.
"""


def test_content_hash_is_stable():
    pipeline = _pipeline()
    assert pipeline.content_hash("Some text") == pipeline.content_hash("Some text")
    assert pipeline.content_hash("Some text") != pipeline.content_hash("Other text")


def test_ingest_text_indexes_and_dedupes():
    pipeline = _pipeline()
    first = pipeline.ingest_text(CV_TEXT, resource_id="RES-1")
    assert first.status == "indexed"
    second = pipeline.ingest_text(CV_TEXT, resource_id="RES-1")
    assert second.status == "skipped"
    assert len(pipeline._repo.stored) == 1  # type: ignore[attr-defined]


def test_ingest_text_merges_metadata():
    pipeline = _pipeline()
    pipeline.ingest_text(
        CV_TEXT,
        resource_id="RES-2",
        extra_metadata={"business_line": "PV", "role": "Engineer", "source": "pkl"},
    )
    stored = pipeline._repo.stored[0]  # type: ignore[attr-defined]
    assert stored.metadata.business_line == "PV"
    assert stored.metadata.role == "Engineer"
    assert stored.metadata.source == "pkl"


def test_ingest_derives_resource_id_from_hash_when_missing():
    pipeline = _pipeline()
    result = pipeline.ingest_text(CV_TEXT)
    assert result.status == "indexed"
    assert result.resource_id.startswith("cv_")


def test_ingest_batch_skips_unsupported_files(tmp_path):
    (tmp_path / "notes.md").write_text("not a cv")
    pipeline = _pipeline()
    summary = pipeline.ingest_batch(tmp_path)
    assert summary.total == 0


def test_ingest_batch_processes_txt_files(tmp_path):
    (tmp_path / "cv1.txt").write_text(CV_TEXT)
    (tmp_path / "cv2.txt").write_text(CV_TEXT.replace("Python", "Java"))
    pipeline = _pipeline()
    summary = pipeline.ingest_batch(tmp_path)
    assert summary.total == 2
    assert summary.indexed == 2
