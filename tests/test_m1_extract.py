import pytest

from pipeline.asvs import parse_mapping
from pipeline.extract.lineage import extra_ids_for, extract
from pipeline.gitrepo import repo_ready
from pipeline.io import load_json
from pipeline.paths import BUILD_DIR, DATA_DIR, ISSUES_DIR

GOLD_COMMITS = {
    "V1.3.6": ["3b6b57a0", "844285bf", "0bbdd60b", "e86154d4", "35f39a56", "d3a825b4", "104040a5"],
    "V1.3.8": ["a739927d", "9019f849", "43481db4", "d3a825b4"],
    "V1.5.2": ["25783d0a", "0f714f0d", "ae9793bf", "c53b2bc4", "bcc0e5d3", "e36063dc"],
    "V11.1.2": ["fddaa31a", "121e76b7", "c270e676", "64881b54"],
    "V11.1.4": ["90c0053d", "fe13d57a", "b4e61e64"],
    "V13.2.4": ["b6e0dfaf", "60f563df", "e4c9d291"],
    "V13.2.5": ["60f563df", "5aec93ed", "d3a825b4"],
}


@pytest.mark.skipif(not repo_ready(), reason="OWASP/ASVS git cache is not present")
@pytest.mark.parametrize("req_id,commits", GOLD_COMMITS.items())
def test_lineage_recalls_gold_commits(req_id, commits):
    record = load_json(DATA_DIR / "requirements" / req_id.split(".")[0] / f"{req_id}.json")
    mapping = parse_mapping().get(req_id)
    extra = extra_ids_for(record)
    extracted = extract(req_id, record["current"]["text"], mapping, extra)
    found = {event["commit"] for event in extracted["events"]}
    missing = [commit for commit in commits if not any(item.startswith(commit) for item in found)]
    assert missing == [], f"{req_id} missing commits {missing}; found {sorted(found)[:20]}"


@pytest.mark.skipif(not repo_ready(), reason="OWASP/ASVS git cache is not present")
def test_mapping_content_disagreement_for_replaced_slots():
    mapping = parse_mapping()
    v1112 = load_json(DATA_DIR / "requirements" / "V11" / "V11.1.2.json")
    extra = extra_ids_for(v1112)
    extracted = extract("V11.1.2", v1112["current"]["text"], mapping["V11.1.2"], extra)
    assert extracted["agrees_with_git"] is False


def test_issue_archive_is_mirrored():
    snapshots = [path for path in ISSUES_DIR.glob("*.json") if not path.name.endswith(".history.json")]
    stubs = list((DATA_DIR / "issues").glob("*.json"))
    assert len(snapshots) >= 1700
    assert len(stubs) == len(snapshots)
    authored = load_json(DATA_DIR / "issues" / "3338.json")
    assert authored["status"]["coverage"] == "authored"
    assert authored["summaries"]


def test_candidate_links_include_ssrf_issue():
    path = BUILD_DIR / "candidates" / "issue-2115.json"
    if not path.exists():
        pytest.skip("candidate index not built yet")
    data = load_json(path)
    ids = {item["requirement_id"] for item in data["candidates"]}
    assert "V1.3.6" in ids
