# Contributing

This repository is a curated provenance corpus, not a discussion forum.
Argument about ASVS belongs in [OWASP/ASVS](https://github.com/OWASP/ASVS).
Changes here explain that argument.

## How to change the corpus

1. Edit JSON under `data/` or use the local editor (`npm --prefix web run edit`).
2. Run the validators.
3. Open a pull request.

```
.venv/bin/python -m pipeline.validate
```

Do not hand-edit files under `sources/`. Those snapshots are regenerable.

## Provenance

Every summary, decision, argument, terminology entry, and open question must
carry a `provenance` object.

- `human` — a person wrote it. `authors` is required. `model` must be null.
- `llm` — a model drafted it. `authors` must be empty.
- `llm_reviewed` — a model drafted it and a named person accepted or edited it.
- `deterministic` — produced by a script from git, mappings, or snapshots.
  `authors` must be empty. `model` must be null.

The site will show Human, AI, or AI-reviewed. It will not name a vendor.

Reviewed (`accepted`) and `human` artifacts must not be overwritten by the
pipeline. If inputs change, the pipeline adds a new unreviewed summary with
`supersedes` set. A person decides which version stands.

## Review actions

There is no review queue. Open a requirement, read the labeled notes, then
enrich from sources when you have something to add.

- Keep text — `origin` becomes `llm_reviewed`, `review.status` becomes `accepted`
- Save edits — same, with the edited body. It is still `llm_reviewed`
- Hide — keep the record, hide it from the public view, do not feed it back
  into later generations
- Write a human note — a new `human` artifact alongside the model draft
- Flag — `changes_requested` plus a note

Human-authored content is `accepted` on write, with the author as reviewer.

## Attribution

Decision and argument records name people by GitHub login only. Link to the
source comment. Do not characterise motives.

If you want a login removed from this corpus, open an issue or pull request
and it will be honoured.

## Quotes

A `quote` is optional, at most 25 words, and must appear verbatim in the
matching file under `sources/`. Prefer a paraphrase plus a link. One quote
per cited comment per file.

## Language

The corpus is English-only. Translation threads triage as process or
`no_requirement`.

## Requirement identity

ASVS IDs change across releases. The stable key is `uid` (`req-` plus eight
hex characters). See [ADR 0001](docs/adr/0001-stable-requirement-uid.md).

File paths use the current ID for humans. After a renumber, the file moves
and the old ID is appended to `identifiers[]`. The `uid` inside the file
does not change.
