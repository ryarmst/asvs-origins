# `sources/`

Raw snapshots. Regenerable. Do not hand-edit.

This tree is bootstrapped from a local copy of
[tghosth/asvs-issue-analyze](https://github.com/tghosth/asvs-issue-analyze)
and from [OWASP/ASVS](https://github.com/OWASP/ASVS):

- `asvs/` — 4.0.3, 5.0.0, and latest CSVs, plus both official v4↔v5 mapping YAML files
- `issues/` — one snapshot per GitHub issue, plus `*.history.json` where edits exist
- `git-cache/ASVS/` — local clone used by lineage extraction (gitignored)
- `manifest.json` — SHA-256 digest and fetch timestamp per tracked file

Refresh with:

```
.venv/bin/python -m pipeline.ingest
```
