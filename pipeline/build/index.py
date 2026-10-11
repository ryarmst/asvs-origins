"""Build derived indexes under build/index/ for the pipeline and the site."""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter, defaultdict

from pipeline.io import load_json, save_json, utc_now
from pipeline.paths import BUILD_DIR, DATA_DIR, ROOT
from pipeline.walk import origin_counts, walk_provenance


WEB_GENERATED = ROOT / "web" / "static" / "generated"


GITHUB_LOGIN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38}$")


def _chapter_sort_key(chapter_id: str) -> tuple[int, str]:
    numeric = "".join(ch for ch in chapter_id if ch.isdigit())
    return (int(numeric) if numeric else 0, chapter_id)


def _requirement_sort_key(req_id: str) -> tuple[int, ...]:
    parts = req_id[1:].split(".")
    return tuple(int(part) for part in parts if part.isdigit())


def _issue_chapters(issue: dict, uid_to_req: dict[str, dict]) -> list[str]:
    chapters: set[str] = set()
    for slice_ in issue.get("requirement_summaries") or []:
        req = uid_to_req.get(slice_.get("requirement_uid") or "")
        if req:
            chapters.add(req["current"]["chapter_id"])
    return sorted(chapters, key=_chapter_sort_key)


def _people_from_records(requirements: list[dict], issues: list[dict]) -> dict[str, dict]:
    people: dict[str, dict] = {}

    def ensure(login: str) -> dict:
        login = (login or "").strip()
        if not GITHUB_LOGIN.match(login):
            return {}
        if login not in people:
            people[login] = {
                "login": login,
                "authored_issues": [],
                "participated_issues": [],
                "reviewed_artifacts": 0,
                "claim_mentions": 0,
                "requirement_ids": [],
            }
        return people[login]

    for issue in issues:
        author = ensure(issue.get("author") or "")
        if author:
            author["authored_issues"].append(issue["number"])
        for login in issue.get("participants") or []:
            row = ensure(login)
            if row:
                row["participated_issues"].append(issue["number"])

    for req in requirements:
        req_id = req["current"]["id"]
        for item in walk_provenance(req):
            prov = item["provenance"]
            for author in prov.get("authors") or []:
                row = ensure(author.get("github") or "")
                if row and req_id not in row["requirement_ids"]:
                    row["requirement_ids"].append(req_id)
            for login in (prov.get("review") or {}).get("by") or []:
                row = ensure(login)
                if row:
                    row["reviewed_artifacts"] += 1
        for claim in (
            list(req.get("decisions") or [])
            + list(req.get("open_questions") or [])
            + list(req.get("terminology") or [])
        ):
            for actor in claim.get("actors") or []:
                row = ensure(actor)
                if row:
                    row["claim_mentions"] += 1
                    if req_id not in row["requirement_ids"]:
                        row["requirement_ids"].append(req_id)

    for issue in issues:
        for claim_holder in issue.get("requirement_summaries") or []:
            for bucket in ("decisions", "arguments", "terminology", "open_questions"):
                for claim in claim_holder.get(bucket) or []:
                    for actor in claim.get("actors") or []:
                        row = ensure(actor)
                        if row:
                            row["claim_mentions"] += 1

    for row in people.values():
        row["authored_issues"] = sorted(set(row["authored_issues"]))
        row["participated_issues"] = sorted(set(row["participated_issues"]))
        row["requirement_ids"].sort(key=_requirement_sort_key)
    return dict(sorted(people.items()))


def _enrichment_state(item: dict) -> str:
    """human | ai_reviewed | ai_draft | extracted | none — from public origin-like artifacts."""
    rank = {"human": 4, "ai_reviewed": 3, "ai_draft": 2, "extracted": 1, "none": 0}
    best = "none"
    for summ in item.get("summaries") or []:
        prov = summ.get("provenance") or {}
        if (prov.get("review") or {}).get("status") == "rejected":
            continue
        origin = prov.get("origin")
        if origin == "human":
            state = "human"
        elif origin == "llm_reviewed":
            state = "ai_reviewed"
        elif origin == "llm":
            state = "ai_draft"
        elif origin == "deterministic":
            state = "extracted"
        else:
            continue
        if rank[state] > rank[best]:
            best = state
    return best


def _ident_score(item: dict, ident: dict) -> int:
    score = {"current": 100, "predecessor": 50, "historical": 10, "deleted": 5}.get(ident.get("status"), 0)
    predecessors = item.get("lineage", {}).get("predecessors") or []
    if any(pred.get("id") == ident.get("id") for pred in predecessors):
        score += 40
    raw = ((item.get("lineage") or {}).get("mapping_entry") or {}).get("raw") or ""
    ident_id = ident.get("id") or ""
    if ident_id and ident_id in raw:
        score += 30
    elif ident_id.startswith("V") and ident_id[1:] in raw:
        score += 30
    return score


