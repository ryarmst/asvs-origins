"""Run all ingest steps."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pipeline.ingest import sync_asvs, sync_git, sync_issues
from pipeline.paths import DEFAULT_ISSUE_ANALYZE


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from", dest="source", default=str(DEFAULT_ISSUE_ANALYZE))
    parser.add_argument("--skip-git", action="store_true")
    args = parser.parse_args()
    sync_asvs.sync()
    sync_issues.sync(Path(args.source))
    if not args.skip_git:
        sync_git.sync()
    return 0


if __name__ == "__main__":
    sys.exit(main())
