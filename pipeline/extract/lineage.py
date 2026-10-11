"""Deterministic requirement lineage from git history and the v4 mapping."""

from __future__ import annotations

import argparse
import re
import sys
from collections import deque

from pipeline.asvs import V4_CSV, load_requirement_csv, parse_mapping
from pipeline.gitrepo import GitError, pickaxe, repo_ready, show_paths
from pipeline.io import load_json, save_json, utc_now
from pipeline.paths import DATA_DIR, ISSUES_DIR
from pipeline.records import is_protected, mechanical_provenance

ID_TOKEN = re.compile(
    r"\*\*(?:V)?(\d{1,2}\.\d{1,2}(?:\.\d{1,2})?)\*\*|(?:(?<=\s)|(?<=\|))(?:V)?(\d{1,2}\.\d{1,2}\.\d{1,2})(?=\s|\|)"
)
ISSUE_REF = re.compile(r"#(\d{3,5})")
WORD = re.compile(r"[A-Za-z][A-Za-z0-9'-]{2,}")
STOP = {
    "verify",
    "that",
    "the",
    "application",
    "and",
    "for",
    "with",
    "from",
    "this",
    "are",
    "was",
    "not",
    "use",
    "used",
    "using",
    "must",
    "should",
}


def _numeric(req_id: str) -> str:
    return req_id[1:] if req_id.startswith("V") else req_id


def _display(numeric: str) -> str:
    return numeric if numeric.startswith("V") else f"V{numeric}"


def _actor(email: str, name: str) -> str:
    local = (email or "").split("@", 1)[0].strip()
    if local and all(ord(ch) < 128 for ch in local):
        return local
    return name or local or "unknown"


def _phrases(text: str) -> list[str]:
    words = [match.group(0) for match in WORD.finditer(text)]
    useful = [word for word in words if word.lower() not in STOP]
    phrases = []
    for size in (5, 4, 3):
        for index in range(0, max(0, len(useful) - size + 1)):
            phrase = " ".join(useful[index : index + size])
            if len(phrase) >= 12:
                phrases.append(phrase)
        if phrases:
            break
    return phrases[:3]


def _ids_in(text: str) -> set[str]:
    found = set()
    for match in ID_TOKEN.finditer(text):
        token = match.group(1) or match.group(2)
        if token:
            found.add(token)
    return found


def _jaccard(left: str, right: str) -> float:
    a = {word.lower() for word in WORD.findall(left or "")}
    b = {word.lower() for word in WORD.findall(right or "")}
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _classify(subject: str, diff: str, before: set[str], after: set[str]) -> str:
    subj = subject.lower()
    if before and after and before != after:
        if any(token in subj for token in ("renumber", "numeration", "reorder")):
            return "renumbered"
        if "moved" in subj or "MOVED" in diff:
            return "moved"
        return "renumbered"
    if "level" in subj:
        return "level_changed"
    if re.search(r"\badd(ed|ing)?\b", subj) or "[ADDED]" in diff:
        return "added"
    if "merged" in subj or "MERGED FROM" in diff:
        return "merged"
    if "moved" in subj or "[MOVED" in diff:
        return "moved"
    if any(token in subj for token in ("typo", "grammar", "filler", "allowlist throughout")):
        return "grammar"
    if any(token in subj for token in ("placeholder", "temporary column", "clean-up", "cleanup")):
        return "tag_cleanup"
    if "split" in subj:
        return "split"
    return "reworded"


def _id_at_time(after: set[str], needle: str, current: str) -> str:
    if _numeric(current) in after:
        return current if current.startswith("V") else f"V{current}"
    if needle in after:
        return _display(needle)
    if after:
        return _display(sorted(after)[0])
    return _display(needle)


def _id_boundary(needle: str) -> re.Pattern:
    return re.compile(rf"(?<![\d.]){re.escape(needle)}(?![\d.])")


def _needle_in_change(diff: str, needle: str) -> bool:
    matcher = _id_boundary(needle) if " " not in needle else None
    for line in diff.splitlines():
        if not line.startswith(("+", "-")):
            continue
        body = line[1:]
        if matcher:
            if matcher.search(body):
                return True
        elif needle in body:
            return True
    return False


