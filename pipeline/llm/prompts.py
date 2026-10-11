"""Load versioned prompt files."""

from __future__ import annotations

from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"

PROMPTS = {
    "triage": ("triage", "v1", "triage.v1.md"),
    "issue-pass": ("issue-pass", "v1", "issue-pass.v1.md"),
    "requirement-pass": ("requirement-pass", "v1", "requirement-pass.v1.md"),
}


def load_prompt(pass_name: str) -> tuple[str, str, str]:
    prompt_id, version, filename = PROMPTS[pass_name]
    text = (PROMPTS_DIR / filename).read_text(encoding="utf-8")
    return prompt_id, version, text
