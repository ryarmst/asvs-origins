"""Stamp provenance, ids, and coverage onto model output."""

from __future__ import annotations

from pipeline.ids import mint_sub_id
from pipeline.records import llm_provenance

CLAIM_PREFIX = {
    "decision": "dec",
    "argument": "arg",
    "terminology": "trm",
    "open_question": "oq",
}


def stamp_citation(raw: dict, *, issue: int | None) -> dict:
    cite = {
        "type": raw.get("type") or "issue_comment",
        "url": raw.get("url"),
        "issue": raw.get("issue") if raw.get("issue") is not None else issue,
        "pr": raw.get("pr"),
        "comment_id": raw.get("comment_id"),
        "commit": raw.get("commit"),
        "author": raw.get("author"),
        "date": raw.get("date"),
        "quote": raw.get("quote"),
        "edited_after": raw.get("edited_after"),
    }
    # Drop keys the schema allows but we want explicit nulls for missing optionals
    # that are required-as-present on some objects. Citation only requires type+url.
    return {key: value for key, value in cite.items() if value is not None or key in {"type", "url"}}


def stamp_claim(
    raw: dict,
    *,
    kind: str,
    issue: int | None,
    digest: str,
    prompt_id: str,
    prompt_version: str,
    provider: str,
    model_id: str,
) -> dict:
    prefix = CLAIM_PREFIX[kind]
    statement = (raw.get("statement") or "").strip()
    citations = [stamp_citation(item, issue=issue) for item in raw.get("citations") or []]
    confidence = raw.get("confidence") or "medium"
    status = raw.get("status") or "unknown"
    if status == "accepted":
        status = "settled"
    elif status not in {"settled", "disputed", "superseded", "unknown"}:
        status = "unknown"
    date = raw.get("date")
    if isinstance(date, str) and "T" in date:
        date = date.split("T", 1)[0]
    return {
        "id": mint_sub_id(prefix, statement, citations[0]["url"] if citations else "none"),
        "statement": statement,
        "kind": kind,
        "subkind": raw.get("subkind") or "unspecified",
        "date": date,
        "actors": list(raw.get("actors") or []),
        "status": status,
        "citations": citations,
        "provenance": llm_provenance(
            prompt_id=prompt_id,
            prompt_version=prompt_version,
            provider=provider,
            model_id=model_id,
            digest=digest,
            confidence=confidence if confidence in {"high", "medium", "low"} else "medium",
        ),
    }


def stamp_summary(
    raw: dict,
    *,
    issue: int | None,
    digest: str,
    prompt_id: str,
    prompt_version: str,
    provider: str,
    model_id: str,
) -> dict:
    body = (raw.get("body") or "").strip()
    citations = [stamp_citation(item, issue=issue) for item in raw.get("citations") or []]
    confidence = raw.get("confidence") or "medium"
    if confidence not in {"high", "medium", "low"}:
        confidence = "medium"
    return {
        "id": mint_sub_id("sum", raw.get("kind") or "overview", body[:80]),
        "kind": raw.get("kind") or "overview",
        "body": body,
        "citations": citations,
        "supersedes": raw.get("supersedes"),
        "provenance": llm_provenance(
            prompt_id=prompt_id,
            prompt_version=prompt_version,
            provider=provider,
            model_id=model_id,
            digest=digest,
            confidence=confidence,
        ),
    }
