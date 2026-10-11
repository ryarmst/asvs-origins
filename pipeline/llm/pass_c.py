"""Pass C — requirement synthesis."""

from __future__ import annotations

import argparse
import json
import sys

from pipeline.io import load_json, save_json, utc_now
from pipeline.llm.context import compact_lineage, load_chapter_requirements
from pipeline.llm.digest import input_digest
from pipeline.llm.postvalidate import sanitize
from pipeline.llm.prompts import load_prompt
from pipeline.llm.provider import JsonProvider, provider_from_env
from pipeline.llm.stamp import stamp_claim, stamp_citation, stamp_summary
from pipeline.paths import DATA_DIR
from pipeline.records import is_locked_artifact, is_protected

PASS_C_SCHEMA_HINT = """
Return JSON with keys:
summaries: [{kind: origin|evolution|interpretation|controversy, body, citations[], confidence}]
open_questions: [claims]
terminology: [claims]
decisions: [claims]
key_sources: [{kind: issue|pr, number, role, rank}]
blocked_reason: string or null

Claims: {statement, subkind, date, actors, status, citations[], confidence}
Citations: {type, url, issue?, commit?, author?, date?, quote?}
"""


def linked_slices(uid: str) -> list[dict]:
    slices = []
    for path in sorted((DATA_DIR / "issues").glob("*.json")):
        data = load_json(path)
        for item in data.get("requirement_summaries") or []:
            if item.get("requirement_uid") != uid:
                continue
            if (item.get("provenance") or {}).get("review", {}).get("status") == "rejected":
                continue
            slices.append(
                {
                    "issue": data["number"],
                    "title": data["title"],
                    "url": data["url"],
                    "created_at": data.get("created_at"),
                    "slice": {
                        "id": item.get("id"),
                        "requirement_id_at_time": item.get("requirement_id_at_time"),
                        "relevance": item.get("relevance"),
                        "body": item.get("body"),
                        "outcome": item.get("outcome"),
                        "decisions": item.get("decisions") or [],
                        "arguments": item.get("arguments") or [],
                        "terminology": item.get("terminology") or [],
                        "open_questions": item.get("open_questions") or [],
                        "citations": item.get("citations") or [],
                    },
                }
            )
    slices.sort(key=lambda item: item.get("created_at") or "")
    return slices


def assemble(req: dict) -> dict:
    return {
        "current": req["current"],
        "identifiers": req.get("identifiers") or [],
        "predecessors": req.get("lineage", {}).get("predecessors") or [],
        "mapping_entry": req.get("lineage", {}).get("mapping_entry"),
        "lineage_events": compact_lineage(req),
        "issue_slices": linked_slices(req["uid"]),
    }


def apply_payload(
    req: dict,
    payload: dict,
    *,
    digest: str,
    prompt_id: str,
    prompt_version: str,
    provider: str,
    model_id: str,
    input_blob: str,
) -> list[str]:
    allowed = {req["uid"]}
    payload, log = sanitize(payload, allowed_uids=allowed, input_blob=input_blob)
    meta = dict(
        issue=None,
        digest=digest,
        prompt_id=prompt_id,
        prompt_version=prompt_version,
        provider=provider,
        model_id=model_id,
    )
    kinds = {"origin", "evolution", "interpretation", "controversy"}
    new_summaries = []
    for raw in payload.get("summaries") or []:
        if raw.get("kind") not in kinds:
            continue
        if not (raw.get("body") or "").strip():
            continue
        new_summaries.append(stamp_summary(raw, **meta))
    locked = [item for item in req.get("summaries") or [] if is_locked_artifact(item.get("provenance"))]
    if locked:
        for item in new_summaries:
            for old in locked:
                if old.get("kind") == item.get("kind"):
                    item["supersedes"] = old["id"]
                    break
        req["summaries"] = locked + new_summaries
    else:
        req["summaries"] = new_summaries

    def merge_claims(field: str, kind: str) -> None:
        incoming = [stamp_claim(item, kind=kind, **meta) for item in payload.get(field) or []]
        locked_items = [item for item in req.get(field) or [] if is_locked_artifact(item.get("provenance"))]
        req[field] = locked_items + incoming

    merge_claims("decisions", "decision")
    merge_claims("open_questions", "open_question")
    merge_claims("terminology", "terminology")

    sources = []
    for raw in payload.get("key_sources") or []:
        if raw.get("kind") not in {"issue", "pr"}:
            continue
        number = raw.get("number")
        if not isinstance(number, int):
            continue
        rank = raw.get("rank") if isinstance(raw.get("rank"), int) and raw.get("rank") >= 1 else len(sources) + 1
        sources.append(
            {
                "kind": raw["kind"],
                "number": number,
                "role": (raw.get("role") or "discussion").strip() or "discussion",
                "rank": rank,
            }
        )
    sources.sort(key=lambda item: item["rank"])
    req["key_sources"] = sources[:5]

    blocked = payload.get("blocked_reason")
    req["status"]["blocked_reason"] = blocked if isinstance(blocked, str) and blocked.strip() else None
    if req["status"]["coverage"] in {"empty", "linked"}:
        req["status"]["coverage"] = "drafted"
    req["status"]["last_pipeline_run"] = utc_now()
    return log


def run_one(req_id: str, provider: JsonProvider, *, force: bool = False) -> str:
    chapter = req_id.split(".")[0]
    path = DATA_DIR / "requirements" / chapter / f"{req_id}.json"
    if not path.exists():
        return "missing"
    req = load_json(path)
    if is_protected(req):
        return "protected"
    prompt_id, prompt_version, system = load_prompt("requirement-pass")
    primary = assemble(req)
    digest = input_digest(
        primary,
        prompt_id=prompt_id,
        prompt_version=prompt_version,
        provider=provider.provider,
        model_id=provider.model_id,
    )
    existing = [
        item
        for item in req.get("summaries") or []
        if (item.get("provenance") or {}).get("input_digest") == digest
    ]
    if existing and not force:
        return "skipped_digest"
    user = PASS_C_SCHEMA_HINT + "\n\nINPUT:\n" + json.dumps(primary, ensure_ascii=False, indent=2)
    raw = provider.complete_json(system, user)
    apply_payload(
        req,
        raw,
        digest=digest,
        prompt_id=prompt_id,
        prompt_version=prompt_version,
        provider=provider.provider,
        model_id=provider.model_id,
        input_blob=user,
    )
    save_json(path, req)
    return "wrote"


def run_chapter(chapter: str, provider: JsonProvider | None = None, *, force: bool = False) -> dict:
    client = provider_from_env(provider)
    counts: dict[str, int] = {}
    for req in load_chapter_requirements(chapter):
        req_id = req["current"]["id"]
        result = run_one(req_id, client, force=force)
        counts[result] = counts.get(result, 0) + 1
        print(f"pass_c {req_id}: {result}", flush=True)
    return {"results": counts}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chapter", default="V9")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run_chapter(args.chapter, force=args.force), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
