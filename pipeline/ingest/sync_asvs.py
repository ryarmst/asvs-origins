"""Import ASVS 5.0.0 / latest / 4.0.3 tables into data/requirements."""

from __future__ import annotations

import argparse
import sys

from pipeline.asvs import (
    LATEST_CSV,
    MAPPING_YAML,
    V4_CSV,
    V5_CSV,
    load_requirement_csv,
    mapping_origin_kind,
    mapping_relation,
    parse_mapping,
    unique_slug,
    v4_level,
    v5_level,
)
from pipeline.ids import mint_uid
from pipeline.io import load_json, save_json, utc_now, utc_today
from pipeline.paths import DATA_DIR
from pipeline.records import empty_requirement, is_protected, mechanical_provenance

PROTECTED_LINEAGE = {"complete", "disputed"}


def _current_from_row(row: dict) -> dict:
    return {
        "release": "5.0.0",
        "id": row["req_id"],
        "chapter_id": row["chapter_id"],
        "chapter_name": row["chapter_name"],
        "section_id": row["section_id"],
        "section_name": row["section_name"],
        "level": v5_level(row),
        "text": row["req_description"],
        "source": "sources/asvs/asvs_5.0.0.csv",
        "status": "current",
    }


def _master_from_row(row: dict, release_row: dict) -> dict:
    text = row["req_description"]
    level = v5_level(row)
    return {
        "id": row["req_id"],
        "level": level,
        "text": text,
        "differs_from_release": text != release_row["req_description"] or level != v5_level(release_row),
        "checked_at": utc_today(),
    }


def _predecessors(req_id: str, mapping: dict, v4_rows: dict) -> list[dict]:
    entry = mapping.get(req_id)
    if not entry:
        return []
    out = []
    for v4_id in entry["v4_ids"]:
        row = v4_rows.get(v4_id)
        out.append(
            {
                "release": "4.0.3",
                "id": v4_id,
                "relation": mapping_relation(entry["raw"]),
                "text": (row or {}).get("req_description") or None,
                "note": None,
            }
        )
    return out


def _identifiers(req_id: str, row: dict, mapping: dict, v4_rows: dict) -> list[dict]:
    items = [
        {
            "release": "5.0.0",
            "id": req_id,
            "level": v5_level(row),
            "status": "current",
        }
    ]
    entry = mapping.get(req_id) or {}
    for v4_id in entry.get("v4_ids") or []:
        v4 = v4_rows.get(v4_id) or {}
        items.append(
            {
                "release": "4.0.3",
                "id": v4_id,
                "level": v4_level(v4) if v4 else None,
                "status": "predecessor",
            }
        )
    return items


def _mapping_entry(req_id: str, mapping: dict) -> dict | None:
    entry = mapping.get(req_id)
    if not entry:
        return None
    return {
        "raw": entry["raw"],
        "status": entry["status"],
        "agrees_with_git": True,
        "note": None,
    }


def _merge_identifiers(existing: list[dict], incoming: list[dict]) -> list[dict]:
    seen = {(item.get("release"), item.get("id")) for item in existing}
    merged = list(existing)
    for item in incoming:
        key = (item.get("release"), item.get("id"))
        if key not in seen:
            merged.append(item)
            seen.add(key)
    return merged


def _requirement_path(req_id: str) -> "Path":
    from pathlib import Path

    chapter = req_id.split(".")[0]
    return DATA_DIR / "requirements" / chapter / f"{req_id}.json"


def load_existing() -> dict[str, dict]:
    records = {}
    root = DATA_DIR / "requirements"
    if not root.exists():
        return records
    for path in root.glob("*/*.json"):
        data = load_json(path)
        records[data["current"]["id"]] = data
        records[data["uid"]] = data
    return records


def sync() -> dict:
    v5 = load_requirement_csv(V5_CSV)
    latest = load_requirement_csv(LATEST_CSV)
    v4 = load_requirement_csv(V4_CSV)
    mapping = parse_mapping(MAPPING_YAML)
    existing_by_id = {}
    taken_slugs: set[str] = set()
    for path in (DATA_DIR / "requirements").glob("*/*.json"):
        data = load_json(path)
        existing_by_id[data["current"]["id"]] = {"path": path, "data": data}
        taken_slugs.add(data["slug"])

    created = 0
    updated = 0
    protected = 0
    for req_id, row in sorted(v5.items(), key=lambda item: item[0]):
        latest_row = latest.get(req_id, row)
        path = _requirement_path(req_id)
        found = existing_by_id.get(req_id)
        current = _current_from_row(row)
        master = _master_from_row(latest_row, row)
        identifiers = _identifiers(req_id, row, mapping, v4)
        if found:
            data = found["data"]
            data["current"] = current
            data["master"] = master
            data["identifiers"] = _merge_identifiers(data.get("identifiers") or [], identifiers)
            data["status"]["last_pipeline_run"] = utc_now()
            if is_protected(data):
                protected += 1
            else:
                if not data.get("lineage", {}).get("mapping_entry"):
                    data["lineage"]["mapping_entry"] = _mapping_entry(req_id, mapping)
                if data["lineage"].get("origin_kind") in {None, "unknown"}:
                    data["lineage"]["origin_kind"] = mapping_origin_kind(mapping.get(req_id))
                if not data["lineage"].get("predecessors"):
                    data["lineage"]["predecessors"] = _predecessors(req_id, mapping, v4)
                if data["status"]["coverage"] == "empty" and data["lineage"].get("mapping_entry"):
                    data["status"]["coverage"] = "linked"
            save_json(path, data)
            updated += 1
            continue

        uid = mint_uid(req_id)
        slug = unique_slug(row["req_description"], req_id, taken_slugs)
        lineage = {
            "origin_kind": mapping_origin_kind(mapping.get(req_id)),
            "predecessors": _predecessors(req_id, mapping, v4),
            "mapping_entry": _mapping_entry(req_id, mapping),
            "events": [],
            "provenance": mechanical_provenance("Imported from ASVS CSVs and mapping YAML."),
        }
        record = empty_requirement(
            uid=uid,
            slug=slug,
            current=current,
            master=master,
            identifiers=identifiers,
            lineage=lineage,
        )
        if record["lineage"]["mapping_entry"]:
            record["status"]["coverage"] = "linked"
        save_json(path, record)
        created += 1

    deleted = 0
    for req_id, item in existing_by_id.items():
        if req_id in v5:
            continue
        data = item["data"]
        data["current"]["status"] = "deleted"
        data["status"]["last_pipeline_run"] = utc_now()
        save_json(item["path"], data)
        deleted += 1

    return {
        "created": created,
        "updated": updated,
        "protected": protected,
        "deleted_marked": deleted,
        "total_v5": len(v5),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    stats = sync()
    print(
        f"sync_asvs: created={stats['created']} updated={stats['updated']} "
        f"protected={stats['protected']} deleted={stats['deleted_marked']} v5={stats['total_v5']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
