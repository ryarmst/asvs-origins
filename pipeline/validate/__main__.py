"""Run all corpus validators."""

from __future__ import annotations

import sys

from pipeline.validate import integrity, quotes, schema


def main() -> int:
    modules = [
        ("schema", schema.validate_all),
        ("integrity", integrity.validate_all),
        ("quotes", quotes.validate_all),
    ]
    status = 0
    for name, fn in modules:
        errors = fn()
        if errors:
            status = 1
            print(f"{name}: {len(errors)} error(s)")
            for error in errors:
                print(error)
        else:
            print(f"{name}: ok")
    return status


if __name__ == "__main__":
    sys.exit(main())
