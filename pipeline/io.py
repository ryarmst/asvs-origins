"""JSON load/save and timestamps."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")


def normalize_github_time(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    if value.endswith("+00:00"):
        value = value[:-6] + "Z"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}", value):
        parsed = datetime.fromisoformat(value)
        value = parsed.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if "." in value and value.endswith("Z"):
        value = value.split(".", 1)[0] + "Z"
    return value
