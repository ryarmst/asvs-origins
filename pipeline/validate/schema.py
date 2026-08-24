"""Validate every corpus file against its JSON Schema."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = ROOT / "schema"
DATA_DIR = ROOT / "data"
SOURCES_DIR = ROOT / "sources"

SCHEMA_FILES = {
    "requirement": "requirement.schema.json",
    "issue": "issue.schema.json",
    "pull_request": "pull-request.schema.json",
}


def load_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def schema_registry() -> Registry:
    registry = Registry()
    for path in SCHEMA_DIR.glob("*.schema.json"):
        contents = load_json(path)
        resource = Resource.from_contents(contents, default_specification=DRAFT202012)
        registry = registry.with_resource(path.name, resource)
        schema_id = contents.get("$id")
        if schema_id:
            registry = registry.with_resource(schema_id, resource)
    return registry


def validator_for(kind: str) -> Draft202012Validator:
    filename = SCHEMA_FILES[kind]
    schema = load_json(SCHEMA_DIR / filename)
    return Draft202012Validator(schema, registry=schema_registry())


def iter_data_files() -> list[tuple[str, Path]]:
    files: list[tuple[str, Path]] = []
    req_root = DATA_DIR / "requirements"
    if req_root.exists():
        for path in sorted(req_root.glob("*/*.json")):
            files.append(("requirement", path))
    issues_root = DATA_DIR / "issues"
    if issues_root.exists():
        for path in sorted(issues_root.glob("*.json")):
            files.append(("issue", path))
    prs_root = DATA_DIR / "prs"
    if prs_root.exists():
        for path in sorted(prs_root.glob("*.json")):
            files.append(("pull_request", path))
    return files


def validate_all() -> list[str]:
    errors: list[str] = []
    files = iter_data_files()
    if not files:
        return ["no corpus files found under data/"]
    validators = {kind: validator_for(kind) for kind in SCHEMA_FILES}
    for kind, path in files:
        instance = load_json(path)
        for error in validators[kind].iter_errors(instance):
            location = "/".join(str(part) for part in error.absolute_path) or "<root>"
            errors.append(f"{path.relative_to(ROOT)}:{location}: {error.message}")
    return errors


def main() -> int:
    errors = validate_all()
    if errors:
        print(f"schema: {len(errors)} error(s)")
        for error in errors:
            print(error)
        return 1
    print("schema: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
