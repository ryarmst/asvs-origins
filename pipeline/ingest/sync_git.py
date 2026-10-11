"""Maintain a local clone of OWASP/ASVS for lineage extraction."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from pipeline.io import load_json, save_json, utc_now
from pipeline.paths import GIT_CACHE, MANIFEST_PATH

REMOTE = "https://github.com/OWASP/ASVS.git"


def _run(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)


def _tag(repo: Path, pattern: str) -> str | None:
    result = _run(["git", "tag", "-l", pattern], cwd=repo)
    tags = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    preferred = [tag for tag in tags if tag.endswith("_release") or tag in {"v5.0.0", "v4.0.3"}]
    if preferred:
        return sorted(preferred)[-1]
    return tags[-1] if tags else None


def sync() -> dict:
    GIT_CACHE.parent.mkdir(parents=True, exist_ok=True)
    if not ((GIT_CACHE / ".git").exists() or (GIT_CACHE / "HEAD").exists()):
        # Full history is required for pickaxe (`git log -S`). A blobless clone
        # can return empty pickaxe results because blobs are not present locally.
        GIT_CACHE.parent.mkdir(parents=True, exist_ok=True)
        _run(
            [
                "git",
                "clone",
                "--single-branch",
                "--no-tags",
                REMOTE,
                str(GIT_CACHE),
            ]
        )
    else:
        _run(["git", "fetch", "origin", "--tags"], cwd=GIT_CACHE)
        default_ref = "origin/master"
        show = subprocess.run(
            ["git", "rev-parse", "--verify", "origin/master"],
            cwd=GIT_CACHE,
            capture_output=True,
            text=True,
        )
        if show.returncode != 0:
            default_ref = "origin/main"
        _run(["git", "reset", "--hard", default_ref], cwd=GIT_CACHE)

    _run(["git", "fetch", "origin", "--tags"], cwd=GIT_CACHE)
    head = _run(["git", "rev-parse", "HEAD"], cwd=GIT_CACHE).stdout.strip()
    v5 = _tag(GIT_CACHE, "*5.0.0*")
    v4 = _tag(GIT_CACHE, "*4.0.3*")
    git_info = {
        "head": head,
        "v5_tag": v5,
        "v4_tag": v4,
        "fetched_at": utc_now(),
        "path": "sources/git-cache/ASVS",
    }
    manifest = {}
    if MANIFEST_PATH.exists():
        manifest = load_json(MANIFEST_PATH)
    manifest["git"] = git_info
    manifest["fetched_at"] = utc_now()
    save_json(MANIFEST_PATH, manifest)
    return git_info


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    info = sync()
    print(
        f"sync_git: head={info['head'][:12]} v5={info['v5_tag']} v4={info['v4_tag']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
