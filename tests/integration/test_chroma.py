from cvengine.constants import Section
from cvengine.db.schemas import CVSection, PersonMetadata, ProcessedCV


def _cv(resource_id, text, keywords):
    return ProcessedCV(
        resource_id=resource_id,
        body=text,
        content_hash=f"hash-{resource_id}",
        sections=[
            CVSection(section=Section.SKILLS, text=text, keywords=keywords),
            CVSection(section=Section.SUMMARY, text=text + " summary", keywords=[]),
        ],
        metadata=PersonMetadata(
            resource_id=resource_id,
            resource_name=resource_id,
            business_line="PV",
            role="Specialist",
        ),
    )


def test_upsert_and_query(chroma_repo):
    chroma_repo.upsert_cv(_cv("RES-1", "Python pandas NumPy", ["python", "pandas"]))
    chroma_repo.upsert_cv(_cv("RES-2", "Java Spring Boot", ["java"]))
    assert chroma_repo.count() == 4

    hits = chroma_repo.query_text(["Python"], n_results=5)[0]
    assert hits
    assert hits[0].resource_id == "RES-1"
    assert hits[0].section == "skills"
    assert "python" in [k.lower() for k in hits[0].keywords]


def test_metadata_filter(chroma_repo):
    chroma_repo.upsert_cv(_cv("RES-1", "Python", ["python"]))
    cv2 = _cv("RES-2", "Python", ["python"])
    cv2.metadata.business_line = "GCP"
    chroma_repo.upsert_cv(cv2)

    hits = chroma_repo.query_text(["Python"], n_results=5, where={"business_line": "GCP"})[0]
    assert len(hits) == 2
    assert all(hit.resource_id == "RES-2" for hit in hits)


def test_exists_hash(chroma_repo):
    chroma_repo.upsert_cv(_cv("RES-1", "Python", ["python"]))
    assert chroma_repo.exists_hash("hash-RES-1")
    assert not chroma_repo.exists_hash("hash-unknown")


def test_get_resource_body_orders_chunks(chroma_repo):
    chroma_repo.upsert_cv(_cv("RES-1", "Python", ["python"]))
    body = chroma_repo.get_resource_body("RES-1")
    assert "summary" in body and "Python" in body


def test_get_resource_metadata(chroma_repo):
    chroma_repo.upsert_cv(_cv("RES-1", "Python", ["python"]))
    metadata = chroma_repo.get_resource_metadata("RES-1")
    assert metadata["business_line"] == "PV"
    assert metadata["role"] == "Specialist"
