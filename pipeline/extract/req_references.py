"""Scan issue snapshots for ASVS requirement identifiers."""

from __future__ import annotations

import argparse
import re
import sys

from pipeline.asvs import parse_mapping
from pipeline.io import load_json, save_json
from pipeline.paths import BUILD_DIR, DATA_DIR, ISSUES_DIR

VERSIONED = [
    (re.compile(r"\bv?5\.0\.0-(\d{1,2}\.\d{1,2}\.\d{1,2})\b", re.I), "5.0.0"),
    (re.compile(r"\bv?5\.0\.be-(\d{1,2}\.\d{1,2}\.\d{1,2})\b", re.I), "pre-release"),
    (re.compile(r"\bv?4\.0\.3-(\d{1,2}\.\d{1,2}\.\d{1,2})\b", re.I), "4.0.3"),
]
V_FULL = re.compile(r"\bV(\d{1,2}\.\d{1,2}\.\d{1,2})\b")
BARE = re.compile(r"(?<![\w.])(\d{1,2}\.\d{1,2}\.\d{1,2})(?![\w.])")
V_SECTION = re.compile(r"\bV(\d{1,2}\.\d{1,2})\b")
V_CHAPTER = re.compile(r"\bV(\d{1,2})\b")
LABEL_CHAPTER = re.compile(r"^V(\d+)")
CONTEXT_HINT = re.compile(r"\bV\d|\bASVS\b|5\.0/en/|4\.0/en/", re.I)

# 5.0.0 released 30 May 2025. Unprefixed IDs before this more often mean 4.x.
V5_RELEASE = "2025-05-30"


def _load_indexes() -> dict:
    current_ids: set[str] = set()
    id_to_current: dict[str, set[str]] = {}
    id_to_uid: dict[str, str] = {}
    by_chapter: dict[str, list[str]] = {}
    by_section: dict[str, list[str]] = {}
    mapping = parse_mapping()
    for path in (DATA_DIR / "requirements").glob("*/*.json"):
        data = load_json(path)
        uid = data["uid"]
        current = data["current"]["id"]
        current_ids.add(current)
        id_to_uid[current] = uid
        id_to_uid[_numeric(current)] = uid
        id_to_current.setdefault(current, set()).add(current)
        id_to_current.setdefault(_numeric(current), set()).add(current)
        chapter = current.split(".")[0]
        section = ".".join(current.split(".")[:2])
        by_chapter.setdefault(chapter, []).append(current)
        by_section.setdefault(section, []).append(current)
        for ident in data.get("identifiers") or []:
            ident_id = ident.get("id")
            if not ident_id:
                continue
            id_to_current.setdefault(ident_id, set()).add(current)
            id_to_current.setdefault(_numeric(ident_id), set()).add(current)
            id_to_uid.setdefault(ident_id, uid)
            id_to_uid.setdefault(_numeric(ident_id), uid)
        mapped = mapping.get(current) or {}
        for v4_id in mapped.get("v4_ids") or []:
            id_to_current.setdefault(v4_id, set()).add(current)
            id_to_current.setdefault(_numeric(v4_id), set()).add(current)
    return {
        "current_ids": current_ids,
        "id_to_current": id_to_current,
        "id_to_uid": id_to_uid,
        "by_chapter": by_chapter,
        "by_section": by_section,
    }


def _numeric(req_id: str) -> str:
    return req_id[1:] if req_id.startswith("V") else req_id


def _resolve(token: str, table: dict, created: str, version: str | None) -> list[str]:
    display = token if token.startswith("V") else f"V{token}"
    numeric = _numeric(token)
    keys = [display, numeric]
    hits: list[str] = []
    for key in keys:
        for current in sorted(table["id_to_current"].get(key) or []):
            if current not in hits:
                hits.append(current)
    if version == "5.0.0":
        return [item for item in hits if item in table["current_ids"]]
    return hits


def _hint(text: str, labels: list[str]) -> bool:
    if CONTEXT_HINT.search(text or ""):
        return True
    return any(LABEL_CHAPTER.match(label) for label in labels)