def _row_text_changed(diff: str, needle: str) -> bool:
    matcher = _id_boundary(needle) if " " not in needle else None

    def hit(line: str) -> bool:
        body = line[1:]
        if matcher:
            return matcher.search(body) is not None
        return needle in body

    minus_rows = [line[1:].strip() for line in diff.splitlines() if line.startswith("-") and hit(line)]
    plus_rows = [line[1:].strip() for line in diff.splitlines() if line.startswith("+") and hit(line)]
    if not minus_rows and not plus_rows:
        return False
    return set(minus_rows) != set(plus_rows)


def extract(req_id: str, text: str, mapping: dict | None, extra_ids: list[str] | None = None) -> dict:
    v4_rows = load_requirement_csv(V4_CSV)
    needles: set[str] = {_numeric(req_id)}
    if mapping:
        for v4_id in mapping.get("v4_ids") or []:
            needles.add(_numeric(v4_id))
        pred_text = " ".join(
            (v4_rows.get(item) or {}).get("req_description") or ""
            for item in mapping.get("v4_ids") or []
        )
        for phrase in _phrases(pred_text):
            needles.add(phrase)
    for ident in extra_ids or []:
        token = _numeric(ident)
        if token:
            needles.add(token)
    for phrase in _phrases(text):
        needles.add(phrase)

    commits: dict[str, dict] = {}
    discovered_ids = {item for item in needles if " " not in item}
    target_ids = {item for item in needles if re.fullmatch(r"\d{1,2}(?:\.\d{1,2}){0,2}", item)}
    seen_needles: set[str] = set()
    queue: deque[str] = deque(
        sorted(item for item in needles if " " not in item) + sorted(item for item in needles if " " in item)
    )

    while queue and len(seen_needles) < 24:
        needle = queue.popleft()
        if needle in seen_needles:
            continue
        seen_needles.add(needle)
        use_regex = " " not in needle
        for sha, iso, email, name, subject in pickaxe(needle, "5.0/en", "4.0/en", regex=use_regex):
            diff = show_paths(sha)
            if not _needle_in_change(diff, needle):
                continue
            if not _row_text_changed(diff, needle):
                continue
            minus = _ids_in("\n".join(line[1:] for line in diff.splitlines() if line.startswith("-")))
            plus = _ids_in("\n".join(line[1:] for line in diff.splitlines() if line.startswith("+")))
            changed_ids = minus | plus
            if len(changed_ids) > 25:
                if not (changed_ids & target_ids):
                    continue
                if not minus or not plus:
                    continue
            for token in changed_ids:
                if not re.fullmatch(r"\d{1,2}\.\d{1,2}\.\d{1,2}", token):
                    continue
                if token not in discovered_ids and len(discovered_ids) < 20:
                    discovered_ids.add(token)
                    queue.append(token)
            issues = [
                int(match)
                for match in ISSUE_REF.findall(subject)
                if (ISSUES_DIR / f"{match}.json").exists()
            ]
            kind = _classify(subject, diff, minus, plus)
            date = iso[:10]
            commits[sha] = {
                "date": date,
                "kind": kind,
                "commit": sha[:8],
                "actor": _actor(email, name),
                "id_at_time": _id_at_time(plus, needle if "." in needle else _numeric(req_id), req_id),
                "summary": (subject.strip() or "(no commit message)")[:240],
                "citations": [{"type": "commit", "url": f"https://github.com/OWASP/ASVS/commit/{sha[:8]}", "commit": sha[:8]}]
                + [
                    {
                        "type": "issue_body",
                        "url": f"https://github.com/OWASP/ASVS/issues/{number}",
                        "issue": number,
                    }
                    for number in issues
                ],
            }

    events = sorted(commits.values(), key=lambda item: (item["date"], item["commit"]))
    git_v4 = {f"V{token}" for token in discovered_ids if f"V{token}" in v4_rows}
    map_v4 = set((mapping or {}).get("v4_ids") or [])
    raw = (mapping or {}).get("raw") or ""
    agrees = True
    note = None
    if map_v4:
        pred_text = " ".join((v4_rows.get(item) or {}).get("req_description") or "" for item in map_v4)
        if pred_text and _jaccard(text, pred_text) < 0.22:
            agrees = False
            note = "Mapping predecessor text is dissimilar to the current requirement; git/content lineage diverges from the ID slot."
        elif map_v4 and git_v4 and not (map_v4 & git_v4) and "ADDED" not in raw:
            agrees = False
            note = "Mapping predecessor IDs were not observed in git pickaxe results."
    origin = "new_in_release" if raw.startswith("ADDED") and "FROM" not in raw else None
    return {
        "events": events,
        "discovered_ids": sorted(discovered_ids),
        "git_v4": sorted(git_v4),
        "agrees_with_git": agrees,
        "note": note,
        "origin_kind": origin,
    }


