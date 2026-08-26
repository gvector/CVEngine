from cvengine.constants import Section
from cvengine.ingestion.sectioner import CVSectioner, HeadingSectioner, to_cv_sections
from tests.fakes import SECTIONING_OK, FakeLLM


def test_heading_sectioner_splits_synthetic_cv():
    text = """PROFESSIONAL SUMMARY
Senior Data Scientist.

SKILLS
Python pandas NumPy

EDUCATION
MSc Computer Science
"""
    output = HeadingSectioner().structure(text)
    sections = to_cv_sections(output)
    by_section = {s.section: s.text for s in sections}
    assert by_section[Section.SUMMARY] == "Senior Data Scientist."
    assert by_section[Section.SKILLS] == "Python pandas NumPy"
    assert by_section[Section.EDUCATION] == "MSc Computer Science"
    assert output.resource_name is None


def test_heading_sectioner_falls_back_to_other():
    text = "just a flat line\nanother line"
    sections = to_cv_sections(HeadingSectioner().structure(text))
    assert len(sections) == 1
    assert sections[0].section == Section.OTHER


def test_cv_sectioner_parses_valid_json():
    llm = FakeLLM({"CV:": SECTIONING_OK})
    output = CVSectioner(llm).structure("some cv")
    assert output.resource_name == "Anna Rossi"
    assert len(output.sections) == 3
    assert output.sections[0].section == Section.SUMMARY


def test_cv_sectioner_retries_on_invalid_json_then_succeeds():
    llm = FakeLLM({"corrected valid JSON": SECTIONING_OK, "CV:": "{ invalid json"})
    output = CVSectioner(llm).structure("some cv")
    assert output.resource_name == "Anna Rossi"
    assert len(llm.calls) == 2


def test_cv_sectioner_falls_back_after_all_retries():
    llm = FakeLLM({"CV:": "{ invalid json"})
    output = CVSectioner(llm).structure("some cv")
    assert len(output.sections) == 1
    assert output.sections[0].section == Section.OTHER
    assert output.sections[0].text == "some cv"
    assert len(llm.calls) == 3


def test_to_cv_sections_drops_empty_text():
    from cvengine.ingestion.sectioner import SectionEntry, SectioningOutput

    output = SectioningOutput(sections=[SectionEntry(section=Section.SKILLS, text="  ", keywords=[])])
    assert to_cv_sections(output) == []
