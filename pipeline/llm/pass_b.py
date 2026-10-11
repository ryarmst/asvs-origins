"""Pass B — issue summarization."""

from __future__ import annotations

import argparse
import json
import sys

from pipeline.ids import canonical_json, mint_sub_id
from pipeline.io import load_json, save_json, utc_now
from pipeline.llm.context import (
    chapter_issue_numbers,
    compact_asvs_context,
    compact_snapshot,
    edit_history_note,
    issue_candidates,
)
from pipeline.llm.digest import input_digest
from pipeline.llm.postvalidate import sanitize
from pipeline.llm.prompts import load_prompt
from pipeline.llm.provider import JsonProvider, provider_from_env
from pipeline.llm.stamp import stamp_claim, stamp_citation, stamp_summary
from pipeline.paths import DATA_DIR
from pipeline.records import is_locked_artifact, is_protected, llm_provenance

PASS_B_SCHEMA_HINT = """
Return JSON with keys:
summaries: [{kind: "overview", body, citations[], confidence}]
outcome: {state: unresolved|accepted|rejected|deferred|merged|no_action, resulting_changes: [str], closed_reason}
requirement_summaries: [{
  requirement_uid, requirement_id_at_time, relevance: primary|secondary|mentioned,
  body, outcome: changed|no_change_yet|rejected|deferred|unresolved,
  decisions[], arguments[], terminology[], open_questions[], citations[]
}]
unmapped_topics: [{topic, reason}]
external_references: [{kind, url, title, id}]

Each claim: {statement, kind omitted (inferred from array), subkind, date (YYYY-MM-DD or null),
actors: [github logins], status: settled|disputed|superseded|unknown, citations[], confidence}
Each citation: {type, url, author, date, quote?, comment_id?, commit?}
"""


def assemble(number: int, chapter: str) -> dict:
    return {
        "issue_snapshot": compact_snapshot(number),
        "edit_history": edit_history_note(number),
        "candidate_requirements": issue_candidates(number, chapter),
        "asvs_context": compact_asvs_context(),
    }


def _blob(primary: dict) -> str:
    return canonical_json(primary)


def apply_payload(
    record: dict,
    payload: dict,
    *,
    number: int,
    digest: str,
    prompt_id: str,
    prompt_version: str,
    provider: str,
    model_id: str,
    allowed_uids: set[str],
    input_blob: str,
) -> list[str]:
    payload, log = sanitize(payload, allowed_uids=allowed_uids, input_blob=input_blob)
    meta = dict(
        issue=number,
        digest=digest,
        prompt_id=prompt_id,
        prompt_version=prompt_version,
        provider=provider,
        model_id=model_id,
    )
    new_summaries = []
    for raw in payload.get("summaries") or []:
        if raw.get("kind") not in {
            "origin",
            "evolution",
            "interpretation",
            "controversy",
            "overview",
            "outcome",
        }:
            raw["kind"] = "overview"
        new_summaries.append(stamp_summary(raw, **meta))
    locked = [item for item in record.get("summaries") or [] if is_locked_artifact(item.get("provenance"))]
    unlocked = [item for item in record.get("summaries") or [] if not is_locked_artifact(item.get("provenance"))]
    if locked:
        for item in new_summaries:
            if unlocked:
                item["supersedes"] = unlocked[0]["id"]
        record["summaries"] = locked + new_summaries
    else:
        record["summaries"] = new_summaries

    raw_outcome = payload.get("outcome")
    if isinstance(raw_outcome, dict) and not is_locked_artifact((record.get("outcome") or {}).get("provenance")):
        record["outcome"] = {
            "state": raw_outcome.get("state")
            if raw_outcome.get("state")
            in {"unresolved", "accepted", "rejected", "deferred", "merged", "no_action"}
            else "unresolved",
            "resulting_changes": list(raw_outcome.get("resulting_changes") or []),
            "closed_reason": raw_outcome.get("closed_reason"),
            "provenance": llm_provenance(
                prompt_id=prompt_id,
                prompt_version=prompt_version,
                provider=provider,
                model_id=model_id,
                digest=digest,
                note="Pass B outcome",
            ),
        }

    slices = []
    for raw in payload.get("requirement_summaries") or []:
        uid = raw.get("requirement_uid")
        if uid not in allowed_uids:
            continue
        body = (raw.get("body") or "").strip()
        if not body:
            continue
        outcome = raw.get("outcome")
        if outcome not in {"changed", "no_change_yet", "rejected", "deferred", "unresolved"}:
            outcome = "unresolved"
        relevance = raw.get("relevance") if raw.get("relevance") in {"primary", "secondary", "mentioned"} else "mentioned"
        slices.append(
            {
                "id": mint_sub_id("rs", str(number), uid, body[:40]),
                "requirement_uid": uid,
                "requirement_id_at_time": raw.get("requirement_id_at_time"),
                "relevance": relevance,
                "body": body,
                "decisions": [
                    stamp_claim(item, kind="decision", **meta) for item in raw.get("decisions") or []
                ],
                "arguments": [
                    stamp_claim(item, kind="argument", **meta) for item in raw.get("arguments") or []
                ],
                "terminology": [
                    stamp_claim(item, kind="terminology", **meta) for item in raw.get("terminology") or []
                ],
                "open_questions": [
                    stamp_claim(item, kind="open_question", **meta) for item in raw.get("open_questions") or []
                ],
                "outcome": outcome,
                "citations": [stamp_citation(item, issue=number) for item in raw.get("citations") or []],
                "provenance": llm_provenance(
                    prompt_id=prompt_id,
                    prompt_version=prompt_version,
                    provider=provider,
                    model_id=model_id,
                    digest=digest,
                    note="Pass B requirement slice",
                ),
            }
        )
    locked_slices = [
        item for item in record.get("requirement_summaries") or [] if is_locked_artifact(item.get("provenance"))
    ]
    record["requirement_summaries"] = locked_slices + slices

    topics = []
    for raw in payload.get("unmapped_topics") or []:
        if not raw.get("topic") or not raw.get("reason"):
            continue
        topics.append(
            {
                "topic": raw["topic"],
                "reason": raw["reason"],
                "provenance": llm_provenance(
                    prompt_id=prompt_id,
                    prompt_version=prompt_version,
                    provider=provider,
                    model_id=model_id,
                    digest=digest,
                    note="Pass B unmapped topic",
                ),
            }
        )
    locked_topics = [
        item for item in record.get("unmapped_topics") or [] if is_locked_artifact(item.get("provenance"))
    ]
    record["unmapped_topics"] = locked_topics + topics

    refs = []
    for raw in payload.get("external_references") or []:
        if not raw.get("url") or not raw.get("kind"):
            continue
        refs.append(
            {
                "kind": raw["kind"],
                "id": raw.get("id"),
                "title": raw.get("title"),
                "url": raw["url"],
                "cited_by": raw.get("cited_by"),
            }
        )
    record["external_references"] = refs or record.get("external_references") or []
    if record["status"]["coverage"] in {"empty", "linked"}:
        record["status"]["coverage"] = "drafted"
    record["status"]["last_pipeline_run"] = utc_now()
    return log