def extra_ids_for(data: dict) -> list[str]:
    ids = []
    for item in data.get("identifiers") or []:
        if item.get("id"):
            ids.append(item["id"])
    for item in (data.get("lineage") or {}).get("predecessors") or []:
        if item.get("id"):
            ids.append(item["id"])
    return ids


def apply_to_record(data: dict, extracted: dict, mapping: dict | None) -> None:
    if is_protected(data):
        return
    lineage = data.setdefault("lineage", {})
    lineage["events"] = extracted["events"]
    if mapping and lineage.get("mapping_entry"):
        lineage["mapping_entry"]["agrees_with_git"] = extracted["agrees_with_git"]
        if extracted["note"]:
            lineage["mapping_entry"]["note"] = extracted["note"]
    elif mapping and not lineage.get("mapping_entry"):
        lineage["mapping_entry"] = {
            "raw": mapping.get("raw") or "",
            "status": mapping.get("status") or "",
            "agrees_with_git": extracted["agrees_with_git"],
            "note": extracted["note"],
        }
    existing_ids = {(item.get("release"), item.get("id")) for item in data.get("identifiers") or []}
    for token in extracted["discovered_ids"]:
        if "." not in token:
            continue
        display = _display(token)
        if display == data["current"]["id"]:
            continue
        release = "4.0.3" if display in extracted["git_v4"] else "pre-release"
        status = "predecessor" if release == "4.0.3" else "historical"
        key = (release, display)
        if key not in existing_ids:
            data.setdefault("identifiers", []).append(
                {"release": release, "id": display, "level": None, "status": status}
            )
            existing_ids.add(key)
    lineage["provenance"] = mechanical_provenance("Git pickaxe + mapping cross-check.")
    if extracted["events"]:
        data["status"]["lineage_state"] = "complete"
        if data["status"]["coverage"] == "empty":
            data["status"]["coverage"] = "linked"
    elif mapping:
        data["status"]["lineage_state"] = "partial"
    data["status"]["last_pipeline_run"] = utc_now()


def run_all(only: list[str] | None = None, resume: bool = False) -> dict:
    if not repo_ready():
        raise GitError("ASVS git cache missing; run python -m pipeline.ingest.sync_git")
    mapping = parse_mapping()
    processed = 0
    skipped = 0
    skipped_done = 0
    for path in sorted((DATA_DIR / "requirements").glob("*/*.json")):
        data = load_json(path)
        req_id = data["current"]["id"]
        if only and req_id not in only:
            continue
        if is_protected(data):
            skipped += 1
            continue
        if resume and (data.get("lineage") or {}).get("events") and data["status"].get("lineage_state") == "complete":
            skipped_done += 1
            continue
        extra = extra_ids_for(data)
        extracted = extract(req_id, data["current"]["text"], mapping.get(req_id), extra)
        apply_to_record(data, extracted, mapping.get(req_id))
        save_json(path, data)
        processed += 1
        print(f"lineage {req_id}: events={len(extracted['events'])}", flush=True)
    return {"processed": processed, "skipped_protected": skipped, "skipped_done": skipped_done}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", nargs="*", help="Requirement IDs to extract, e.g. V1.3.6")
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip unprotected records that already have complete lineage events",
    )
    args = parser.parse_args()
    stats = run_all(args.only, resume=args.resume)
    print(
        f"lineage: processed={stats['processed']} skipped_protected={stats['skipped_protected']} "
        f"skipped_done={stats['skipped_done']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
