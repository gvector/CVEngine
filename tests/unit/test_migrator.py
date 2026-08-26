import pickle

from cvengine.ingestion.migrator import (
    _MigratingUnpickler,
    _StubCV,
    _StubPerson,
    load_legacy_archive,
)


def test_find_class_maps_legacy_paths_to_stubs():
    unpickler = _MigratingUnpickler.__new__(_MigratingUnpickler)
    assert unpickler.find_class("components.cv", "CVperson") is _StubCV
    assert unpickler.find_class("components.person", "Person") is _StubPerson


def test_roundtrip_stub_cv(tmp_path):
    cv = _StubCV()
    cv.idx = "ROD"
    cv.body = "body text"
    cv.person = _StubPerson()
    cv.person.resource_name = "Rossi"

    path = tmp_path / "archive.pkl"
    with open(path, "wb") as handle:
        pickle.dump([cv], handle)

    loaded = load_legacy_archive(path)
    assert len(loaded) == 1
    assert loaded[0].idx == "ROD"
    assert loaded[0].body == "body text"
    assert loaded[0].person.resource_name == "Rossi"


def test_load_dict_archive(tmp_path):
    path = tmp_path / "dict.pkl"
    with open(path, "wb") as handle:
        pickle.dump({"RES-1": {"body": "text", "other": 1}}, handle)
    loaded = load_legacy_archive(path)
    assert loaded[0].idx == "RES-1"
    assert loaded[0].body == "text"
