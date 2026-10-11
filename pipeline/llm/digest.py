"""Input digests for LLM idempotency."""

from __future__ import annotations

from typing import Any

from pipeline.ids import canonical_json, sha256_bytes


def input_digest(primary: Any, *, prompt_id: str, prompt_version: str, provider: str, model_id: str) -> str:
    payload = canonical_json(
        {
            "primary": primary,
            "prompt_id": prompt_id,
            "prompt_version": prompt_version,
            "provider": provider,
            "model_id": model_id,
        }
    )
    return sha256_bytes(payload.encode("utf-8"))
