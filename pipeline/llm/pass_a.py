"""Pass A — cheap triage."""

from __future__ import annotations

import argparse
import json
import sys

from pipeline.ids import canonical_json
from pipeline.io import load_json, save_json, utc_now
from pipeline.llm.context import chapter_issue_numbers, compact_snapshot
from pipeline.llm.digest import input_digest
from pipeline.llm.prompts import load_prompt
from pipeline.llm.provider import JsonProvider, provider_from_env
from pipeline.paths import DATA_DIR
from pipeline.records import is_protected, llm_provenance

CLASSES = {
    "proposal",
    "clarification",
    "defect",
    "wording",
    "process",
    "translation",
    "meta",
    "spam",
}
RELEVANCE = {"requirement_bearing", "chapter_bearing", "no_requirement"}


def assemble(number: int) -> dict:
    snap = compact_snapshot(number, body_limit=2000)
    return {
        "number": number,
        "title": snap["title"],
        "body": snap["body"],
        "labels": snap["labels"],
        "comment_count": len(snap["comments"]),
        "participants": sorted(
            {snap["author"], *(item["author"] for item in snap["comments"] if item.get("author"))}
            - {None}
        ),
        "url": snap["url"],
    }


def run_one(number: int, provider: JsonProvider, *, force: bool = False) -> str:
    dest = DATA_DIR / "issues" / f"{number}.json"
    if not dest.exists():
        return "missing"
    record = load_json(dest)
    if is_protected(record):
        return "protected"
    prompt_id, prompt_version, system = load_prompt("triage")
    primary = assemble(number)
    digest = input_digest(
        primary,
        prompt_id=prompt_id,
        prompt_version=prompt_version,
        provider=provider.provider,
        model_id=provider.model_id,
    )
    existing = (record.get("triage") or {}).get("provenance") or {}
    if not force and existing.get("input_digest") == digest:
        return "skipped_digest"
    user = canonical_json(primary)
    raw = provider.complete_json(system, user)
    klass = raw.get("class") if raw.get("class") in CLASSES else "meta"
    relevance = raw.get("relevance") if raw.get("relevance") in RELEVANCE else "no_requirement"
    count = raw.get("estimated_requirement_count") or 0
    if not isinstance(count, int) or count < 0:
        count = 0
    reason = (raw.get("reason") or "No reason supplied.").strip()
    record["triage"] = {
        "class": klass,
        "relevance": relevance,
        "estimated_requirement_count": count,
        "reason": reason,
        "provenance": llm_provenance(
            prompt_id=prompt_id,
            prompt_version=prompt_version,
            provider=provider.provider,
            model_id=provider.model_id,
            digest=digest,
            confidence="medium",
            note="Pass A triage",
        ),
    }
    if relevance == "no_requirement" and record["status"]["coverage"] == "empty":
        record["status"]["coverage"] = "linked"
        topic = {
            "topic": klass,
            "reason": reason,
            "provenance": record["triage"]["provenance"],
        }
        existing_topics = record.get("unmapped_topics") or []
        if not any(item.get("reason") == reason for item in existing_topics):
            record["unmapped_topics"] = existing_topics + [topic]
    record["status"]["last_pipeline_run"] = utc_now()
    save_json(dest, record)
    return relevance


def run_chapter(chapter: str, provider: JsonProvider | None = None, *, limit: int | None = None, force: bool = False) -> dict:
    client = provider_from_env(provider)
    numbers = chapter_issue_numbers(chapter)
    if limit is not None:
        numbers = numbers[:limit]
    counts: dict[str, int] = {}
    for number in numbers:
        result = run_one(number, client, force=force)
        counts[result] = counts.get(result, 0) + 1
        print(f"pass_a {number}: {result}", flush=True)
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
