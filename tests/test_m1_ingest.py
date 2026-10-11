from pipeline.asvs import parse_mapping, parse_v4_mapping, slugify, unique_slug
from pipeline.ids import mint_uid
from pipeline.io import load_json
from pipeline.paths import DATA_DIR
from pipeline.records import is_protected


def test_all_v5_requirements_imported():
    files = list((DATA_DIR / "requirements").glob("*/*.json"))
    assert len(files) == 345
    uids = [load_json(path)["uid"] for path in files]
    assert len(set(uids)) == 345
    assert mint_uid("V1.3.6") == "req-f86fb3ab"
    assert (DATA_DIR / "requirements" / "V1" / "V1.3.6.json").exists()


def test_authored_seed_not_regressed():
    req = load_json(DATA_DIR / "requirements" / "V1" / "V1.3.6.json")
    assert req["status"]["coverage"] == "authored"
    assert req["slug"] == "ssrf-allowlist-validation"
    assert any(item["kind"] == "origin" for item in req["summaries"])
    assert is_protected(req)
    issue = load_json(DATA_DIR / "issues" / "3338.json")
    assert issue["status"]["coverage"] == "authored"


def test_mapping_parsed():
    mapping = parse_mapping()
    assert mapping["V1.3.6"]["status"] == "MODIFIED"
    assert "V5.2.6" in mapping["V1.3.6"]["v4_ids"]
    assert mapping["V1.3.8"]["status"] == "ADDED"


def test_v4_mapping_includes_deletions_and_ssrf_move():
    mapping = parse_v4_mapping()
    assert mapping["V5.2.6"]["status"] == "MODIFIED"
    assert "V1.3.6" in mapping["V5.2.6"]["v5_ids"]
    assert mapping["V1.1.1"]["status"] == "DELETED"
    assert mapping["V4.3.3"]["v5_ids"] == ["V13.2.4"]


def test_slugify_is_stable_and_unique():
    taken: set[str] = set()
    first = unique_slug("Verify that the application protects against SSRF attacks", "V1.3.6", taken)
    second = unique_slug("Verify that the application protects against SSRF attacks", "V9.1.1", taken)
    assert first != second
    assert slugify("Verify that the application protects against SSRF attacks", "V1.3.6").startswith(
        "protects-against-ssrf"
    )
