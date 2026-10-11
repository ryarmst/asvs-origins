"""Protected-record ratchet and empty corpus stubs."""

from __future__ import annotations

from pipeline.io import utc_now

PROTECTED_COVERAGE = {"reviewed", "authored"}
LOCKED_ORIGINS = {"human"}
LOCKED_REVIEW = {"accepted"}


def is_protected(record: dict) -> bool:
    coverage = (record.get("status") or {}).get("coverage")
    return coverage in PROTECTED_COVERAGE


def is_locked_artifact(provenance: dict | None) -> bool:
    if not provenance:
        return False
    if provenance.get("origin") in LOCKED_ORIGINS:
        return True
    review = provenance.get("review") or {}
    if review.get("status") in LOCKED_REVIEW:
        return True
    return False


def llm_provenance(*, prompt_id: str, prompt_version: str, provider: str, model_id: str, digest: str, confidence: str = "medium", note: str | None = None) -> dict:
    now = utc_now()
    return {
        "origin": "llm",
        "created_at": now,
        "updated_at": now,
        "authors": [],
        "model": {
            "provider": provider,
            "id": model_id,
            "prompt_id": prompt_id,
            "prompt_version": prompt_version,
        },
        "review": {
            "status": "unreviewed",
            "by": [],
            "at": None,
            "note": note,
        },
        "input_digest": digest,
        "confidence": confidence,
    }


def mechanical_provenance(note: str) -> dict:
    now = utc_now()
    return {
        "origin": "deterministic",
        "created_at": now,
        "updated_at": now,
        "authors": [],
        "model": None,
        "review": {
            "status": "unreviewed",
            "by": [],
            "at": None,
            "note": note,
        },
        "input_digest": None,
        "confidence": "high",
    }


def empty_requirement(
    *,
    uid: str,
    slug: str,
    current: dict,
    master: dict,
    identifiers: list[dict],
    lineage: dict,
) -> dict:
    return {
        "uid": uid,
        "slug": slug,
        "current": current,
        "master": master,
        "identifiers": identifiers,
        "lineage": lineage,
        "summaries": [],
        "decisions": [],
        "open_questions": [],
        "terminology": [],
        "key_sources": [],
        "related_requirements": [],
        "external_references": [],
        "status": {
            "coverage": "empty",
            "lineage_state": "empty",
            "last_pipeline_run": utc_now(),
            "last_human_review": None,
            "blocked_reason": None,
            "stale": False,
        },
    }


def empty_issue(
    *,
    number: int,
    url: str,
    title: str,
    state: str,
    created_at: str,
    closed_at: str | None,
    author: str,
    participants: list[str],
    labels: list[str],
    source: dict,
) -> dict:
    return {
        "kind": "issue",
        "number": number,
        "url": url,
        "title": title,
        "state": state,
        "created_at": created_at,
        "closed_at": closed_at,
        "author": author,
        "participants": participants,
        "labels": labels,
        "source": source,
        "triage": None,
        "summaries": [],
        "outcome": None,
        "requirement_summaries": [],
        "unmapped_topics": [],
        "external_references": [],
        "status": {
            "coverage": "empty",
            "last_pipeline_run": utc_now(),
            "last_human_review": None,
            "stale": False,
        },
    }
