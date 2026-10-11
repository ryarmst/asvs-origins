import copy

from pipeline.build.index import build
from pipeline.build.search import build_search
from pipeline.enrich import enrich_record
from pipeline.io import load_json
from pipeline.mapping import alignment_report
from pipeline.paths import BUILD_DIR, DATA_DIR
from pipeline.review import apply_action, artifacts, validate_record
from pipeline.walk import origin_counts


def test_index_includes_legacy_redirect_and_v9():
    coverage = build()
    index_dir = BUILD_DIR / "index"
    uid_map = load_json(index_dir / "uid-map.json")
    assert uid_map["V1.3.6"].startswith("req-")
    assert uid_map["V1.3.6"] == uid_map["req-f86fb3ab"]
    legacy = load_json(index_dir / "legacy.json")
    assert legacy["4.0.3"]["5.2.6"]["id"] == "V1.3.6"
    assert legacy["4.0.3"]["V5.2.6"]["id"] == "V1.3.6"
    assert coverage["requirements"]["total"] == 345
    assert "human" in coverage["provenance_mix"]
    chapters = load_json(index_dir / "chapters.json")
    v9 = next(item for item in chapters if item["id"] == "V9")
    assert v9["name"] == "Self-contained Tokens"
    assert "V9.1.1" in v9["requirement_ids"]
    search = load_json(index_dir / "search.json")
    ids = {doc["id"] for doc in search}
    assert "req:V9.1.1" in ids
    assert "issue:839" in ids


def test_search_builder_keeps_requirement_text():
    cards = [
        {
            "id": "V9.1.1",
            "uid": "req-a349c369",
            "slug": "tokens",
            "chapter_id": "V9",
            "chapter_name": "Self-contained Tokens",
            "section_name": "Token source",
            "text": "Verify that self-contained tokens are validated.",
            "coverage": "drafted",
        }
    ]
    docs = build_search(cards, [])
    assert docs[0]["href"] == "/requirements/V9.1.1"
    assert "self-contained tokens" in docs[0]["text"]


def test_search_indexes_old_ids_and_origin_notes():
    req = load_json(DATA_DIR / "requirements" / "V1" / "V1.3.6.json")
    docs = build_search([req], [])
    text = docs[0]["text"].lower()
    assert "v5.2.6" in text
    assert "ssrf" in text


def test_mapping_alignment_flags_v13_2_4_git_disagreement():
    report = alignment_report()
    ids = {item["id"] for item in report["git_disagreements"]}
    assert "V13.2.4" in ids
    assert report["counts"]["v4_entries"] > 200


def test_enrich_skips_authored_and_fills_empty_origin():
    authored = load_json(DATA_DIR / "requirements" / "V1" / "V1.3.6.json")
    assert enrich_record(copy.deepcopy(authored)) == "protected"
    linked = copy.deepcopy(load_json(DATA_DIR / "requirements" / "V2" / "V2.2.1.json"))
    linked["summaries"] = []
    assert enrich_record(linked) == "wrote"
    kinds = {item["kind"] for item in linked["summaries"]}
    assert "origin" in kinds
    assert "evolution" in kinds
    assert linked["summaries"][0]["provenance"]["origin"] == "deterministic"


def test_accept_stamps_llm_reviewed_and_authors():
    record = copy.deepcopy(load_json(DATA_DIR / "requirements" / "V9" / "V9.1.1.json"))
    apply_action(
        record,
        path="summaries/0",
        action="accept",
        github="ryarmst",
        name="Ryan Armstrong",
        note="pilot review",
    )
    summary = record["summaries"][0]
    assert summary["provenance"]["origin"] == "llm_reviewed"
    assert summary["provenance"]["review"]["status"] == "accepted"
    assert summary["provenance"]["review"]["by"] == ["ryarmst"]
    assert summary["provenance"]["authors"][0]["github"] == "ryarmst"
    assert summary["provenance"]["model"]["prompt_id"] == "requirement-pass"
    errors = validate_record("requirement", record, "memory")
    assert errors == []


def test_reject_keeps_llm_origin():
    record = copy.deepcopy(load_json(DATA_DIR / "issues" / "839.json"))
    apply_action(record, path="summaries/0", action="reject", github="ryarmst", name="Ryan Armstrong")
    assert record["summaries"][0]["provenance"]["origin"] == "llm"
    assert record["summaries"][0]["provenance"]["review"]["status"] == "rejected"


def test_write_human_summary_validates():
    record = copy.deepcopy(load_json(DATA_DIR / "requirements" / "V9" / "V9.1.1.json"))
    apply_action(
        record,
        path="summaries",
        action="write",
        github="ryarmst",
        name="Ryan Armstrong",
        body="Human origin note for the V9.1.1 signature check.",
    )
    human = record["summaries"][-1]
    assert human["provenance"]["origin"] == "human"
    assert human["kind"] == "evolution"
    errors = validate_record("requirement", record, "memory")
    assert errors == []


def test_artifacts_include_issue_triage():
    record = load_json(DATA_DIR / "issues" / "839.json")
    paths = {item["path"] for item in artifacts(record)}
    assert "triage" in paths
    assert "summaries/0" in paths


def test_origin_counts_skip_rejected_when_published():
    record = copy.deepcopy(load_json(DATA_DIR / "issues" / "839.json"))
    apply_action(record, path="summaries/0", action="reject", github="ryarmst", name="Ryan Armstrong")
    published = origin_counts([record], published_only=True)
    all_counts = origin_counts([record], published_only=False)
    assert all_counts.get("llm", 0) >= published.get("llm", 0)
