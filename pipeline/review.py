"""Apply maintainer review actions and write corpus JSON."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from pipeline.ids import mint_sub_id
from pipeline.io import load_json, save_json, utc_now
from pipeline.paths import DATA_DIR, ROOT
from pipeline.validate import quotes, schema
from pipeline.walk import resolve_path, walk_provenance

LOCKED_ORIGINS = {"human"}
LOCKED_REVIEW = {"accepted"}


def reviewer_from_env() -> tuple[str, str]:
    github = os.environ.get("ASVS_ORIGINS_GITHUB") or os.environ.get("ASVS_ORIGINS_REVIEWER") or ""
    name = os.environ.get("ASVS_ORIGINS_NAME") or github
    return github, name


def record_path(kind: str, ident: str) -> Path:
    if kind == "requirement":
        chapter = ident.split(".", 1)[0]
        path = DATA_DIR / "requirements" / chapter / f"{ident}.json"
        if not path.exists():
            raise FileNotFoundError(f"no requirement record for {ident}")
        return path
    if kind == "issue":
        path = DATA_DIR / "issues" / f"{ident}.json"
        if not path.exists():
            raise FileNotFoundError(f"no issue record for {ident}")
        return path
    raise ValueError(f"unsupported kind {kind}")


def load_record(kind: str, ident: str) -> tuple[Path, dict]:
    path = record_path(kind, ident)
    return path, load_json(path)


def artifacts(record: dict) -> list[dict]:
    items = []
    for block in walk_provenance(record):
        path = block["path"]
        if path.endswith("/provenance"):
            artifact_path = path[: -len("/provenance")]
        else:
            artifact_path = path
        parent, _, node = resolve_path(record, artifact_path)
        preview = ""
        if isinstance(node, dict):
            preview = node.get("body") or node.get("statement") or node.get("reason") or ""
        items.append(
            {
                "path": artifact_path,
                "provenance_path": path if path.endswith("/provenance") else f"{artifact_path}/provenance",
                "preview": preview[:240],
                "kind": node.get("kind") if isinstance(node, dict) else None,
                "provenance": block["provenance"],
            }
        )
    # De-duplicate when both the artifact and its provenance node were walked.
    seen = set()
    unique = []
    for item in items:
        key = item["path"]
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def _stamp_review(provenance: dict, *, status: str, github: str, note: str | None, now: str) -> None:
    by = list(provenance.get("review", {}).get("by") or [])
    if github not in by:
        by.append(github)
    provenance["review"] = {
        "status": status,
        "by": by,
        "at": now,
        "note": note,
    }
    provenance["updated_at"] = now


def _ensure_reviewer_author(provenance: dict, github: str, name: str) -> None:
    authors = list(provenance.get("authors") or [])
    if any(author.get("github") == github for author in authors):
        provenance["authors"] = authors
        return
    authors.append({"name": name or github, "github": github})
    provenance["authors"] = authors


def apply_action(
    record: dict,
    *,
    path: str,
    action: str,
    github: str,
    name: str,
    note: str | None = None,
    body: str | None = None,
    statement: str | None = None,
    citations: list | None = None,
    kind: str | None = None,
) -> dict:
    if not github:
        raise ValueError("reviewer GitHub login is required")
    now = utc_now()
    if action == "write":
        return _write_human(
            record,
            path=path,
            github=github,
            name=name,
            body=body,
            now=now,
            kind=kind,
            citations=citations,
        )

    parent, key, node = resolve_path(record, path)
    if not isinstance(node, dict):
        raise ValueError(f"path {path} does not point at an object")

    provenance = node.get("provenance")
    if provenance is None and "origin" in node and "review" in node:
        provenance = node
    if not isinstance(provenance, dict):
        raise ValueError(f"path {path} has no provenance")
    if provenance.get("origin") in LOCKED_ORIGINS and action != "flag":
        raise ValueError("human artifacts are not rewritten by review actions; use write")
    if (provenance.get("review") or {}).get("status") in LOCKED_REVIEW and action in {"accept", "reject"}:
        raise ValueError("accepted artifacts are locked")

    if action == "accept":
        if body is not None and "body" in node:
            node["body"] = body
        if statement is not None and "statement" in node:
            node["statement"] = statement
        if citations is not None and "citations" in node:
            node["citations"] = citations
        if provenance.get("origin") == "llm":
            provenance["origin"] = "llm_reviewed"
        if provenance.get("origin") == "llm_reviewed":
            _ensure_reviewer_author(provenance, github, name)
        _stamp_review(provenance, status="accepted", github=github, note=note, now=now)
    elif action == "reject":
        _stamp_review(provenance, status="rejected", github=github, note=note, now=now)
    elif action == "flag":
        _stamp_review(provenance, status="changes_requested", github=github, note=note, now=now)
    else:
        raise ValueError(f"unknown action {action}")

    _refresh_coverage(record, now)
    return record


def _write_human(
    record: dict,
    *,
    path: str,
    github: str,
    name: str,
    body: str | None,
    now: str,
    kind: str | None = None,
    citations: list | None = None,
) -> dict:
    if not body or not body.strip():
        raise ValueError("write requires a body")
    parent, key, node = resolve_path(record, path)
    if not isinstance(node, list):
        raise ValueError("write path must be a summaries array")
    if not kind:
        kind = "overview"
        if path.endswith("summaries") and record.get("kind") != "issue":
            kind = "origin" if not any(item.get("kind") == "origin" for item in node) else "evolution"
    allowed = {"origin", "evolution", "overview", "interpretation", "controversy"}
    if kind not in allowed:
        raise ValueError(f"unsupported summary kind {kind}")
    summary = {
        "id": mint_sub_id("sum", kind, body[:80], github),
        "kind": kind,
        "body": body.strip(),
        "citations": citations or [],
        "supersedes": None,
        "provenance": {
            "origin": "human",
            "created_at": now,
            "updated_at": now,
            "authors": [{"name": name or github, "github": github}],
            "model": None,
            "review": {
                "status": "accepted",
                "by": [github],
                "at": now,
                "note": None,
            },
            "input_digest": None,
            "confidence": "high",
        },
    }
    node.append(summary)
    _refresh_coverage(record, now)
    return record


def _refresh_coverage(record: dict, now: str) -> None:
    status = record.get("status")
    if not isinstance(status, dict):
        return
    current = status.get("coverage")
    if current == "authored":
        status["last_human_review"] = now
        return
    pending = False
    accepted = False
    for item in artifacts(record):
        path = item["path"]
        if path.startswith("lineage"):
            continue
        prov = item["provenance"]
        origin = prov.get("origin")
        review = (prov.get("review") or {}).get("status")
        if origin == "deterministic":
            continue
        if origin == "human" or review == "accepted":
            accepted = True
            continue
        if review == "rejected":
            continue
        pending = True
    if accepted and not pending:
        status["coverage"] = "reviewed"
        status["last_human_review"] = now
        status["stale"] = False
    elif accepted:
        status["last_human_review"] = now


def validate_record(kind: str, record: dict, rel: str) -> list[str]:
    errors = schema.validate_instance(kind, record, rel)
    errors.extend(quotes.validate_record(record, rel))
    return errors


def save_record(kind: str, ident: str, record: dict) -> Path:
    path = record_path(kind, ident)
    rel = str(path.relative_to(ROOT))
    errors = validate_record(kind, record, rel)
    if errors:
        raise ValueError("\n".join(errors))
    save_json(path, record)
    return path


def run_action(payload: dict) -> dict:
    kind = payload["kind"]
    ident = str(payload["id"])
    github = payload.get("github") or reviewer_from_env()[0]
    name = payload.get("name") or reviewer_from_env()[1]
    path, record = load_record(kind, ident)
    apply_action(
        record,
        path=payload["path"],
        action=payload["action"],
        github=github,
        name=name,
        note=payload.get("note"),
        body=payload.get("body"),
        statement=payload.get("statement"),
        citations=payload.get("citations"),
        kind=payload.get("summary_kind") or payload.get("summaryKind"),
    )
    save_record(kind, ident, record)
    return {"ok": True, "path": str(path.relative_to(ROOT)), "record": record}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="read one JSON payload from stdin")
    parser.add_argument("--kind")
    parser.add_argument("--id")
    parser.add_argument("--path")
    parser.add_argument("--action")
    parser.add_argument("--note")
    parser.add_argument("--body")
    parser.add_argument("--github")
    parser.add_argument("--name")
    args = parser.parse_args()
    if args.json:
        payload = json.load(sys.stdin)
    else:
        payload = {
            "kind": args.kind,
            "id": args.id,
            "path": args.path,
            "action": args.action,
            "note": args.note,
            "body": args.body,
            "github": args.github,
            "name": args.name,
        }
    try:
        result = run_action(payload)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1
    print(json.dumps({"ok": True, "path": result["path"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
