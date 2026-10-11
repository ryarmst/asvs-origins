"""Official v4↔v5 mapping views and disagreement reports."""

from __future__ import annotations

from pipeline.asvs import parse_mapping, parse_v4_mapping, V4_CSV, load_requirement_csv
from pipeline.io import load_json
from pipeline.paths import DATA_DIR

ASVS_DEV_V4 = "https://asvs.dev/mapping_v4.0.3_to_v5.0.0.html"
ASVS_DEV_V5 = "https://asvs.dev/mapping_v5.0.0_to_v4.0.3.html"
GITHUB_V4 = "https://github.com/OWASP/ASVS/blob/master/5.0/mappings/mapping_v4.0.3_to_v5.0.0.yml"
GITHUB_V5 = "https://github.com/OWASP/ASVS/blob/master/5.0/mappings/mapping_v5.0.0_to_v4.0.3.yml"


def _sort_id(req_id: str) -> tuple[int, ...]:
    parts = req_id[1:].split(".")
    return tuple(int(part) for part in parts if part.isdigit())


def v4_rows() -> list[dict]:
    v5 = parse_mapping()
    v4 = parse_v4_mapping()
    csv_rows = load_requirement_csv(V4_CSV)
    reverse: dict[str, list[str]] = {}
    for v5_id, entry in v5.items():
        for v4_id in entry.get("v4_ids") or []:
            reverse.setdefault(v4_id, []).append(v5_id)
    rows = []
    for v4_id, entry in sorted(v4.items(), key=lambda item: _sort_id(item[0])):
        csv = csv_rows.get(v4_id) or csv_rows.get(v4_id[1:]) or {}
        text = (csv.get("req_description") or "").strip()
        rows.append(
            {
                "from_id": v4_id,
                "from_text": text or None,
                "raw": entry["raw"],
                "status": entry["status"],
                "to_ids": entry.get("v5_ids") or [],
                "deleted": entry["status"] == "DELETED" or entry["raw"].startswith("DELETED"),
                "v5_yaml_backrefs": sorted(set(reverse.get(v4_id) or []), key=_sort_id),
            }
        )
    return rows


def alignment_report() -> dict:
    """Compare the two official YAML files with the corpus predecessors."""
    v5 = parse_mapping()
    v4 = parse_v4_mapping()
    yaml_mismatches = []
    for v5_id, entry in v5.items():
        for v4_id in entry.get("v4_ids") or []:
            peer = v4.get(v4_id)
            if not peer:
                yaml_mismatches.append(
                    {
                        "kind": "v4_missing",
                        "v5_id": v5_id,
                        "v4_id": v4_id,
                        "detail": f"{v5_id} maps from {v4_id}, which is absent from the v4→v5 file.",
                    }
                )
                continue
            if v5_id not in (peer.get("v5_ids") or []):
                yaml_mismatches.append(
                    {
                        "kind": "asymmetric",
                        "v5_id": v5_id,
                        "v4_id": v4_id,
                        "detail": (
                            f"{v5_id} lists {v4_id}, but {v4_id} maps to "
                            f"{', '.join(peer.get('v5_ids') or []) or '(none)'}."
                        ),
                    }
                )
    for v4_id, entry in v4.items():
        if entry["status"] == "DELETED" or entry["raw"].startswith("DELETED"):
            continue
        for v5_id in entry.get("v5_ids") or []:
            peer = v5.get(v5_id)
            if not peer:
                yaml_mismatches.append(
                    {
                        "kind": "v5_missing",
                        "v5_id": v5_id,
                        "v4_id": v4_id,
                        "detail": f"{v4_id} maps to {v5_id}, which is absent from the v5→v4 file.",
                    }
                )
                continue
            if v4_id not in (peer.get("v4_ids") or []):
                yaml_mismatches.append(
                    {
                        "kind": "asymmetric",
                        "v5_id": v5_id,
                        "v4_id": v4_id,
                        "detail": (
                            f"{v4_id} lists {v5_id}, but {v5_id} maps from "
                            f"{', '.join(peer.get('v4_ids') or []) or '(none)'}."
                        ),
                    }
                )

    git_disagreements = []
    for path in sorted((DATA_DIR / "requirements").glob("*/*.json")):
        data = load_json(path)
        mapping = (data.get("lineage") or {}).get("mapping_entry") or {}
        if mapping.get("agrees_with_git") is False:
            note = mapping.get("note") or ""
            kind = "content_divergent"
            lowered = note.lower()
            if "misleading" in lowered or "replaced" in lowered or "not in v5" in lowered:
                kind = "stale_slot"
            elif "not observed in git" in lowered:
                kind = "id_divergent"
            git_disagreements.append(
                {
                    "id": data["current"]["id"],
                    "uid": data["uid"],
                    "raw": mapping.get("raw"),
                    "note": mapping.get("note"),
                    "kind": kind,
                }
            )

    stale = [item for item in git_disagreements if item["kind"] == "stale_slot"]
    return {
        "source": {
            "asvs_dev_v4": ASVS_DEV_V4,
            "asvs_dev_v5": ASVS_DEV_V5,
            "github_v4": GITHUB_V4,
            "github_v5": GITHUB_V5,
        },
        "counts": {
            "v5_entries": len(v5),
            "v4_entries": len(v4),
            "v4_deleted": sum(
                1 for item in v4.values() if item["status"] == "DELETED" or item["raw"].startswith("DELETED")
            ),
            "yaml_mismatches": len(yaml_mismatches),
            "git_disagreements": len(git_disagreements),
            "stale_slots": len(stale),
        },
        "yaml_mismatches": yaml_mismatches,
        "stale_slots": stale,
        "git_disagreements": git_disagreements,
    }
