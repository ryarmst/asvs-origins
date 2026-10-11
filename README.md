# asvs-origins

A companion knowledge base for the
[OWASP Application Security Verification Standard](https://github.com/OWASP/ASVS).
For any requirement it records where the text came from, who argued about it,
what was decided, and why it says what it says.

This is not a replacement for [asvs.dev](https://asvs.dev) or for the
standard. Requirement text is mirrored for context. Discussion stays in the
OWASP/ASVS tracker. This repository curates provenance around that discussion.

## Status

Milestone 3: static site and local editor. Every requirement has an origin
note. Public pages hide rejected artifacts. Use
[docs/review.md](docs/review.md) to run the app and add human notes.

## Repository layout

- `schema/` — JSON Schema (draft 2020-12) for requirements, issues, and pull requests
- `sources/` — raw ASVS tables and GitHub issue snapshots (regenerable)
- `data/` — curated corpus (git-tracked, reviewed)
- `pipeline/` — Python ingest, extract, validation, LLM passes, and site indexes
- `web/` — SvelteKit static site and local editor
- `build/` — derived indexes and candidate links (gitignored)
- `docs/adr/` — architecture decisions

## Dual license

Code and documentation are Apache-2.0. See `LICENSE`.

The corpus in `data/` is [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
Mirrored ASVS requirement text is already under that license, so share-alike
applies to public redistribution of the corpus. See `data/LICENSE`.

## Validate the corpus

Create a virtualenv and install the package.

```
python3 -m venv .venv
```

```
.venv/bin/pip install -e ".[dev]"
```

Run every validator.

```
.venv/bin/python -m pipeline.validate
```

The same checks run as three modules:

```
.venv/bin/python -m pipeline.validate.schema
```

```
.venv/bin/python -m pipeline.validate.integrity
```

```
.venv/bin/python -m pipeline.validate.quotes
```

Run tests.

```
.venv/bin/pytest
```

## Ingest and extract (M1)

Refresh the requirement tables from the CSVs in `sources/asvs/`. Existing
authored records keep their slug, uid, lineage events, and summaries.

```
.venv/bin/python -m pipeline.ingest.sync_asvs
```

Mirror the issue archive from a local
[asvs-issue-analyze](https://github.com/tghosth/asvs-issue-analyze) checkout
(defaults to the path used on this machine):

```
.venv/bin/python -m pipeline.ingest.sync_issues
```

Clone or update OWASP/ASVS under `sources/git-cache/ASVS` (gitignored):

```
.venv/bin/python -m pipeline.ingest.sync_git
```

Or run all three:

```
.venv/bin/python -m pipeline.ingest
```

Extract git lineage (skips authored/reviewed records) and scan issues for
requirement IDs.

```
.venv/bin/python -m pipeline.extract
```

`--resume` skips records that already have complete lineage, after an interrupted run.

```
.venv/bin/python -m pipeline.extract --resume
```

Build derived indexes under `build/index/`:

```
.venv/bin/python -m pipeline.build.index
```

## LLM enrichment (M2)

Pass A triages issues, Pass B summarizes requirement-bearing threads, Pass C
writes origin/evolution summaries for a chapter. Artifacts are `llm` and
`unreviewed`. Human `accepted` records are never overwritten.

Set `ASVS_ORIGINS_LLM_API_KEY` or `OPENAI_API_KEY` (OpenAI-compatible
`/v1/chat/completions`). Optional: `ASVS_ORIGINS_LLM_BASE_URL`,
`ASVS_ORIGINS_LLM_MODEL`.

```
.venv/bin/python -m pipeline.llm --chapter V9
```

The V9 pilot in this repo was produced with the session provider (no vendor
API). Re-run that path with:

```
.venv/bin/python scripts/run_m2_v9_session.py
```

Print a maintainer queue (optional; the site does not use it):

```
.venv/bin/python -m pipeline.llm.queue --chapter V9
```

Fill origin and evolution notes for every requirement from mapping + git
lineage. Authored records and existing summaries are left alone.

```
.venv/bin/python -m pipeline.enrich
```

## Web app (M3)

Read-only site (rebuilds indexes, then serves http://127.0.0.1:5173):

```
npm --prefix web install
```

```
npm --prefix web run dev
```

Local editor (writes `data/` when `DEV_EDIT=1`). Set your GitHub login in
`web/.env` first. See [docs/review.md](docs/review.md). Open a requirement,
then Enrich from sources.

```
cp web/.env.example web/.env
```

```
npm --prefix web run edit
```

Production static build (output `web/build/`):

```
npm --prefix web run build
```

## Seed records

M0 includes authored JSON for:

- V1.3.6, V1.3.8, V1.5.2, V11.1.2, V11.1.4, V13.2.4, V13.2.5
- issue 3338
- stub requirement files for V1.1.1, V1.5.3, V2.2.1, and V5.3.2 (referenced by the seed)

Regenerate those files from the transcription script only if you are changing
the seed itself:

```
.venv/bin/python scripts/write_m0_seed.py
```

## Provenance

Every authored block is `human`, `llm`, `llm_reviewed`, or `deterministic`.
The public UI will badge the first three as Human, AI, or AI-reviewed.
`deterministic` is for mechanical extractors (git pickaxe, mapping, ID
scans). There is no project rule about which model to use. Pipeline metadata
may still record a model id and prompt version so regenerations stay
idempotent; that metadata is not a vendor endorsement.

## What comes next

1. Human notes on controls you care about, from the local editor
2. M4 — LLM backfill of remaining issue threads where mapping+git is not enough
3. M5 — daily source sync
