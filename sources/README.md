# `sources/`

Raw snapshots. Regenerable. Do not hand-edit.

M0 bootstrapped these files from a local copy of
[tghosth/asvs-issue-analyze](https://github.com/tghosth/asvs-issue-analyze):

- `asvs/` — 4.0.3, 5.0.0, and latest CSVs, plus the v5.0.0 to v4.0.3 mapping
- `issues/` — snapshots cited by the M0 seed records, plus edit history
  where it existed
- `manifest.json` — SHA-256 digest and fetch timestamp per file

M1 will replace this partial copy with a full sync of the issue archive and
a blobless clone of OWASP/ASVS under `git-cache/` (gitignored).
