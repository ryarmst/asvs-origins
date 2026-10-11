"""Run LLM enrichment passes. Provider-agnostic; no vendor policy."""

from __future__ import annotations

import argparse
import sys

from pipeline.llm import pass_a, pass_b, pass_c, queue


def _chapters(requested: str) -> list[str]:
    if requested.lower() in {"all", "*"}:
        from pipeline.paths import DATA_DIR

        return sorted(
            path.name
            for path in (DATA_DIR / "requirements").iterdir()
            if path.is_dir()
        )
    return [requested]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chapter", default="V9")
    parser.add_argument("--pass", dest="passes", action="append", choices=["a", "b", "c", "queue"])
    parser.add_argument("--limit", type=int, help="Cap Pass A/B issue count")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    selected = args.passes or ["a", "b", "c"]
    for chapter in _chapters(args.chapter):
        print(f"== {chapter} ==", flush=True)
        if "a" in selected:
            print(pass_a.run_chapter(chapter, limit=args.limit, force=args.force))
        if "b" in selected:
            print(pass_b.run_chapter(chapter, limit=args.limit, force=args.force))
        if "c" in selected:
            print(pass_c.run_chapter(chapter, force=args.force))
        if "queue" in selected:
            built = queue.build_queue(chapter)
            print(f"queue items={len(built['items'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
