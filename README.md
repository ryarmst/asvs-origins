# asvs-origins

A companion knowledge base for the
[OWASP Application Security Verification Standard](https://github.com/OWASP/ASVS).
For any requirement it records where the text came from, who argued about it,
what was decided, and why it says what it says.

This is not a replacement for [asvs.dev](https://asvs.dev) or for the
standard. Requirement text is mirrored for context. Discussion stays in the
OWASP/ASVS tracker. This repository curates provenance around that discussion.

## Status

Milestone 0: schemas, validators, and a seed corpus transcribed from the
seven requirement-history reports in
[asvs-issue-analyze](https://github.com/tghosth/asvs-issue-analyze).

No LLM enrichment yet. No public site yet.

## Repository layout

- `schema/` — JSON Schema (draft 2020-12) for requirements, issues, and pull requests
- `sources/` — raw ASVS tables and GitHub issue snapshots (regenerable)
- `data/` — curated corpus (git-tracked, reviewed)
- `pipeline/` — Python ingest, extract, validation, and later LLM passes
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

Every authored block is `human`, `llm`, or `llm_reviewed`. The public UI will
badge those as Human, AI, or AI-reviewed. There is no project rule about which
model to use. Pipeline metadata may still record a model id and prompt version
so regenerations stay idempotent; that metadata is not a vendor endorsement.

## What comes next

1. M1 — import all 345 requirements, sync the issue archive, port lineage extraction
2. M2 — LLM passes on chapter V9, then human review
3. M3 — public read-only site with legacy ID redirects
