# LLM prompts

Each pass has a versioned prompt. Provenance records `prompt_id` and
`prompt_version`. Bump the version filename and add a row to
`docs/prompt-changelog.md` in the same change.

| Pass | File | Version |
|---|---|---|
| A — triage | `triage.v1.md` | v1 |
| B — issue summarization | `issue-pass.v1.md` | v1 |
| C — requirement synthesis | `requirement-pass.v1.md` | v1 |

The model must not use prior knowledge of ASVS. Inputs are assembled by
the pipeline.
