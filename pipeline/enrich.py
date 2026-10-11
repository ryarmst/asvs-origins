"""Write origin/evolution summaries from mapping + git lineage for every requirement.

This is mechanical enrichment, not a model pass. Existing human, reviewed, and
LLM summaries are left alone. Artifacts are stamped `deterministic`.
"""

from __future__ import annotations

import argparse
import sys

from pipeline.ids import mint_sub_id
from pipeline.io import load_json, save_json, utc_now
from pipeline.llm.context import BULK_SUBJECT, compact_lineage
from pipeline.paths import DATA_DIR
from pipeline.records import is_protected, mechanical_provenance

MAPPING_URL = "https://github.com/OWASP/ASVS/blob/master/5.0/mappings/mapping_v5.0.0_to_v4.0.3.yml"
KIND_LABEL = {
    "new_in_release": "new in 5.0.0",
    "carried_forward": "carried forward from 4.0.3",
    "split_from": "split from a 4.0.3 control",
    "merged_from": "merged from 4.0.3 controls",
    "unknown": "of uncertain mapping status",
}


def _has_kind(summaries: list[dict], kind: str) -> bool:
    return any(item.get("kind") == kind for item in summaries or [])


def _mapping_cite() -> dict:
    return {"type": "mapping", "url": MAPPING_URL}


def _event_cites(event: dict) -> list[dict]:
    out = []
    for cite in event.get("citations") or []:
        if cite.get("type") and cite.get("url"):
            out.append({key: value for key, value in cite.items() if value is not None})
    return out


def _issue_sources(events: list[dict]) -> list[dict]:
    seen: set[int] = set()
    sources = []
    for event in events:
        if event.get("kind") in {"renumbered", "tag_cleanup"}:
            continue
        if BULK_SUBJECT.search(event.get("summary") or ""):
            continue
        for cite in event.get("citations") or []:
            number = cite.get("issue")
            if not isinstance(number, int) or number in seen:
                continue
            seen.add(number)
            sources.append({"kind": "issue", "number": number, "role": "discussion", "rank": len(sources) + 1})
            if len(sources) >= 5:
                return sources
    return sources


def _origin_body(req: dict) -> tuple[str, list[dict]]:
    req_id = req["current"]["id"]
    lineage = req.get("lineage") or {}
    kind = lineage.get("origin_kind") or "unknown"
    mapping = lineage.get("mapping_entry") or {}
    preds = [item for item in lineage.get("predecessors") or [] if item.get("release") == "4.0.3"]
    events = compact_lineage(req, limit=40)
    added = next((item for item in events if item.get("kind") == "added"), events[0] if events else None)
    cites = [_mapping_cite()]
    parts = [f"{req_id} is {KIND_LABEL.get(kind, kind)}."]
    if mapping.get("raw"):
        parts.append(f"Official mapping: {mapping['raw']}.")
    if preds:
        listed = ", ".join(f"{item.get('id')} ({item.get('relation')})" for item in preds[:4])
        parts.append(f"4.0.3 predecessor{'s' if len(preds) > 1 else ''}: {listed}.")
        if preds[0].get("note"):
            parts.append(preds[0]["note"].rstrip(".") + ".")
    if added:
        actor = added.get("actor") or "unknown"
        when = added.get("date") or "an unknown date"
        at_id = added.get("id_at_time") or req_id
        summary = (added.get("summary") or "").rstrip(".")
        parts.append(f"Git first records it as {at_id} on {when} ({actor})" + (f": {summary}." if summary else "."))
        cites.extend(_event_cites(added)[:4])
    if mapping.get("agrees_with_git") is False and mapping.get("note"):
        parts.append(mapping["note"].rstrip(".") + ".")
    return " ".join(parts), cites[:8]


def _evolution_body(req: dict) -> tuple[str, list[dict]]:
    req_id = req["current"]["id"]
    events = compact_lineage(req, limit=40)
    mapping = (req.get("lineage") or {}).get("mapping_entry") or {}
    material = [
        item
        for item in events
        if item.get("kind") not in {"added", "renumbered", "tag_cleanup"}
        and not BULK_SUBJECT.search(item.get("summary") or "")
    ]
    cites = [_mapping_cite()]
    if not material:
        body = (
            f"After it entered the tree, {req_id} has no later wording events in the filtered git lineage. "
            "Renumbering and bulk tag-cleanup commits are omitted here."
        )
        return body, cites
    clauses = []
    for event in material[:6]:
        when = event.get("date") or ""
        actor = event.get("actor") or ""
        summary = (event.get("summary") or event.get("kind") or "").rstrip(".")
        who = f" ({actor})" if actor else ""
        clauses.append(f"{when}{who}: {summary}".strip(": ").strip() + ".")
        cites.extend(_event_cites(event)[:2])
        if len(clauses) >= 5:
            break
    extra = len(material) - len(clauses)
    tail = f" {extra} further wording event{'s' if extra != 1 else ''} are in the timeline." if extra > 0 else ""
    if mapping.get("agrees_with_git") is False:
        tail += " The official mapping disagrees with git; git is treated as authoritative."
    return " ".join(clauses) + tail, cites[:8]


def _stamp_summary(kind: str, body: str, citations: list[dict]) -> dict:
    return {
        "id": mint_sub_id("sum", kind, body[:80]),
        "kind": kind,
        "body": body,
        "citations": citations,
        "supersedes": None,
        "provenance": mechanical_provenance("Synthesized from official mapping YAML and git lineage events."),
    }


def enrich_record(req: dict, *, force: bool = False) -> str:
    if is_protected(req):
        return "protected"
    summaries = list(req.get("summaries") or [])
    wrote = False
    if force or not _has_kind(summaries, "origin"):
        body, cites = _origin_body(req)
        summaries = [item for item in summaries if item.get("kind") != "origin"] + [
            _stamp_summary("origin", body, cites)
        ]
        wrote = True
    if force or not _has_kind(summaries, "evolution"):
        body, cites = _evolution_body(req)
        summaries = [item for item in summaries if item.get("kind") != "evolution"] + [
            _stamp_summary("evolution", body, cites)
        ]
        wrote = True
    if not wrote:
        return "skipped"
    req["summaries"] = summaries
    if not req.get("key_sources"):
        req["key_sources"] = _issue_sources((req.get("lineage") or {}).get("events") or [])
    if req["status"]["coverage"] in {"empty", "linked"}:
        req["status"]["coverage"] = "drafted"
    req["status"]["last_pipeline_run"] = utc_now()
    return "wrote"


def run_all(*, force: bool = False, chapter: str | None = None) -> dict:
    counts: dict[str, int] = {}
    root = DATA_DIR / "requirements"
    paths = sorted((root / chapter).glob("*.json")) if chapter else sorted(root.glob("*/*.json"))
    for path in paths:
        req = load_json(path)
        result = enrich_record(req, force=force)
        counts[result] = counts.get(result, 0) + 1
        if result == "wrote":
            save_json(path, req)
            print(f"enrich {req['current']['id']}: wrote", flush=True)
    return {"results": counts, "chapter": chapter}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chapter")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    stats = run_all(force=args.force, chapter=args.chapter)
    print(stats)
    return 0


if __name__ == "__main__":
    sys.exit(main())
