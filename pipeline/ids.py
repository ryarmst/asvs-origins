"""Stable identifiers for ASVS Origins records."""

from __future__ import annotations

import hashlib
import json
from typing import Any


UID_NAMESPACE = "asvs-origins:uid:5.0.0:"


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def mint_uid(requirement_id: str) -> str:
    """Mint a stable requirement uid from the 5.0.0 identifier.

    The uid is assigned once at import and never regenerated from later IDs.
    """
    payload = f"{UID_NAMESPACE}{requirement_id}".encode("utf-8")
    return "req-" + hashlib.sha256(payload).hexdigest()[:8]


def mint_sub_id(prefix: str, *parts: str) -> str:
    payload = "asvs-origins:sub:" + prefix + ":" + ":".join(parts)
    return f"{prefix}-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:6]