def build() -> dict:
    requirements = []
    uid_to_req: dict[str, dict] = {}
    id_to_req: dict[str, dict] = {}
    for path in sorted((DATA_DIR / "requirements").glob("*/*.json")):
        data = load_json(path)
        requirements.append(data)
        uid = data["uid"]
        current_id = data["current"]["id"]
        uid_to_req[uid] = data
        id_to_req[current_id] = data

    uid_map: dict[str, str] = {}
    for data in requirements:
        uid = data["uid"]
        current_id = data["current"]["id"]
        uid_map[current_id] = uid
        uid_map[uid] = uid
        if current_id.startswith("V"):
            uid_map[current_id[1:]] = uid
    for data in requirements:
        uid = data["uid"]
        for ident in data.get("identifiers") or []:
            ident_id = ident.get("id")
            if ident_id:
                uid_map.setdefault(ident_id, uid)
                if ident_id.startswith("V"):
                    uid_map.setdefault(ident_id[1:], uid)

    issues = []
    issues_root = DATA_DIR / "issues"
    if issues_root.exists():
        for path in sorted(issues_root.glob("*.json"), key=lambda item: int(item.stem)):
            issues.append(load_json(path))

    mentions: dict[str, list[dict]] = defaultdict(list)
    for issue in issues:
        for slice_ in issue.get("requirement_summaries") or []:
            uid = slice_.get("requirement_uid")
            if not uid:
                continue
            mentions[uid].append(
                {
                    "issue": issue["number"],
                    "title": issue["title"],
                    "relevance": slice_.get("relevance"),
                    "body": slice_.get("body"),
                    "id": slice_.get("id"),
                }
            )

    coverage_counts = Counter((item.get("status") or {}).get("coverage") for item in requirements)
    lineage_counts = Counter((item.get("status") or {}).get("lineage_state") for item in requirements)
    issue_counts = Counter((item.get("status") or {}).get("coverage") for item in issues)
    authored = coverage_counts.get("authored", 0) + coverage_counts.get("reviewed", 0)
    sourced = sum(1 for item in requirements if item.get("key_sources"))
    total_req = len(requirements) or 1
    bearing_issues = [
        item
        for item in issues
        if (item.get("triage") or {}).get("relevance") == "requirement_bearing"
    ]
    bearing_drafted = sum(
        1 for item in bearing_issues if item["status"]["coverage"] in {"drafted", "reviewed", "authored"}
    )
    coverage = {
        "generated_at": utc_now(),
        "requirements": {
            "total": len(requirements),
            "by_coverage": dict(coverage_counts),
            "reviewed_or_better": authored,
            "reviewed_or_better_pct": round(100 * authored / total_req, 1),
            "lineage_complete": lineage_counts.get("complete", 0),
            "lineage_complete_pct": round(100 * lineage_counts.get("complete", 0) / total_req, 1),
            "sourced": sourced,
            "sourced_pct": round(100 * sourced / total_req, 1),
            "orphans_without_key_sources": sum(
                1 for item in requirements if not item.get("key_sources")
            ),
        },
        "issues": {
            "total": len(issues),
            "by_coverage": dict(issue_counts),
            "requirement_bearing": len(bearing_issues),
            "requirement_bearing_drafted_or_better": bearing_drafted,
        },
        "provenance_mix": origin_counts(requirements + issues),
        "provenance_mix_published": origin_counts(requirements + issues, published_only=True),
    }

    chapters: dict[str, dict] = {}
    for item in requirements:
        chapter_id = item["current"]["chapter_id"]
        section_id = item["current"]["section_id"]
        chapter = chapters.setdefault(
            chapter_id,
            {
                "id": chapter_id,
                "name": item["current"]["chapter_name"],
                "sections": {},
                "requirement_ids": [],
                "by_coverage": Counter(),
            },
        )
        chapter["requirement_ids"].append(item["current"]["id"])
        chapter["by_coverage"][item["status"]["coverage"]] += 1
        section = chapter["sections"].setdefault(
            section_id,
            {
                "id": section_id,
                "name": item["current"]["section_name"],
                "requirement_ids": [],
            },
        )
        section["requirement_ids"].append(item["current"]["id"])

    chapter_list = []
    for chapter_id, chapter in sorted(chapters.items(), key=lambda pair: _chapter_sort_key(pair[0])):
        chapter["requirement_ids"].sort(key=_requirement_sort_key)
        chapter["by_coverage"] = dict(chapter["by_coverage"])
        sections = []
        for section_id, section in sorted(
            chapter["sections"].items(), key=lambda pair: _requirement_sort_key(pair[0] + ".0")
        ):
            section["requirement_ids"].sort(key=_requirement_sort_key)
            sections.append(section)
        chapter["sections"] = sections
        chapter_list.append(chapter)

    legacy: dict[str, dict[str, dict]] = defaultdict(dict)
    legacy_score: dict[tuple[str, str], int] = {}
    for item in requirements:
        target = {"uid": item["uid"], "id": item["current"]["id"], "slug": item["slug"]}
        for ident in item.get("identifiers") or []:
            release = ident.get("release") or "unknown"
            ident_id = ident.get("id")
            if not ident_id:
                continue
            score = _ident_score(item, ident)
            for key in {ident_id, ident_id[1:] if ident_id.startswith("V") else ident_id}:
                prev = legacy_score.get((release, key), -1)
                if score > prev:
                    legacy[release][key] = target
                    legacy_score[(release, key)] = score

    issue_cards = []
    for item in issues:
        uids = [
            slice_["requirement_uid"]
            for slice_ in item.get("requirement_summaries") or []
            if slice_.get("requirement_uid")
        ]
        req_ids = [uid_to_req[uid]["current"]["id"] for uid in uids if uid in uid_to_req]
        issue_cards.append(
            {
                "number": item["number"],
                "title": item["title"],
                "state": item["state"],
                "coverage": item["status"]["coverage"],
                "author": item.get("author"),
                "relevance": (item.get("triage") or {}).get("relevance"),
                "class": (item.get("triage") or {}).get("class"),
                "requirement_ids": req_ids,
                "chapter_ids": _issue_chapters(item, uid_to_req),
            }
        )

    requirement_cards = [
        {
            "uid": item["uid"],
            "id": item["current"]["id"],
            "slug": item["slug"],
            "chapter_id": item["current"]["chapter_id"],
            "chapter_name": item["current"]["chapter_name"],
            "section_id": item["current"]["section_id"],
            "section_name": item["current"]["section_name"],
            "level": item["current"]["level"],
            "coverage": item["status"]["coverage"],
            "lineage_state": item["status"]["lineage_state"],
            "blocked_reason": item["status"].get("blocked_reason"),
            "text": item["current"]["text"],
            "has_origin": any(summ.get("kind") == "origin" for summ in item.get("summaries") or []),
            "key_source_count": len(item.get("key_sources") or []),
            "event_count": len((item.get("lineage") or {}).get("events") or []),
            "enrichment": _enrichment_state(item),
        }
        for item in sorted(requirements, key=lambda row: _requirement_sort_key(row["current"]["id"]))
    ]

    index_dir = BUILD_DIR / "index"
    index_dir.mkdir(parents=True, exist_ok=True)
    save_json(index_dir / "uid-map.json", uid_map)
    save_json(index_dir / "requirements.json", requirement_cards)
    save_json(index_dir / "issues.json", issue_cards)
    save_json(index_dir / "chapters.json", chapter_list)
    save_json(index_dir / "coverage.json", coverage)
    save_json(index_dir / "legacy.json", {key: dict(value) for key, value in legacy.items()})
    save_json(index_dir / "mentions.json", dict(mentions))
    save_json(index_dir / "people.json", _people_from_records(requirements, issues))
    save_json(
        index_dir / "id-to-uid.json",
        {item["current"]["id"]: item["uid"] for item in requirements},
    )
    save_json(
        index_dir / "uid-to-id.json",
        {item["uid"]: item["current"]["id"] for item in requirements},
    )
    pairs = []
    for item in requirements:
        for pred in (item.get("lineage") or {}).get("predecessors") or []:
            pairs.append(
                {
                    "from_release": pred.get("release"),
                    "from_id": pred.get("id"),
                    "to_id": item["current"]["id"],
                    "to_uid": item["uid"],
                    "relation": pred.get("relation"),
                    "from_text": pred.get("text"),
                    "to_text": item["current"]["text"],
                    "note": pred.get("note"),
                    "mapping": (item.get("lineage") or {}).get("mapping_entry"),
                }
            )
    save_json(index_dir / "lineage-pairs.json", pairs)

    from pipeline.build.search import build_search
    from pipeline.mapping import alignment_report, v4_rows

    search_docs = build_search(requirements, issues)
    save_json(index_dir / "search.json", search_docs)
    mapping_v4 = v4_rows()
    mapping_report = alignment_report()
    save_json(index_dir / "mapping-v4.json", mapping_v4)
    save_json(index_dir / "mapping-alignment.json", mapping_report)
    WEB_GENERATED.mkdir(parents=True, exist_ok=True)
    save_json(WEB_GENERATED / "search.json", search_docs)
    save_json(WEB_GENERATED / "coverage.json", coverage)

    return coverage


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    coverage = build()
    req = coverage["requirements"]
    print(
        f"index: requirements={req['total']} issues={coverage['issues']['total']} "
        f"lineage_complete={req['lineage_complete']} "
        f"reviewed_or_better={req['reviewed_or_better']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
