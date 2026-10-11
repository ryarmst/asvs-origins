"""Run deterministic extractors."""

from __future__ import annotations

import argparse
import sys

from pipeline.extract import lineage, req_references


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", nargs="*", help="Limit lineage extraction to these requirement IDs")
    parser.add_argument("--resume", action="store_true", help="Skip records that already have complete lineage")
    parser.add_argument("--skip-references", action="store_true")
    args = parser.parse_args()
    lineage.run_all(args.only, resume=args.resume)
    if not args.skip_references:
        req_references.run_all()
    return 0


if __name__ == "__main__":
    sys.exit(main())
