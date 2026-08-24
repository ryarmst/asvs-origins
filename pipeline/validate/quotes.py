"""Verbatim quote checks against sources/ snapshots."""

from __future__ import annotations

import re
import sys

from pipeline.validate.schema import ROOT, SOURCES_DIR, iter_data_files, load_json

MAX_QUOTE_WORDS = 25


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _snapshot_text(number: int) -> tuple[str | None, dict | None]:
    path = SOURCES_DIR / "issues" / f"{number}.json"
    if not path.exists():
        return None, None
    data = load_json(path)
    parts = [data.get("title") or "", data.get("body") or ""]
    comments = data.get("comments") or []
    for comment in comments:
        if isinstance(comment, dict):
            parts.append(comment.get("body") or "")
        else:
            parts.append(str(comment))
    return _normalize("\n".join(parts)), data


def _history_edited_ids(number: int) -> set[str]:
    path = SOURCES_DIR / "issues" / f"{number}.history.json"
    if not path.exists():
        return set()
    data = load_json(path)
    edited = set()
    for item in data.get("edited_comments") or []:
        comment_id = item.get("id") or item.get("comment_id")
        if comment_id:
            edited.add(str(comment_id))
    return edited


def validate_all() -> list[str]:
    errors: list[str] = []
    snapshot_cache: dict[int, tuple[str | None, dict | None]] = {}

    for kind, path in iter_data_files():
        rel = str(path.relative_to(ROOT))
        data = load_json(path)
        seen_comment_quotes: set[tuple[int, str]] = set()
        for node in _walk(data):
            if not isinstance(node, dict):
                continue
            quote = node.get("quote")
            if not quote or node.get("type") not in {
                "issue_body",
                "issue_comment",
                "pr_body",
                "pr_review_comment",
            }:
                continue
            words = quote.split()
            if len(words) > MAX_QUOTE_WORDS:
                errors.append(
                    f"{rel}: quote exceeds {MAX_QUOTE_WORDS} words ({len(words)}): {quote!r}"
                )
            issue_number = node.get("issue")
            if issue_number is None and node.get("url"):
                match = re.search(r"/issues/(\d+)", node["url"])
                if match:
                    issue_number = int(match.group(1))
            if not isinstance(issue_number, int):
                errors.append(f"{rel}: quoted citation is missing issue number")
                continue
            if issue_number not in snapshot_cache:
                snapshot_cache[issue_number] = _snapshot_text(issue_number)
            text, _ = snapshot_cache[issue_number]
            if text is None:
                errors.append(f"{rel}: no source snapshot for quoted issue {issue_number}")
                continue
            if _normalize(quote) not in text:
                errors.append(
                    f"{rel}: quote not found verbatim in sources/issues/{issue_number}.json: {quote!r}"
                )
            comment_id = str(node.get("comment_id") or "")
            if comment_id:
                key = (issue_number, comment_id)
                if key in seen_comment_quotes:
                    errors.append(
                        f"{rel}: more than one quote cites issue {issue_number} comment {comment_id}"
                    )
                seen_comment_quotes.add(key)
    return errors


def main() -> int:
    errors = validate_all()
    if errors:
        print(f"quotes: {len(errors)} error(s)")
        for error in errors:
            print(error)
        return 1
    print("quotes: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
