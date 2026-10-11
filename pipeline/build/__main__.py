"""Build site indexes and search documents."""

from __future__ import annotations

import argparse
import sys

from pipeline.build.index import build


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    coverage = build()
    req = coverage["requirements"]
    print(
        f"build: requirements={req['total']} issues={coverage['issues']['total']} "
        f"lineage_complete={req['lineage_complete']} "
        f"reviewed_or_better={req['reviewed_or_better']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
