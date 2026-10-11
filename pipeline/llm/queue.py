"""Build a maintainer review queue (CLI; the editor lands in M3)."""

from __future__ import annotations

import argparse
import sys

from pipeline.io import load_json, save_json, utc_now
from pipeline.llm.context import load_chapter_requirements
from pipeline.paths import BUILD_DIR, DATA_DIR
from pipeline.walk import walk_provenance


def build_queue(chapter: str | None = None) -> dict:
    items = []
    req_root = DATA_DIR / "requirements"
    paths = []
    if chapter:
        paths.extend(sorted((req_root / chapter).glob("*.json")))
    else:
        paths.extend(sorted(req_root.glob("*/*.json")))
    for path in paths:
        data = load_json(path)
        req_id = data["current"]["id"]
        if data["status"].get("stale") and data["status"].get("coverage") in {"reviewed", "authored"}:
            items.append(
                {
                    "priority": 1,
                    "kind": "requirement",
                    "id": req_id,
                    "reason": "stale accepted record",
                    "coverage": data["status"]["coverage"],
                }
            )
        for block in walk_provenance(data):
            prov = block["provenance"]
            if prov.get("origin") == "llm" and (prov.get("review") or {}).get("status") == "unreviewed":
                supersedes = None
                items.append(
                    {
                        "priority": 2 if "supersedes" in block["path"] else 4,
                        "kind": "requirement",
                        "id": req_id,
                        "reason": f"unreviewed {prov.get('origin')} at {block['path']}",
                        "coverage": data["status"]["coverage"],
                        "confidence": prov.get("confidence"),
                    }
                )
        if data["status"]["coverage"] in {"empty", "linked"}:
            items.append(
                {
                    "priority": 5,
                    "kind": "requirement",
                    "id": req_id,
                    "reason": "not yet drafted",
                    "coverage": data["status"]["coverage"],
                }
            )
    issues_root = DATA_DIR / "issues"
    for path in sorted(issues_root.glob("*.json")):
        data = load_json(path)
        triage = data.get("triage") or {}
        if triage.get("relevance") == "no_requirement" and data["number"] % 20 == 0:
            items.append(
                {
                    "priority": 6,
                    "kind": "issue",
                    "id": data["number"],
                    "reason": "5% sample of no_requirement triage",
                    "coverage": data["status"]["coverage"],
                }
            )
        if data["status"]["coverage"] != "drafted":
            continue
        if chapter:
            uids = {item["uid"] for item in load_chapter_requirements(chapter)}
            if not any(rs.get("requirement_uid") in uids for rs in data.get("requirement_summaries") or []):
                continue
        items.append(
            {
                "priority": 4,
                "kind": "issue",
                "id": data["number"],
                "reason": "drafted issue awaiting review",
                "coverage": data["status"]["coverage"],
            }
        )
    items.sort(key=lambda item: (item["priority"], str(item["id"])))
    # De-duplicate requirement rows that listed every unreviewed block.
    seen = set()
    unique = []
    for item in items:
        key = (item["kind"], item["id"], item["reason"][:24])
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    queue = {"generated_at": utc_now(), "chapter": chapter, "items": unique}
    out = BUILD_DIR / "index"
    out.mkdir(parents=True, exist_ok=True)
    name = f"review-queue-{chapter}.json" if chapter else "review-queue.json"
    save_json(out / name, queue)
    return queue


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chapter", default="V9")
    args = parser.parse_args()
    queue = build_queue(args.chapter)
    print(f"review queue: {len(queue['items'])} item(s) -> build/index/review-queue-{args.chapter}.json")
    for item in queue["items"][:30]:
        print(f"  p{item['priority']} {item['kind']} {item['id']}: {item['reason']}")
    if len(queue["items"]) > 30:
        print(f"  … {len(queue['items']) - 30} more")
    return 0


if __name__ == "__main__":
    sys.exit(main())
