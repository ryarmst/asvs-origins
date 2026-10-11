You are triaging one OWASP ASVS GitHub issue for a provenance corpus.

Use only the supplied title, body excerpt, labels, comment count, and
participants. Do not use prior knowledge of ASVS. Do not invent requirement
IDs.

ASVS 5.0.0 chapter IDs are not the same as 4.x. An issue about "V9" and HSTS
or TLS is usually the old Communications chapter, not 5.0.0 V9 (Self-contained
Tokens). Treat ID collisions as `chapter_bearing` only when the current
chapter's subject is actually discussed; otherwise `no_requirement`.

Return a JSON object with:
- `class`: proposal | clarification | defect | wording | process | translation | meta | spam
- `relevance`: requirement_bearing | chapter_bearing | no_requirement
- `estimated_requirement_count`: integer >= 0
- `reason`: one sentence

Empty is valid. A translation, typo, CI, or process thread is
`relevance: no_requirement`.
