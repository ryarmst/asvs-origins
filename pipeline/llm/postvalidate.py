"""Post-validate model JSON before it is written to the corpus."""

from __future__ import annotations

import re
from typing import Any

MAX_QUOTE_WORDS = 25
URL = re.compile(r"https?://[^\s)\]>\"']+")


def collect_input_urls(blob: str) -> set[str]:
    return set(URL.findall(blob or ""))


def collect_input_text(blob: str) -> str:
    return re.sub(r"\s+", " ", blob or "").strip()


def quote_ok(quote: str | None, haystack: str) -> bool:
    if not quote:
        return True
    if len(quote.split()) > MAX_QUOTE_WORDS:
        return False
    return collect_input_text(quote) in haystack


def walk_citations(value: Any):
    if isinstance(value, dict):
        if value.get("type") in {
            "issue_body",
            "issue_comment",
            "pr_body",
            "pr_review_comment",
            "commit",
            "mapping",
            "release_note",
            "external",
        } and value.get("url"):
            yield value
        for child in value.values():
            yield from walk_citations(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_citations(child)


def sanitize(
    payload: dict,
    *,
    allowed_uids: set[str],
    input_blob: str,
) -> tuple[dict, list[str]]:
    """Drop uncitable claims and unknown uids. Returns (payload, log)."""
    log: list[str] = []
    urls = collect_input_urls(input_blob)
    haystack = collect_input_text(input_blob)

    summaries = payload.get("requirement_summaries") or []
    kept = []
    for item in summaries:
        uid = item.get("requirement_uid")
        if uid not in allowed_uids:
            log.append(f"drop requirement_summary unknown uid {uid}")
            continue
        for key in ("decisions", "arguments", "terminology", "open_questions"):
            item[key] = _filter_claims(item.get(key) or [], urls, haystack, log)
        item["citations"] = _filter_citations(item.get("citations") or [], urls, haystack, log)
        kept.append(item)
    payload["requirement_summaries"] = kept

    for summary in payload.get("summaries") or []:
        summary["citations"] = _filter_citations(summary.get("citations") or [], urls, haystack, log)
        if summary.get("quote") is not None:
            pass
    payload["key_sources"] = [
        item
        for item in payload.get("key_sources") or []
        if not item.get("requirement_uid") or item.get("requirement_uid") in allowed_uids
    ]
    return payload, log


def _filter_citations(citations: list[dict], urls: set[str], haystack: str, log: list[str]) -> list[dict]:
    kept = []
    for cite in citations:
        url = cite.get("url") or ""
        if url not in urls and not any(url.startswith(item) or item.startswith(url) for item in urls):
            log.append(f"drop citation missing from input: {url}")
            continue
        quote = cite.get("quote")
        if quote and not quote_ok(quote, haystack):
            cite = dict(cite)
            cite["quote"] = None
            log.append("stripped quote that was not verbatim or too long")
        kept.append(cite)
    return kept


def _filter_claims(claims: list[dict], urls: set[str], haystack: str, log: list[str]) -> list[dict]:
    kept = []
    for claim in claims:
        citations = _filter_citations(claim.get("citations") or [], urls, haystack, log)
        if not citations:
            log.append(f"drop uncitable claim: {(claim.get('statement') or '')[:80]}")
            continue
        claim = dict(claim)
        claim["citations"] = citations
        kept.append(claim)
    return kept
