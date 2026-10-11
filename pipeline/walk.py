"""Walk nested corpus records for provenance-bearing artifacts."""

from __future__ import annotations

from collections.abc import Iterator


def walk_nodes(value, path: str = "") -> Iterator[tuple[str, dict | list]]:
    if isinstance(value, dict):
        yield path, value
        for key, child in value.items():
            child_path = f"{path}/{key}" if path else str(key)
            yield from walk_nodes(child, child_path)
    elif isinstance(value, list):
        yield path, value
        for index, child in enumerate(value):
            yield from walk_nodes(child, f"{path}/{index}")


def walk_provenance(record: dict) -> list[dict]:
    found: list[dict] = []
    for path, node in walk_nodes(record):
        if isinstance(node, dict) and "origin" in node and "review" in node:
            found.append({"path": path, "provenance": node})
    return found


def resolve_path(record: dict, path: str):
    """Return (parent, key, node) for a slash-separated path of keys/indexes."""
    if not path:
        return None, None, record
    node: dict | list = record
    parent: dict | list | None = None
    key: str | int | None = None
    for part in path.split("/"):
        parent = node
        key = int(part) if part.isdigit() else part
        node = node[key]  # type: ignore[index]
    return parent, key, node


def origin_counts(records: list[dict], *, published_only: bool = False) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        for item in walk_provenance(record):
            prov = item["provenance"]
            review = (prov.get("review") or {}).get("status")
            if published_only and review == "rejected":
                continue
            origin = prov.get("origin") or "unknown"
            counts[origin] = counts.get(origin, 0) + 1
    return counts