def scan_issue(snapshot: dict, table: dict) -> list[dict]:
    created = (snapshot.get("createdAt") or "")[:10]
    labels = [
        label.get("name") if isinstance(label, dict) else str(label)
        for label in snapshot.get("labels") or []
    ]
    blobs = [("title", snapshot.get("title") or "", None)]
    blobs.append(("body", snapshot.get("body") or "", None))
    for comment in snapshot.get("comments") or []:
        if isinstance(comment, dict):
            blobs.append(("comment", comment.get("body") or "", comment.get("url")))
    combined = "\n".join(blob[1] for blob in blobs)
    has_hint = _hint(combined, labels)
    found: list[dict] = []
    seen: set[tuple] = set()

    def add(matched: str, req_ids: list[str], where: str, url: str | None, rule: str, confidence: float, relevance: str) -> None:
        for req_id in req_ids:
            key = (req_id, where, matched)
            if key in seen:
                continue
            seen.add(key)
            uid = table["id_to_uid"].get(req_id) or table["id_to_uid"].get(_numeric(req_id))
            if not uid:
                continue
            found.append(
                {
                    "matched": matched,
                    "requirement_id": req_id,
                    "requirement_uid": uid,
                    "where": where,
                    "url": url,
                    "rule": rule,
                    "confidence": round(confidence, 2),
                    "relevance": relevance,
                }
            )

    for where, text, url in blobs:
        base = 0.9 if where == "title" else 0.7 if where == "body" else 0.5
        for pattern, version in VERSIONED:
            for match in pattern.finditer(text):
                req_ids = _resolve(match.group(1), table, created, version)
                add(match.group(0), req_ids, where, url, f"versioned:{version}", min(1.0, base + 0.2), "primary" if where == "title" else "secondary")
        for match in V_FULL.finditer(text):
            req_ids = _resolve(match.group(1), table, created, None)
            add(match.group(0), req_ids, where, url, "v-prefix", base, "primary" if where == "title" else "secondary")
        if has_hint:
            for match in BARE.finditer(text):
                req_ids = _resolve(match.group(1), table, created, None)
                add(match.group(0), req_ids, where, url, "bare", max(0.2, base - 0.3), "mentioned")
        for match in V_SECTION.finditer(text):
            section = f"V{match.group(1)}"
            reqs = table["by_section"].get(section) or []
            if 0 < len(reqs) <= 8:
                add(match.group(0), reqs, where, url, "section", 0.35, "mentioned")
        for match in V_CHAPTER.finditer(text):
            chapter = f"V{match.group(1)}"
            reqs = table["by_chapter"].get(chapter) or []
            if 0 < len(reqs) <= 8:
                add(match.group(0), reqs, where, url, "chapter", 0.25, "mentioned")

    for label in labels:
        match = LABEL_CHAPTER.match(label)
        if not match:
            continue
        chapter = f"V{match.group(1)}"
        reqs = table["by_chapter"].get(chapter) or []
        if 0 < len(reqs) <= 8:
            add(label, reqs, "label", None, "chapter-label", 0.4, "mentioned")
    return found


def run_all() -> dict:
    table = _load_indexes()
    out_dir = BUILD_DIR / "candidates"
    out_dir.mkdir(parents=True, exist_ok=True)
    issues = 0
    links = 0
    for path in sorted(ISSUES_DIR.glob("*.json")):
        if path.name.endswith(".history.json"):
            continue
        snapshot = load_json(path)
        number = int(path.stem)
        candidates = scan_issue(snapshot, table)
        save_json(out_dir / f"issue-{number}.json", {"issue": number, "candidates": candidates})
        issues += 1
        links += len(candidates)
        dest = DATA_DIR / "issues" / f"{number}.json"
        if dest.exists() and candidates:
            record = load_json(dest)
            if record.get("status", {}).get("coverage") == "empty":
                record["status"]["coverage"] = "linked"
                save_json(dest, record)
    return {"issues": issues, "candidates": links}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    stats = run_all()
    print(f"req_references: issues={stats['issues']} candidates={stats['candidates']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
