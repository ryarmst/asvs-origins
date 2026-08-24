# ADR 0001: Stable requirement `uid`

- Status: accepted
- Date: 2026-08-24

## Context

ASVS requirement IDs are labels, not keys. The SSRF control has been V5.30,
V5.4.2, V5.1.9, V5.2.6, and V1.3.6. Practitioners still cite the old numbers
in reports. A corpus keyed on `V1.3.6` would break on the next renumber
(5.0.1 or 5.1).

## Decision

Every requirement has a `uid` of the form `req-` plus eight lowercase hex
characters. It is minted once at import and never changes.

For the 5.0.0 import, the mint is deterministic:

```
sha256("asvs-origins:uid:5.0.0:" + current_id)[:8]
```

That formula is an import convenience so M0 seed records and M1 import agree.
After import, the stored `uid` is authoritative even if the formula later
changes.

Human-readable `slug` values (`ssrf-allowlist-validation`) are also assigned
once and then frozen, because they appear in URLs.

ASVS IDs live in `current.id` and in `identifiers[]`, versioned. File paths
are `data/requirements/<chapter>/<current-id>.json` for navigation. A later
`pipeline/renumber.py` will move files and append identifiers. Permalinks
will be `/r/<uid>` and `/legacy/<release>/<old-id>`.

## Consequences

- Linking is by `uid`, not by ASVS ID
- Deleted requirements keep their file; `current.status` becomes `deleted`
- Mapping YAML and git lineage may disagree; git wins, and the disagreement
  is stored on `lineage.mapping_entry.agrees_with_git`
- Seed records minted with the 5.0.0 formula must not be reminted when IDs
  change
