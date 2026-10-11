"""Assemble LLM pass inputs from the corpus and snapshots."""

from __future__ import annotations

import re
from pipeline.io import load_json
from pipeline.paths import BUILD_DIR, DATA_DIR, ISSUES_DIR

BULK_SUBJECT = re.compile(
    r"step \d|renumber|temporary column|language support|copy current id",
    re.I,
)
STRONG_RULES = {"versioned:5.0.0", "versioned:4.0.3", "versioned:pre-release", "v-prefix"}


def load_chapter_requirements(chapter: str) -> list[dict]:
    root = DATA_DIR / "requirements" / chapter
    return [load_json(path) for path in sorted(root.glob("*.json"))]


def compact_asvs_context() -> list[dict]:
    rows = []
    seen = set()
    for path in sorted((DATA_DIR / "requirements").glob("*/*.json")):
        data = load_json(path)
        current = data["current"]
        key = (current["chapter_id"], current["section_id"])
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "chapter_id": current["chapter_id"],
                "chapter_name": current["chapter_name"],
                "section_id": current["section_id"],
                "section_name": current["section_name"],
            }
        )
    return rows


def chapter_issue_numbers(chapter: str) -> list[int]:
    reqs = load_chapter_requirements(chapter)
    ids = {item["current"]["id"] for item in reqs}
    uids = {item["uid"] for item in reqs}
    numbers: set[int] = set()
    candidates_root = BUILD_DIR / "candidates"
    if candidates_root.exists():
        for path in candidates_root.glob("issue-*.json"):
            data = load_json(path)
            if any(_strong_hit(hit, ids, uids) for hit in data.get("candidates") or []):
                numbers.add(int(data["issue"]))
    for req in reqs:
        for event in req.get("lineage", {}).get("events") or []:
            subject = event.get("summary") or ""
            if BULK_SUBJECT.search(subject):
                continue
            if event.get("kind") in {"renumbered", "tag_cleanup"}:
                continue
            for cite in event.get("citations") or []:
                if cite.get("issue"):
                    numbers.add(int(cite["issue"]))
    return sorted(numbers)


def _strong_hit(hit: dict, ids: set[str], uids: set[str]) -> bool:
    if hit.get("requirement_id") not in ids and hit.get("requirement_uid") not in uids:
        return False
    if hit.get("relevance") in {"primary", "secondary"}:
        return True
    if (hit.get("confidence") or 0) >= 0.5:
        return True
    rule = hit.get("rule") or ""
    return rule in STRONG_RULES or rule.startswith("versioned:")


def issue_candidates(number: int, chapter: str | None = None) -> list[dict]:
    path = BUILD_DIR / "candidates" / f"issue-{number}.json"
    if not path.exists():
        return []
    data = load_json(path)
    hits = data.get("candidates") or []
    if not chapter:
        return hits
    reqs = {item["current"]["id"]: item for item in load_chapter_requirements(chapter)}
    uids = {item["uid"]: item for item in reqs.values()}
    out = []
    seen = set()
    for hit in hits:
        rec = reqs.get(hit.get("requirement_id")) or uids.get(hit.get("requirement_uid"))
        if not rec or rec["uid"] in seen:
            continue
        seen.add(rec["uid"])
        out.append(
            {
                "uid": rec["uid"],
                "id": rec["current"]["id"],
                "chapter": rec["current"]["chapter_id"],
                "section": rec["current"]["section_id"],
                "level": rec["current"]["level"],
                "text": rec["current"]["text"],
                "matched": hit.get("matched"),
                "confidence": hit.get("confidence"),
                "relevance": hit.get("relevance"),
            }
        )
    # Lineage-cited issues may have no candidate row; still offer the chapter.
    if not out:
        for rec in reqs.values():
            out.append(
                {
                    "uid": rec["uid"],
                    "id": rec["current"]["id"],
                    "chapter": rec["current"]["chapter_id"],
                    "section": rec["current"]["section_id"],
                    "level": rec["current"]["level"],
                    "text": rec["current"]["text"],
                    "matched": None,
                    "confidence": 0.2,
                    "relevance": "mentioned",
                }
            )
    return out


def compact_snapshot(number: int, body_limit: int | None = None) -> dict:
    snapshot = load_json(ISSUES_DIR / f"{number}.json")
    comments = []
    for comment in snapshot.get("comments") or []:
        if not isinstance(comment, dict):
            continue
        author = comment.get("author") or {}
        login = author.get("login") if isinstance(author, dict) else author
        comments.append(
            {
                "url": comment.get("url"),
                "author": login,
                "createdAt": comment.get("createdAt"),
                "body": comment.get("body") or "",
            }
        )
    body = snapshot.get("body") or ""
    if body_limit is not None:
        body = body[:body_limit]
    labels = []
    for label in snapshot.get("labels") or []:
        if isinstance(label, dict):
            labels.append(label.get("name") or "")
        else:
            labels.append(str(label))
    author = snapshot.get("author") or {}
    login = author.get("login") if isinstance(author, dict) else author
    return {
        "number": snapshot.get("number") or number,
        "url": snapshot.get("url") or f"https://github.com/OWASP/ASVS/issues/{number}",
        "title": snapshot.get("title") or "",
        "state": snapshot.get("state") or "",
        "author": login,
        "createdAt": snapshot.get("createdAt"),
        "labels": labels,
        "body": body,
        "comments": comments,
    }


def edit_history_note(number: int) -> dict | None:
    path = ISSUES_DIR / f"{number}.history.json"
    if not path.exists():
        return None
    data = load_json(path)
    edited = data.get("edited_comments") or []
    return {
        "edited_comment_count": len(edited),
        "edited_comment_ids": [item.get("id") or item.get("comment_id") for item in edited[:20]],
    }


def compact_lineage(req: dict, limit: int = 24) -> list[dict]:
    events = []
    for event in req.get("lineage", {}).get("events") or []:
        if event.get("kind") in {"renumbered", "tag_cleanup"}:
            continue
        events.append(
            {
                "date": event.get("date"),
                "kind": event.get("kind"),
                "commit": event.get("commit"),
                "actor": event.get("actor"),
                "id_at_time": event.get("id_at_time"),
                "summary": event.get("summary"),
                "citations": event.get("citations") or [],
            }
        )
        if len(events) >= limit:
            break
    return events
