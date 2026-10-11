from pipeline.io import load_json, save_json
from pipeline.llm import pass_a, pass_b
from pipeline.llm.digest import input_digest
from pipeline.llm.provider import MockProvider
from pipeline.paths import DATA_DIR
from pipeline.records import is_protected


def test_pass_a_writes_triage_and_skips_on_digest(tmp_path, monkeypatch):
    number = 839
    dest = DATA_DIR / "issues" / f"{number}.json"
    original = load_json(dest)
    provider = MockProvider(
        responses=[
            {
                "class": "wording",
                "relevance": "requirement_bearing",
                "estimated_requirement_count": 1,
                "reason": "Discusses the level of the stateless token signing control.",
            }
        ]
    )
    try:
        assert pass_a.run_one(number, provider) == "requirement_bearing"
        updated = load_json(dest)
        assert updated["triage"]["class"] == "wording"
        assert updated["triage"]["provenance"]["origin"] == "llm"
        assert updated["triage"]["provenance"]["authors"] == []
        assert pass_a.run_one(number, provider) == "skipped_digest"
    finally:
        save_json(dest, original)


def test_pass_b_drops_unknown_uid_and_uncited_claims():
    number = 839
    dest = DATA_DIR / "issues" / f"{number}.json"
    original = load_json(dest)
    snap_url = original["url"]
    payload = {
        "summaries": [
            {
                "kind": "overview",
                "body": "The thread argued whether token signature verification belongs at L1.",
                "citations": [{"type": "issue_body", "url": snap_url, "issue": number}],
            }
        ],
        "outcome": {"state": "accepted", "resulting_changes": ["level"], "closed_reason": None},
        "requirement_summaries": [
            {
                "requirement_uid": "req-deadbeef",
                "requirement_id_at_time": "V3.5.3",
                "relevance": "primary",
                "body": "Should not survive.",
                "outcome": "changed",
                "decisions": [],
                "arguments": [],
                "terminology": [],
                "open_questions": [],
                "citations": [{"type": "issue_body", "url": snap_url}],
            },
            {
                "requirement_uid": "req-a349c369",
                "requirement_id_at_time": "V3.5.3",
                "relevance": "primary",
                "body": "Signing of stateless tokens was argued down to L1.",
                "outcome": "changed",
                "decisions": [
                    {
                        "statement": "This claim has no citation.",
                        "subkind": "level",
                        "date": "2019-01-01",
                        "actors": ["jmanico"],
                        "status": "settled",
                        "citations": [],
                    }
                ],
                "arguments": [],
                "terminology": [],
                "open_questions": [],
                "citations": [{"type": "issue_body", "url": snap_url, "quote": "this quote is not in the issue at all"}],
            },
        ],
        "unmapped_topics": [],
        "external_references": [],
    }
    provider = MockProvider(responses=[payload])
    try:
        result = pass_b.run_one(number, "V9", provider, force=True)
        assert result == "wrote"
        updated = load_json(dest)
        uids = {item["requirement_uid"] for item in updated["requirement_summaries"]}
        assert "req-deadbeef" not in uids
        assert "req-a349c369" in uids
        slice_ = next(item for item in updated["requirement_summaries"] if item["requirement_uid"] == "req-a349c369")
        assert slice_["decisions"] == []
        assert slice_["citations"][0].get("quote") in {None} or "quote" not in slice_["citations"][0]
        assert updated["status"]["coverage"] == "drafted"
        assert updated["summaries"][0]["provenance"]["model"]["prompt_id"] == "issue-pass"
    finally:
        save_json(dest, original)


def test_pass_b_does_not_overwrite_protected_issue():
    assert is_protected(load_json(DATA_DIR / "issues" / "3338.json"))
    provider = MockProvider(responses=[{"summaries": []}])
    assert pass_b.run_one(3338, "V9", provider, force=True) == "protected"


def test_input_digest_changes_with_prompt_version():
    primary = {"n": 1}
    a = input_digest(primary, prompt_id="issue-pass", prompt_version="v1", provider="mock", model_id="m")
    b = input_digest(primary, prompt_id="issue-pass", prompt_version="v2", provider="mock", model_id="m")
    assert a != b
    assert a.startswith("sha256:")
