"""MiniSearch documents for the static site."""

from __future__ import annotations


def _summary_text(summaries: list[dict] | None) -> str:
    parts = []
    for item in summaries or []:
        if (item.get("provenance") or {}).get("review", {}).get("status") == "rejected":
            continue
        kind = item.get("kind") or ""
        body = item.get("body") or ""
        if body:
            parts.append(f"{kind} {body}")
    return " ".join(parts)


def _claim_text(*groups: list[dict] | None) -> str:
    parts = []
    for group in groups:
        for item in group or []:
            statement = item.get("statement") or ""
            if statement:
                parts.append(statement)
    return " ".join(parts)


def _identifier_text(identifiers: list[dict] | None) -> str:
    return " ".join(
        f"{item.get('release') or ''} {item.get('id') or ''}".strip()
        for item in identifiers or []
        if item.get("id")
    )


def build_search(requirements: list[dict], issues: list[dict]) -> list[dict]:
    documents: list[dict] = []
    for item in requirements:
        current = item.get("current") or {}
        req_id = current.get("id") or item.get("id")
        documents.append(
            {
                "id": f"req:{req_id}",
                "kind": "requirement",
                "title": f"{req_id} {(item.get('slug') or '').replace('-', ' ')}",
                "text": " ".join(
                    part
                    for part in [
                        req_id,
                        current.get("chapter_name") or item.get("chapter_name") or "",
                        current.get("section_name") or item.get("section_name") or "",
                        current.get("text") or item.get("text") or "",
                        _identifier_text(item.get("identifiers")),
                        _summary_text(item.get("summaries")),
                        _claim_text(item.get("decisions"), item.get("open_questions"), item.get("terminology")),
                    ]
                    if part
                ),
                "href": f"/requirements/{req_id}",
                "chapter": current.get("chapter_id") or item.get("chapter_id"),
                "coverage": (item.get("status") or {}).get("coverage") or item.get("coverage"),
            }
        )
    for issue in issues:
        triage = issue.get("triage") or {}
        slices = " ".join(
            f"{slice_.get('requirement_id_at_time') or ''} {slice_.get('body') or ''}"
            for slice_ in issue.get("requirement_summaries") or []
        )
        documents.append(
            {
                "id": f"issue:{issue['number']}",
                "kind": "issue",
                "title": f"#{issue['number']} {issue['title']}",
                "text": " ".join(
                    part
                    for part in [
                        issue["title"],
                        issue.get("author") or "",
                        " ".join(issue.get("labels") or []),
                        _summary_text(issue.get("summaries")),
                        triage.get("reason") or "",
                        triage.get("class") or "",
                        triage.get("relevance") or "",
                        slices,
                    ]
                    if part
                ),
                "href": f"/issues/{issue['number']}",
                "chapter": None,
                "coverage": issue["status"]["coverage"],
            }
        )
    return documents
