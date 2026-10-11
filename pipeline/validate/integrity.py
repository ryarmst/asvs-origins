"""Cross-file referential integrity checks."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import urlparse

from pipeline.validate.schema import ROOT, SOURCES_DIR, iter_data_files, load_json

COMMIT_URL = re.compile(
    r"^https://github\.com/OWASP/ASVS/commit/[0-9a-f]{7,40}$", re.IGNORECASE
)
ISSUE_URL = re.compile(
    r"^https://github\.com/OWASP/ASVS/issues/(\d+)(?:#issuecomment-\d+)?$",
    re.IGNORECASE,
)
PR_URL = re.compile(
    r"^https://github\.com/OWASP/ASVS/pull/(\d+)(?:#(?:issuecomment|discussion_r)-\d+)?$",
    re.IGNORECASE,
)

ID_PREFIX = {
    "decision": "dec-",
    "argument": "arg-",
    "terminology": "trm-",
    "open_question": "oq-",
}


def _walk(value, path=""):
    if isinstance(value, dict):
        yield path, value
        for key, child in value.items():
            yield from _walk(child, f"{path}/{key}" if path else key)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk(child, f"{path}/{index}")


def _collect_records() -> tuple[dict, list[tuple[str, Path, dict]]]:
    records: list[tuple[str, Path, dict]] = []
    for kind, path in iter_data_files():
        records.append((kind, path, load_json(path)))
    return records


def validate_all() -> list[str]:
    errors: list[str] = []
    records = _collect_records()
    if not records:
        return ["no corpus files found under data/"]

    requirements = [item for item in records if item[0] == "requirement"]
    uids: dict[str, Path] = {}
    slugs: dict[str, Path] = {}
    for _, path, data in requirements:
        uid = data.get("uid")
        slug = data.get("slug")
        if uid in uids:
            errors.append(f"{path.relative_to(ROOT)}: duplicate uid {uid} (also {uids[uid]})")
        else:
            uids[uid] = path.relative_to(ROOT)
        if slug in slugs:
            errors.append(f"{path.relative_to(ROOT)}: duplicate slug {slug} (also {slugs[slug]})")
        else:
            slugs[slug] = path.relative_to(ROOT)

    for kind, path, data in records:
        rel = path.relative_to(ROOT)
        for location, node in _walk(data):
            if "requirement_uid" in node:
                ref = node["requirement_uid"]
                if ref not in uids:
                    errors.append(f"{rel}:{location}: unknown requirement_uid {ref}")
            if node.get("kind") in ID_PREFIX and "id" in node and "statement" in node:
                expected = ID_PREFIX[node["kind"]]
                if not str(node["id"]).startswith(expected):
                    errors.append(
                        f"{rel}:{location}: claim id {node['id']} does not match kind {node['kind']}"
                    )
            if "url" in node and node.get("type") in {
                "issue_body",
                "issue_comment",
                "pr_body",
                "pr_review_comment",
                "commit",
                "mapping",
                "release_note",
                "external",
            }:
                errors.extend(_check_citation(rel, location, node))

            origin = node.get("origin")
            if origin in {"human", "llm", "llm_reviewed", "deterministic"}:
                authors = node.get("authors") or []
                model = node.get("model")
                if origin in {"llm", "deterministic"} and authors:
                    errors.append(f"{rel}:{location}: {origin} provenance must not have authors")
                if origin in {"human", "llm_reviewed"} and not authors:
                    errors.append(f"{rel}:{location}: {origin} provenance requires authors")
                if origin in {"human", "deterministic"} and model is not None:
                    errors.append(f"{rel}:{location}: {origin} provenance must not set model")

    return errors


def _check_citation(rel: Path, location: str, node: dict) -> list[str]:
    errors: list[str] = []
    url = node.get("url") or ""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        errors.append(f"{rel}:{location}: citation url is not well-formed: {url}")
        return errors
    ctype = node["type"]
    if ctype == "commit":
        if not COMMIT_URL.match(url):
            errors.append(f"{rel}:{location}: commit citation url must be an OWASP/ASVS commit: {url}")
    elif ctype in {"issue_body", "issue_comment"}:
        match = ISSUE_URL.match(url.split("#")[0] + (
            "#" + url.split("#", 1)[1] if "#" in url else ""
        ))
        if not match:
            # Allow body URLs without fragment.
            match = re.match(
                r"^https://github\.com/OWASP/ASVS/issues/(\d+)$", url, re.IGNORECASE
            )
        if not match:
            errors.append(f"{rel}:{location}: issue citation url is not an OWASP/ASVS issue: {url}")
        else:
            number = int(match.group(1))
            snapshot = SOURCES_DIR / "issues" / f"{number}.json"
            if not snapshot.exists():
                errors.append(
                    f"{rel}:{location}: cited issue {number} has no snapshot at {snapshot.relative_to(ROOT)}"
                )
    elif ctype in {"pr_body", "pr_review_comment"}:
        if not PR_URL.match(url) and not re.match(
            r"^https://github\.com/OWASP/ASVS/pull/\d+$", url, re.IGNORECASE
        ):
            errors.append(f"{rel}:{location}: pull request citation url is not an OWASP/ASVS PR: {url}")
        # Local PR snapshots are optional until selective PR ingest (M1).
    return errors


def main() -> int:
    errors = validate_all()
    if errors:
        print(f"integrity: {len(errors)} error(s)")
        for error in errors:
            print(error)
        return 1
    print("integrity: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
