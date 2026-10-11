"""Dump compact Pass C inputs and apply session-local requirement drafts.

No vendor API. Payloads in build/session-pass-c/out/ are stamped llm / unreviewed.
Does not overwrite protected records or existing human/LLM summaries.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pipeline.io import load_json, save_json
from pipeline.llm.context import compact_lineage, compact_snapshot
from pipeline.llm.digest import input_digest
from pipeline.llm.pass_c import apply_payload
from pipeline.llm.prompts import load_prompt
from pipeline.paths import BUILD_DIR, DATA_DIR, ISSUES_DIR
from pipeline.records import is_protected

ROOT = BUILD_DIR / "session-pass-c"
INPUT_DIR = ROOT / "input"
OUT_DIR = ROOT / "out"
MAPPING_URL = "https://github.com/OWASP/ASVS/blob/master/5.0/mappings/mapping_v5.0.0_to_v4.0.3.yml"


def _origin_of(req: dict) -> set[str]:
    return {
        (item.get("provenance") or {}).get("origin")
        for item in req.get("summaries") or []
        if item.get("kind") == "origin"
    }


def is_session_target(req: dict) -> bool:
    if is_protected(req):
        return False
    origins = _origin_of(req)
    if origins & {"human", "llm", "llm_reviewed"}:
        return False
    return True


def _issue_numbers(req: dict) -> list[int]:
    seen: list[int] = []
    for event in (req.get("lineage") or {}).get("events") or []:
        for cite in event.get("citations") or []:
            number = cite.get("issue")
            if isinstance(number, int) and number not in seen:
                seen.append(number)
    for source in req.get("key_sources") or []:
        number = source.get("number")
        if source.get("kind") == "issue" and isinstance(number, int) and number not in seen:
            seen.append(number)
    return seen[:5]


def _compact_issue(number: int) -> dict | None:
    path = ISSUES_DIR / f"{number}.json"
    if not path.exists():
        return None
    snap = compact_snapshot(number, body_limit=1600)
    comments = []
    for comment in (snap.get("comments") or [])[:8]:
        body = (comment.get("body") or "").replace("\r\n", "\n")[:600]
        comments.append(
            {
                "url": comment.get("url"),
                "author": comment.get("author"),
                "createdAt": comment.get("createdAt"),
                "body": body,
            }
        )
    return {
        "number": snap.get("number") or number,
        "url": snap.get("url"),
        "title": snap.get("title"),
        "state": snap.get("state"),
        "author": snap.get("author"),
        "createdAt": snap.get("createdAt"),
        "body": (snap.get("body") or "").replace("\r\n", "\n")[:1600],
        "comments": comments,
    }


def assemble_dump(req: dict) -> dict:
    mapping = (req.get("lineage") or {}).get("mapping_entry") or {}
    preds = []
    for item in (req.get("lineage") or {}).get("predecessors") or []:
        preds.append(
            {
                "release": item.get("release"),
                "id": item.get("id"),
                "relation": item.get("relation"),
                "text": item.get("text"),
                "note": item.get("note"),
            }
        )
    issues = []
    for number in _issue_numbers(req):
        packed = _compact_issue(number)
        if packed:
            issues.append(packed)
    return {
        "uid": req["uid"],
        "current": req["current"],
        "identifiers": req.get("identifiers") or [],
        "origin_kind": (req.get("lineage") or {}).get("origin_kind"),
        "mapping_entry": mapping,
        "mapping_url": MAPPING_URL,
        "predecessors": preds,
        "lineage_events": compact_lineage(req, limit=20),
        "issues": issues,
        "existing_extracted": [
            {"kind": item.get("kind"), "body": item.get("body")}
            for item in req.get("summaries") or []
            if (item.get("provenance") or {}).get("origin") == "deterministic"
        ],
    }


def dump_all(chapter: str | None = None) -> dict:
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    root = DATA_DIR / "requirements"
    paths = sorted((root / chapter).glob("*.json")) if chapter else sorted(root.glob("*/*.json"))
    counts = {"dumped": 0, "skipped": 0}
    by_chapter: dict[str, list[str]] = {}
    for path in paths:
        req = load_json(path)
        if not is_session_target(req):
            counts["skipped"] += 1
            continue
        payload = assemble_dump(req)
        req_id = req["current"]["id"]
        dest = INPUT_DIR / f"{req_id}.json"
        dest.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        counts["dumped"] += 1
        by_chapter.setdefault(req["current"]["chapter_id"], []).append(req_id)
        print(f"dump {req_id}", flush=True)
    (ROOT / "manifest.json").write_text(
        json.dumps({"counts": counts, "chapters": by_chapter}, indent=2) + "\n",
        encoding="utf-8",
    )
    return counts


def apply_all(*, force: bool = False) -> dict:
    prompt_id, prompt_version, _ = load_prompt("requirement-pass")
    counts: dict[str, int] = {}
    for path in sorted(OUT_DIR.glob("V*.json")):
        req_id = path.stem
        chapter = req_id.split(".")[0]
        rec_path = DATA_DIR / "requirements" / chapter / f"{req_id}.json"
        if not rec_path.exists():
            counts["missing"] = counts.get("missing", 0) + 1
            continue
        req = load_json(rec_path)
        if not force and not is_session_target(req):
            counts["skipped"] = counts.get("skipped", 0) + 1
            continue
        dump_path = INPUT_DIR / f"{req_id}.json"
        if not dump_path.exists():
            counts["no_input"] = counts.get("no_input", 0) + 1
            continue
        dump = json.loads(dump_path.read_text(encoding="utf-8"))
        payload = json.loads(path.read_text(encoding="utf-8"))
        keep_sources = list(req.get("key_sources") or [])
        extracted = [
            item
            for item in req.get("summaries") or []
            if (item.get("provenance") or {}).get("origin") == "deterministic"
        ]
        blob = json.dumps(dump, ensure_ascii=False)
        digest = input_digest(
            dump,
            prompt_id=prompt_id,
            prompt_version=prompt_version,
            provider="cursor-session",
            model_id="grok-4.6",
        )
        log = apply_payload(
            req,
            payload,
            digest=digest,
            prompt_id=prompt_id,
            prompt_version=prompt_version,
            provider="cursor-session",
            model_id="grok-4.6",
            input_blob=blob,
        )
        incoming = req.get("summaries") or []
        for item in incoming:
            for old in extracted:
                if old.get("kind") == item.get("kind"):
                    item["supersedes"] = old.get("id")
                    break
        req["summaries"] = extracted + incoming
        if not req.get("key_sources") and keep_sources:
            req["key_sources"] = keep_sources
        save_json(rec_path, req)
        counts["wrote"] = counts.get("wrote", 0) + 1
        dropped = [line for line in log if line.startswith("drop")]
        print(f"apply {req_id}: wrote drops={len(dropped)}", flush=True)
    return counts


def validate_out() -> dict:
    counts = {"ok": 0, "bad": 0}
    problems: list[str] = []
    for path in sorted(OUT_DIR.glob("V*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            counts["bad"] += 1
            problems.append(f"{path.stem}: invalid JSON ({exc})")
            continue
        kinds = {item.get("kind") for item in payload.get("summaries") or [] if item.get("body")}
        if "origin" not in kinds or "evolution" not in kinds:
            counts["bad"] += 1
            problems.append(f"{path.stem}: missing origin/evolution")
            continue
        counts["ok"] += 1
    return {"counts": counts, "problems": problems[:40], "out_files": counts["ok"] + counts["bad"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["dump", "apply", "validate"])
    parser.add_argument("--chapter")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if args.command == "dump":
        print(dump_all(args.chapter))
    elif args.command == "validate":
        print(json.dumps(validate_out(), indent=2))
    else:
        print(apply_all(force=args.force))
    return 0


if __name__ == "__main__":
    sys.exit(main())
