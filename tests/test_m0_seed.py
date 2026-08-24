from pipeline.ids import mint_uid
from pipeline.validate import integrity, quotes, schema
from pipeline.validate.schema import DATA_DIR, load_json


def test_uid_is_stable_for_known_seed_ids():
    assert mint_uid("V1.3.6") == "req-f86fb3ab"
    assert mint_uid("V13.2.4") == "req-3b6e4671"


def test_seed_files_validate():
    assert schema.validate_all() == []
    assert integrity.validate_all() == []
    assert quotes.validate_all() == []


def test_mapping_disagreement_is_recorded():
    v1112 = load_json(DATA_DIR / "requirements" / "V11" / "V11.1.2.json")
    v1324 = load_json(DATA_DIR / "requirements" / "V13" / "V13.2.4.json")
    assert v1112["lineage"]["mapping_entry"]["agrees_with_git"] is False
    assert v1324["lineage"]["mapping_entry"]["agrees_with_git"] is False
    assert v1324["lineage"]["origin_kind"] == "new_in_release"


def test_issue_3338_links_only_known_uids():
    issue = load_json(DATA_DIR / "issues" / "3338.json")
    uids = {rs["requirement_uid"] for rs in issue["requirement_summaries"]}
    assert mint_uid("V2.2.1") in uids
    assert mint_uid("V1.1.1") in uids
    assert mint_uid("V1.5.3") in uids
    assert issue["source"]["has_edits"] is True


def test_human_provenance_on_seed():
    req = load_json(DATA_DIR / "requirements" / "V1" / "V1.3.6.json")
    assert req["status"]["coverage"] == "authored"
    for item in req["summaries"]:
        assert item["provenance"]["origin"] == "human"
        assert item["provenance"]["authors"][0]["github"] == "ryarmst"
        assert item["provenance"]["model"] is None
