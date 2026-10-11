# Run the site and add human notes

The public site is a static SvelteKit app. Enrichment happens in a local editor that
writes JSON under `data/`. There is no hosted write path and no review queue.

## Public site

Install web dependencies once.

```
npm --prefix web install
```

Build indexes and start the read-only dev server.

```
npm --prefix web run dev
```

Open http://127.0.0.1:5173. Typical path:

1. Search or open a chapter.
2. Open a requirement. Origin and evolution notes are labeled Human, AI draft, AI · reviewed, or Extracted.
3. Follow source issues if you want more context.

Rejected artifacts never appear on public pages.

## Local editor

Copy the env file and set your GitHub login if it is not already `ryarmst`.

```
cp web/.env.example web/.env
```

Start the editor (rebuilds indexes first).

```
npm --prefix web run edit
```

Open a requirement, then **Enrich from sources**. That page is:

1. The issue snapshot. Click a comment to attach a citation.
2. Existing notes, labeled by provenance.
3. A human note form. Choose origin or evolution and save.

Keep text / Save edits / Flag / Hide still apply to an existing AI or extracted note when you want to stamp review state. Invalid JSON will not save.

After a batch, run the corpus validators.

```
.venv/bin/python -m pipeline.validate
```

Commit the `data/` JSON. Do not re-run LLM passes on records you have accepted.

## Mechanical enrichment

Fill origin/evolution for every requirement from the official mapping and git lineage (skips authored and already-summarized records):

```
.venv/bin/python -m pipeline.enrich
```

## Production build

```
npm --prefix web run build
```

Output is `web/build/`. Preview it with `npm --prefix web run preview`.
For a project-pages URL set `BASE_PATH=/asvs-origins` when building.
