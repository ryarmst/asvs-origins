"""Thin git wrapper around the OWASP/ASVS cache."""

from __future__ import annotations

import re
import subprocess
from functools import lru_cache
from pathlib import Path

from pipeline.paths import GIT_CACHE


class GitError(RuntimeError):
    pass


def repo_ready() -> bool:
    return (GIT_CACHE / ".git").exists() or (GIT_CACHE / "HEAD").exists()


def git(*args: str, cwd: Path | None = None) -> str:
    result = subprocess.run(
        ["git", "-C", str(cwd or GIT_CACHE), *args],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise GitError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout


def pickaxe(needle: str, *paths: str, regex: bool = False) -> list[tuple[str, str, str, str, str]]:
    """Return (hash, iso-date, email, name, subject) for commits that touch needle."""
    path_tuple = tuple(paths) if paths else ("5.0/en", "4.0/en")
    return _pickaxe(needle, path_tuple, regex)


@lru_cache(maxsize=2048)
def _pickaxe(needle: str, paths: tuple[str, ...], regex: bool) -> list[tuple[str, str, str, str, str]]:
    if not needle or len(needle) < 3:
        return []
    flag = "-G" if regex else "-S"
    value = re.escape(needle) if regex else needle
    try:
        out = git(
            "log",
            "--format=%H%x09%aI%x09%ae%x09%an%x09%s",
            flag,
            value,
            "--",
            *paths,
        )
    except GitError:
        return []
    rows = []
    for line in out.splitlines():
        parts = line.split("\t", 4)
        if len(parts) == 5:
            rows.append(tuple(parts))  # type: ignore[arg-type]
    return rows


@lru_cache(maxsize=512)
def show_paths(commit: str) -> str:
    try:
        return git("show", "--format=", commit, "--", "5.0/en", "4.0/en")
    except GitError:
        return ""


def head_short() -> str:
    return git("rev-parse", "--short=8", "HEAD").strip()
