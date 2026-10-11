"""Copy issue snapshots from asvs-issue-analyze and upsert data/issues stubs."""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

from pipeline.ids import canonical_json, sha256_bytes, sha256_file
from pipeline.io import load_json, normalize_github_time, save_json, utc_now
from pipeline.paths import DATA_DIR, DEFAULT_ISSUE_ANALYZE, ISSUES_DIR, MANIFEST_PATH, SOURCES_DIR
from pipeline.records import empty_issue, is_protected

ISSUE_FILE = re.compile(r"^issue_(\d+)\.json$")
HISTORY_FILE = re.compile(r"^issue_(\d+)_history\.json$")


def _login(value) -> str | None:
    if isinstance(value, dict):
        return value.get("login")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _participants(snapshot: dict) -> list[str]:
    found: set[str] = set()
    author = _login(snapshot.get("author"))
    if author:
        found.add(author)
    for comment in snapshot.get("comments") or []:
        if isinstance(comment, dict):
            login = _login(comment.get("author"))
            if login:
                found.add(login)
    return sorted(found)


def _labels(snapshot: dict) -> list[str]:
    names = []
    for label in snapshot.get("labels") or []:
        if isinstance(label, dict):
            name = label.get("name")
            if name:
                names.append(name)
        elif label:
            names.append(str(label))
    return names


def _state(raw: str) -> str:
    value = (raw or "").lower()
    if value == "open":
        return "open"
    return "closed"


def _copy_issues(src: Path) -> tuple[int, int]:
    json_dir = src / "issues_json"
    if not json_dir.is_dir():
        raise FileNotFoundError(f"no issues_json directory at {json_dir}")
    ISSUES_DIR.mkdir(parents=True, exist_ok=True)
    copied = 0
    histories = 0
    for path in json_dir.iterdir():
        issue_match = ISSUE_FILE.match(path.name)
        hist_match = HISTORY_FILE.match(path.name)
        if issue_match:
            dest = ISSUES_DIR / f"{issue_match.group(1)}.json"
            shutil.copy2(path, dest)
            copied += 1
        elif hist_match:
            dest = ISSUES_DIR / f"{hist_match.group(1)}.history.json"
            shutil.copy2(path, dest)
            histories += 1
    return copied, histories


def _update_manifest() -> int:
    now = utc_now()
    manifest = {"fetched_at": now, "source": "asvs-issue-analyze sync", "files": {}}
    if MANIFEST_PATH.exists():
        previous = load_json(MANIFEST_PATH)
        if previous.get("git"):
            manifest["git"] = previous["git"]
    count = 0
    git_cache = SOURCES_DIR / "git-cache"
    for path in sorted(SOURCES_DIR.rglob("*")):
        if not path.is_file() or path.name == "manifest.json":
            continue
        if git_cache in path.parents or path == git_cache:
            continue
        rel = str(path.relative_to(SOURCES_DIR))
        manifest["files"][rel] = {"digest": sha256_file(str(path)), "fetched_at": now}
        count += 1
    save_json(MANIFEST_PATH, manifest)
    return count


def _upsert_issue(number: int) -> str:
    snapshot_path = ISSUES_DIR / f"{number}.json"
    snapshot = load_json(snapshot_path)
    digest = sha256_bytes(canonical_json(snapshot).encode("utf-8"))
    history_rel = f"sources/issues/{number}.history.json"
    history_path = ISSUES_DIR / f"{number}.history.json"
    dest = DATA_DIR / "issues" / f"{number}.json"
    source = {
        "snapshot": f"sources/issues/{number}.json",
        "snapshot_digest": digest,
        "history_snapshot": history_rel if history_path.exists() else None,
        "fetched_at": utc_now(),
        "comment_count": len(snapshot.get("comments") or []),
        "has_edits": history_path.exists(),
        "previous_digest": None,
    }
    facts = {
        "title": snapshot.get("title") or f"Issue {number}",
        "state": _state(snapshot.get("state") or "closed"),
        "created_at": normalize_github_time(snapshot.get("createdAt")) or utc_now(),
        "closed_at": normalize_github_time(snapshot.get("closedAt")),
        "author": _login(snapshot.get("author")) or "unknown",
        "participants": _participants(snapshot),
        "labels": _labels(snapshot),
        "url": snapshot.get("url") or f"https://github.com/OWASP/ASVS/issues/{number}",
        "source": source,
    }
    if dest.exists():
        data = load_json(dest)
        previous = (data.get("source") or {}).get("snapshot_digest")
        data["title"] = facts["title"]
        data["state"] = facts["state"]
        data["created_at"] = facts["created_at"]
        data["closed_at"] = facts["closed_at"]
        data["author"] = facts["author"]
        data["participants"] = facts["participants"]
        data["labels"] = facts["labels"]
        data["url"] = facts["url"]
        data["source"] = source
        if previous and previous != digest:
            data["source"]["previous_digest"] = previous
            if is_protected(data):
                data["status"]["stale"] = True
        data["status"]["last_pipeline_run"] = utc_now()
        save_json(dest, data)
        return "updated"
    record = empty_issue(
        number=number,
        url=facts["url"],
        title=facts["title"],
        state=facts["state"],
        created_at=facts["created_at"],
        closed_at=facts["closed_at"],
        author=facts["author"],
        participants=facts["participants"],
        labels=facts["labels"],
        source=source,
    )
    save_json(dest, record)
    return "created"


def sync(src: Path) -> dict:
    copied, histories = _copy_issues(src)
    created = 0
    updated = 0
    for path in ISSUES_DIR.glob("*.json"):
        if path.name.endswith(".history.json"):
            continue
        number = int(path.stem)
        result = _upsert_issue(number)
        if result == "created":
            created += 1
        else:
            updated += 1
    files = _update_manifest()
    return {
        "copied": copied,
        "histories": histories,
        "created": created,
        "updated": updated,
        "manifest_files": files,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--from",
        dest="source",
        default=str(DEFAULT_ISSUE_ANALYZE),
        help="Path to asvs-issue-analyze checkout",
    )
    args = parser.parse_args()
    src = Path(args.source)
    stats = sync(src)
    print(
        f"sync_issues: copied={stats['copied']} histories={stats['histories']} "
        f"created={stats['created']} updated={stats['updated']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
