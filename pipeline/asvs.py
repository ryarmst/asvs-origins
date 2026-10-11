"""ASVS CSV and mapping parsers, plus slug minting."""

from __future__ import annotations

import csv
import re
from functools import lru_cache
from pathlib import Path

from pipeline.ids import mint_uid
from pipeline.paths import ASVS_DIR

V5_CSV = ASVS_DIR / "asvs_5.0.0.csv"
V4_CSV = ASVS_DIR / "asvs_4.0.3.csv"
LATEST_CSV = ASVS_DIR / "asvs_latest.csv"
MAPPING_YAML = ASVS_DIR / "mapping_v5.0.0_to_v4.0.3.yml"
MAPPING_V4_YAML = ASVS_DIR / "mapping_v4.0.3_to_v5.0.0.yml"

PREFIXES = (
    "verify that the application ",
    "verify that ",
    "verify the application ",
    "verify ",
)

SLUG_STRIP = re.compile(r"[^a-z0-9]+")
V4_REF = re.compile(r"v4\.0\.3-(\d+\.\d+\.\d+)", re.IGNORECASE)
V5_REF = re.compile(r"v5\.0\.0-(\d+\.\d+\.\d+)", re.IGNORECASE)
STATUS_WORD = re.compile(r"\b(ADDED|MODIFIED|MOVED|SPLIT|MERGED|GRAMMAR|COVERS|DELETED|LEVEL)\b")


@lru_cache(maxsize=8)
def load_requirement_csv(path: Path) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            req_id = (row.get("req_id") or "").strip()
            if not req_id:
                continue
            rows[req_id] = row
    return rows


def v5_level(row: dict) -> int | None:
    raw = (row.get("L") or "").strip()
    return int(raw) if raw.isdigit() else None


def v4_level(row: dict) -> int | None:
    if (row.get("level1") or "").strip():
        return 1
    if (row.get("level2") or "").strip():
        return 2
    if (row.get("level3") or "").strip():
        return 3
    return None


def _parse_mapping_yaml(path: Path, *, key_prefix: str, peer_ref: re.Pattern[str]) -> dict[str, dict]:
    """Parse an official ASVS mapping YAML into {V1.3.6: {raw, status, peer_ids}}."""
    text = path.read_text(encoding="utf-8")
    entries: dict[str, dict] = {}
    current: str | None = None
    raw_parts: list[str] = []

    def flush() -> None:
        nonlocal current, raw_parts
        if current is None:
            return
        raw = " ".join(part.strip() for part in raw_parts if part.strip())
        raw = re.sub(r"\s+", " ", raw).strip().strip(",")
        peer_ids = [f"V{m.group(1)}" for m in peer_ref.finditer(raw)]
        status_match = STATUS_WORD.search(raw)
        status = status_match.group(1) if status_match else raw.split(",", 1)[0].strip()
        entries[current] = {"raw": raw, "status": status, "peer_ids": peer_ids}
        current = None
        raw_parts = []

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(key_prefix) and stripped.endswith(":"):
            flush()
            numeric = stripped.split(":", 1)[0].removeprefix(key_prefix).strip()
            current = f"V{numeric}"
            raw_parts = []
            continue
        if current is None:
            continue
        if "tag-v" in line and ":" in line:
            raw_parts.append(line.split(":", 1)[1])
        elif line.startswith(" ") and raw_parts:
            raw_parts.append(line)
    flush()
    return entries


def parse_mapping(path: Path = MAPPING_YAML) -> dict[str, dict]:
    """Parse mapping_v5.0.0_to_v4.0.3.yml into {V1.3.6: {raw, status, v4_ids}}."""
    entries = _parse_mapping_yaml(path, key_prefix="v5.0.0-", peer_ref=V4_REF)
    return {
        req_id: {"raw": item["raw"], "status": item["status"], "v4_ids": item["peer_ids"]}
        for req_id, item in entries.items()
    }


def parse_v4_mapping(path: Path = MAPPING_V4_YAML) -> dict[str, dict]:
    """Parse mapping_v4.0.3_to_v5.0.0.yml into {V5.2.6: {raw, status, v5_ids}}."""
    entries = _parse_mapping_yaml(path, key_prefix="v4.0.3-", peer_ref=V5_REF)
    return {
        req_id: {"raw": item["raw"], "status": item["status"], "v5_ids": item["peer_ids"]}
        for req_id, item in entries.items()
    }


def mapping_origin_kind(entry: dict | None) -> str:
    if not entry:
        return "unknown"
    raw = entry.get("raw") or ""
    if "MERGED FROM" in raw:
        return "merged_from"
    if "SPLIT FROM" in raw:
        return "split_from"
    if raw.startswith("ADDED") and "FROM" not in raw:
        return "new_in_release"
    if "MOVED FROM" in raw or raw.startswith("MODIFIED") or raw.startswith("GRAMMAR"):
        return "carried_forward"
    return "unknown"


def mapping_relation(raw: str) -> str:
    if "MERGED FROM" in raw:
        return "merged"
    if "SPLIT FROM" in raw:
        return "split"
    if raw.startswith("GRAMMAR"):
        return "grammar"
    if "LEVEL CHANGE" in raw:
        return "level_change"
    if "MOVED FROM" in raw and "MODIFIED" not in raw:
        return "moved"
    return "modified"


def slugify(text: str, fallback: str) -> str:
    lowered = text.strip().lower()
    for prefix in PREFIXES:
        if lowered.startswith(prefix):
            lowered = lowered[len(prefix) :]
            break
    lowered = lowered.split(".")[0]
    lowered = SLUG_STRIP.sub("-", lowered).strip("-")
    words = [part for part in lowered.split("-") if part and part not in {"a", "an", "the", "and", "or", "of", "to", "for", "in", "by", "with", "is", "are", "be", "that", "this"}]
    slug = "-".join(words[:8]) or fallback.lower().replace(".", "-")
    slug = slug[:80].strip("-")
    if len(slug) < 3:
        slug = (slug + "-" + fallback.lower().replace(".", "-")).strip("-")[:80]
    return slug


def unique_slug(text: str, req_id: str, taken: set[str]) -> str:
    base = slugify(text, req_id)
    slug = base
    if slug not in taken:
        taken.add(slug)
        return slug
    suffix = mint_uid(req_id)[-4:]
    slug = f"{base[:75]}-{suffix}".strip("-")
    n = 2
    while slug in taken:
        slug = f"{base[:70]}-{suffix}-{n}"
        n += 1
    taken.add(slug)
    return slug