def run_one(number: int, chapter: str, provider: JsonProvider, *, force: bool = False) -> str:
    dest = DATA_DIR / "issues" / f"{number}.json"
    if not dest.exists():
        return "missing"
    record = load_json(dest)
    if is_protected(record):
        return "protected"
    triage = record.get("triage") or {}
    if triage.get("relevance") == "no_requirement" and not force:
        return "skipped_triage"
    prompt_id, prompt_version, system = load_prompt("issue-pass")
    primary = assemble(number, chapter)
    digest = input_digest(
        primary,
        prompt_id=prompt_id,
        prompt_version=prompt_version,
        provider=provider.provider,
        model_id=provider.model_id,
    )
    existing = None
    for item in record.get("summaries") or []:
        if (item.get("provenance") or {}).get("input_digest") == digest:
            existing = item
            break
    if existing and not force:
        return "skipped_digest"
    allowed = {item["uid"] for item in primary["candidate_requirements"]}
    user = (
        PASS_B_SCHEMA_HINT
        + "\n\nINPUT:\n"
        + json.dumps(primary, ensure_ascii=False, indent=2)
    )
    raw = provider.complete_json(system, user)
    apply_payload(
        record,
        raw,
        number=number,
        digest=digest,
        prompt_id=prompt_id,
        prompt_version=prompt_version,
        provider=provider.provider,
        model_id=provider.model_id,
        allowed_uids=allowed,
        input_blob=user,
    )
    save_json(dest, record)
    return "wrote"


def run_chapter(chapter: str, provider: JsonProvider | None = None, *, limit: int | None = None, force: bool = False) -> dict:
    client = provider_from_env(provider)
    numbers = chapter_issue_numbers(chapter)
    if limit is not None:
        numbers = numbers[:limit]
    counts: dict[str, int] = {}
    for number in numbers:
        result = run_one(number, chapter, client, force=force)
        counts[result] = counts.get(result, 0) + 1
        print(f"pass_b {number}: {result}", flush=True)
    return {"issues": len(numbers), "results": counts}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chapter", default="V9")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    stats = run_chapter(args.chapter, limit=args.limit, force=args.force)
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
