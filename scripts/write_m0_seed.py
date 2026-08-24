"""Emit M0 seed records transcribed from asvs-issue-analyze investigations.

Run from the repository root:

python3 scripts/write_m0_seed.py
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.ids import canonical_json, mint_sub_id, mint_uid, sha256_bytes  # noqa: E402

WHEN = "2026-08-24T22:51:00Z"
REVIEW_NOTE = (
    "Transcribed from asvs-issue-analyze investigations/ into the asvs-origins schema."
)


def human_prov(confidence: str = "high") -> dict:
    return {
        "origin": "human",
        "created_at": WHEN,
        "updated_at": WHEN,
        "authors": [{"name": "Ryan Armstrong", "github": "ryarmst"}],
        "model": None,
        "review": {
            "status": "accepted",
            "by": ["ryarmst"],
            "at": WHEN,
            "note": REVIEW_NOTE,
        },
        "input_digest": None,
        "confidence": confidence,
    }


def commit_cit(sha: str) -> dict:
    return {
        "type": "commit",
        "url": f"https://github.com/OWASP/ASVS/commit/{sha}",
        "commit": sha,
    }


def issue_cit(
    number: int,
    *,
    comment_id: str | None = None,
    fragment: str | None = None,
    author: str | None = None,
    date: str | None = None,
    quote: str | None = None,
    edited_after: bool | None = None,
) -> dict:
    url = f"https://github.com/OWASP/ASVS/issues/{number}"
    if fragment:
        url = f"{url}#{fragment}"
    citation: dict = {
        "type": "issue_comment" if (comment_id or (fragment or "").startswith("issuecomment-")) else "issue_body",
        "url": url,
        "issue": number,
    }
    if comment_id:
        citation["comment_id"] = comment_id
    if author:
        citation["author"] = author
    if date:
        citation["date"] = date
    if quote is not None:
        citation["quote"] = quote
    if edited_after is not None:
        citation["edited_after"] = edited_after
    return citation


def pr_cit(number: int) -> dict:
    return {
        "type": "pr_body",
        "url": f"https://github.com/OWASP/ASVS/pull/{number}",
        "pr": number,
    }


def mapping_cit() -> dict:
    return {
        "type": "mapping",
        "url": "https://github.com/OWASP/ASVS/blob/master/5.0/mappings/mapping_v5.0.0_to_v4.0.3.yml",
    }


def claim(prefix: str, key: str, **fields) -> dict:
    payload = {
        "id": mint_sub_id(prefix, key),
        "date": None,
        "actors": [],
        "citations": [],
        "provenance": human_prov(),
    }
    payload.update(fields)
    return payload


def summary(kind: str, key: str, body: str, citations: list[dict] | None = None) -> dict:
    return {
        "id": mint_sub_id("sum", key),
        "kind": kind,
        "body": body,
        "citations": citations or [],
        "supersedes": None,
        "provenance": human_prov(),
    }


def event(date: str, kind: str, commit: str | None, actor: str | None, id_at_time: str | None, text: str, extra_cits: list[dict] | None = None) -> dict:
    citations = []
    if commit:
        citations.append(commit_cit(commit))
    if extra_cits:
        citations.extend(extra_cits)
    return {
        "date": date,
        "kind": kind,
        "commit": commit,
        "actor": actor,
        "id_at_time": id_at_time,
        "summary": text,
        "citations": citations,
    }


def load_csv_row(release_file: str, req_id: str) -> dict:
    path = ROOT / "sources" / "asvs" / release_file
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["req_id"] == req_id:
                return row
    raise KeyError(req_id)


def dump(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {path.relative_to(ROOT)}")


def stub_requirement(req_id: str, slug: str) -> dict:
    row = load_csv_row("asvs_5.0.0.csv", req_id)
    latest = load_csv_row("asvs_latest.csv", req_id)
    uid = mint_uid(req_id)
    return {
        "uid": uid,
        "slug": slug,
        "current": {
            "release": "5.0.0",
            "id": req_id,
            "chapter_id": row["chapter_id"],
            "chapter_name": row["chapter_name"],
            "section_id": row["section_id"],
            "section_name": row["section_name"],
            "level": int(row["L"]),
            "text": row["req_description"],
            "source": "sources/asvs/asvs_5.0.0.csv",
            "status": "current",
        },
        "master": {
            "id": latest["req_id"],
            "level": int(latest["L"]),
            "text": latest["req_description"],
            "differs_from_release": latest["req_description"] != row["req_description"]
            or latest["L"] != row["L"],
            "checked_at": "2026-08-24",
        },
        "identifiers": [
            {
                "release": "5.0.0",
                "id": req_id,
                "level": int(row["L"]),
                "status": "current",
            }
        ],
        "lineage": {
            "origin_kind": "unknown",
            "predecessors": [],
            "mapping_entry": None,
            "events": [],
            "provenance": human_prov(),
        },
        "summaries": [],
        "decisions": [],
        "open_questions": [],
        "terminology": [],
        "key_sources": [],
        "related_requirements": [],
        "external_references": [],
        "status": {
            "coverage": "empty",
            "lineage_state": "empty",
            "last_pipeline_run": None,
            "last_human_review": None,
            "blocked_reason": None,
            "stale": False,
        },
    }


def requirement_v136() -> dict:
    row = load_csv_row("asvs_5.0.0.csv", "V1.3.6")
    pred = load_csv_row("asvs_4.0.3.csv", "V5.2.6")
    uid = mint_uid("V1.3.6")
    return {
        "uid": uid,
        "slug": "ssrf-allowlist-validation",
        "current": {
            "release": "5.0.0",
            "id": "V1.3.6",
            "chapter_id": "V1",
            "chapter_name": "Encoding and Sanitization",
            "section_id": "V1.3",
            "section_name": "Sanitization",
            "level": 2,
            "text": row["req_description"],
            "source": "sources/asvs/asvs_5.0.0.csv",
            "status": "current",
        },
        "master": {
            "id": "V1.3.6",
            "level": 2,
            "text": row["req_description"],
            "differs_from_release": False,
            "checked_at": "2026-08-24",
        },
        "identifiers": [
            {"release": "5.0.0", "id": "V1.3.6", "level": 2, "status": "current"},
            {"release": "4.0.3", "id": "V5.2.6", "level": 1, "status": "predecessor"},
            {"release": "pre-release", "id": "V5.1.9", "level": None, "status": "historical"},
            {"release": "pre-release", "id": "V5.4.2", "level": None, "status": "historical"},
            {"release": "pre-release", "id": "V5.30", "level": None, "status": "historical"},
        ],
        "lineage": {
            "origin_kind": "carried_forward",
            "predecessors": [
                {
                    "release": "4.0.3",
                    "id": "V5.2.6",
                    "relation": "modified",
                    "text": pred["req_description"],
                    "note": "Rewritten in 2024 to split allowlist validation from character sanitization and to drop the file-metadata clause, which V5.3.2 (then discussed as 12.3.1) covers. Level changed from L1 to L2.",
                }
            ],
            "mapping_entry": {
                "raw": "MODIFIED, MOVED FROM v4.0.3-5.2.6",
                "status": "MODIFIED",
                "agrees_with_git": True,
                "note": None,
            },
            "events": [
                event("2018-08-05", "added", "3b6b57a0", "jmanico", "V5.30", "Original one-line SSRF requirement with no guidance."),
                event("2018-11-19", "moved", "844285bf", "vanderaj", "V5.4.2", "Moved into the deserialization/other parsing section with wording about filenames and URL fields."),
                event("2019-01-13", "reworded", "0bbdd60b", "tghosth", "V5.1.9", "Moved to input validation and introduced allowlisting of protocols, domains, paths and ports."),
                event("2019-02-10", "moved", "2e561634", "vanderaj", "V5.1.9", "V5 sections restructured (#350).", extra_cits=[issue_cit(350)]),
                event("2019-02-11", "renumbered", "2b45281f", "vanderaj", "V5.2.6", "Renumbered to V5.2.6, the ID that survived through v4.0.3."),
                event("2024-10-08", "reworded", "e86154d4", "tghosth", "V5.2.6", "Major rewrite for v5.0 to resolve #2115: allowlist validation plus character sanitization; file-metadata clause removed.", extra_cits=[issue_cit(2115), pr_cit(2125)]),
                event("2024-10-08", "grammar", "35f39a56", "tghosth", "V5.2.6", "Fixed the typo 'Server-side Request Forge (SRF' to 'Forgery (SSRF)'."),
                event("2024-10-17", "renumbered", "4eaad210", "elarlang", "V5.2.6", "Reorder and numeration fix; content unchanged."),
                event("2025-03-24", "tag_cleanup", "30ab63dd", "elarlang", "V5.2.6", "Removed placeholders (#2456 step 2.1).", extra_cits=[issue_cit(2456)]),
                event("2025-03-27", "renumbered", "d3a825b4", "elarlang", "V1.3.6", "Renumbered from V5.2.6 to V1.3.6 during the v5 chapter restructure (#2553, #2456).", extra_cits=[issue_cit(2553), issue_cit(2456)]),
                event("2025-05-24", "tag_cleanup", "104040a5", "elarlang", "V1.3.6", "Removed the v5.0.be temporary tracking column (#2456 step 4.1).", extra_cits=[issue_cit(2456)]),
            ],
            "provenance": human_prov(),
        },
        "summaries": [
            summary(
                "origin",
                "v136-origin",
                "SSRF entered ASVS in August 2018 when jmanico added V5.30 as a one-line control with no defensive guidance. Over the next few months vanderaj and tghosth relocated it during v4.0 development — first to V5.4.2, then to V5.1.9 — and the January 2019 move introduced allowlisting of protocols, domains, paths and ports, which has remained the core of the requirement ever since. It settled as V5.2.6 in v4.0.3.",
                [commit_cit("3b6b57a0"), commit_cit("0bbdd60b"), issue_cit(2115)],
            ),
            summary(
                "evolution",
                "v136-evolution",
                "The 2024 rewrite in #2115 / PR #2125 is the wording change that matters. tghosth split three overlapping SSRF controls: this requirement kept allowlist validation of data used to call another service, file metadata moved to what is now V5.3.2, and the sanitization-versus-validation terminology was argued in thread. The March 2025 renumber to V1.3.6 was chapter restructure, not a change of meaning. Level also moved from L1 to L2.",
                [issue_cit(2115), pr_cit(2125)],
            ),
            summary(
                "controversy",
                "v136-controversy",
                "Issue #3244, still open, challenges the phrase 'sanitizing potentially dangerous characters'. jmanico argues sanitization is the wrong SSRF control and should be dropped; tghosth has endorsed that direction. elarlang then asked how the remainder differs from V13.2.4. Two proposals are in play: fold user-input SSRF into V13.2.4 and remove V1.3.6, or keep a first-layer application allowlist here and a second-layer infrastructure allowlist in V13.2.4. No wording change has been merged.",
                [issue_cit(3244)],
            ),
        ],
        "decisions": [
            claim(
                "dec",
                "v136-allowlist",
                statement="The SSRF control is an application-layer allowlist of protocols, domains, paths and ports, kept distinct from server/network allowlisting.",
                kind="decision",
                subkind="reworded",
                date="2019-01-13",
                actors=["tghosth"],
                status="settled",
                citations=[commit_cit("0bbdd60b"), issue_cit(1324)],
            ),
            claim(
                "dec",
                "v136-dedup",
                statement="The 2024 rewrite separated allowlist validation from file-metadata handling and from network-level SSRF defence.",
                kind="decision",
                subkind="reworded",
                date="2024-10-08",
                actors=["tghosth", "elarlang", "jmanico"],
                status="settled",
                citations=[issue_cit(2115), pr_cit(2125)],
            ),
            claim(
                "dec",
                "v136-level",
                statement="The requirement moved from L1 (all levels in v4.0.3) to L2 in v5.0.0.",
                kind="decision",
                subkind="level_changed",
                date="2025-03-19",
                actors=["elarlang"],
                status="settled",
                citations=[issue_cit(2694)],
            ),
        ],
        "open_questions": [
            claim(
                "oq",
                "v136-sanitize",
                statement="Whether 'sanitizing potentially dangerous characters' should be dropped, and whether V1.3.6 should remain separate from V13.2.4.",
                kind="open_question",
                subkind="unresolved",
                date="2025-08-19",
                actors=["ajayojha", "jmanico", "tghosth", "elarlang"],
                status="disputed",
                citations=[issue_cit(3244)],
            )
        ],
        "terminology": [
            claim(
                "trm",
                "v136-allowlist",
                statement="The thread adopted 'allowlist validation' over 'checking' or 'matching' for the URL-construction control.",
                kind="terminology",
                subkind="standardized",
                date="2024-09-26",
                actors=["jmanico", "tghosth"],
                status="settled",
                citations=[issue_cit(2115)],
            )
        ],
        "key_sources": [
            {"kind": "issue", "number": 2115, "role": "drove_rewording", "rank": 1},
            {"kind": "pr", "number": 2125, "role": "implemented", "rank": 2},
            {"kind": "issue", "number": 1324, "role": "defence_in_depth", "rank": 3},
            {"kind": "issue", "number": 3244, "role": "open_wording", "rank": 4},
            {"kind": "issue", "number": 2553, "role": "renumbering", "rank": 5},
        ],
        "related_requirements": [
            {
                "uid": mint_uid("V5.3.2"),
                "id": "V5.3.2",
                "relation": "boundary",
                "note": "Owns file-metadata validation. Discussed as 12.3.1 when V1.3.6 was rewritten.",
            },
            {
                "uid": mint_uid("V13.2.4"),
                "id": "V13.2.4",
                "relation": "overlaps",
                "note": "Technology-agnostic outbound allowlist. #3244 asks whether V1.3.6 should be folded into it.",
            },
            {
                "uid": mint_uid("V13.2.5"),
                "id": "V13.2.5",
                "relation": "companion",
                "note": "Server-configuration allowlist that was V12.6.1; second-layer SSRF defence in the #1324 model.",
            },
        ],
        "external_references": [
            {
                "kind": "cwe",
                "id": "CWE-918",
                "title": "Server-Side Request Forgery (SSRF)",
                "url": "https://cwe.mitre.org/data/definitions/918.html",
                "cited_by": None,
            }
        ],
        "status": {
            "coverage": "authored",
            "lineage_state": "complete",
            "last_pipeline_run": None,
            "last_human_review": WHEN,
            "blocked_reason": None,
            "stale": False,
        },
    }


def requirement_v138() -> dict:
    row = load_csv_row("asvs_5.0.0.csv", "V1.3.8")
    return {
        "uid": mint_uid("V1.3.8"),
        "slug": "jndi-injection-prevention",
        "current": {
            "release": "5.0.0",
            "id": "V1.3.8",
            "chapter_id": "V1",
            "chapter_name": "Encoding and Sanitization",
            "section_id": "V1.3",
            "section_name": "Sanitization",
            "level": 2,
            "text": row["req_description"],
            "source": "sources/asvs/asvs_5.0.0.csv",
            "status": "current",
        },
        "master": {
            "id": "V1.3.8",
            "level": 2,
            "text": row["req_description"],
            "differs_from_release": False,
            "checked_at": "2026-08-24",
        },
        "identifiers": [
            {"release": "5.0.0", "id": "V1.3.8", "level": 2, "status": "current"},
            {"release": "pre-release", "id": "V5.2.11", "level": 1, "status": "historical"},
        ],
        "lineage": {
            "origin_kind": "new_in_release",
            "predecessors": [],
            "mapping_entry": {
                "raw": "ADDED",
                "status": "ADDED",
                "agrees_with_git": True,
                "note": None,
            },
            "events": [
                event("2023-09-28", "added", "a739927d", "tghosth", "V5.2.11", "Created as 5.2.11 to resolve #1533 (JNDI injection).", extra_cits=[issue_cit(1533), pr_cit(1736)]),
                event("2023-09-28", "grammar", "bd587a43", "elarlang", "V5.2.11", "Markdown table syntax fix; no content change."),
                event("2025-03-19", "level_changed", "9019f849", "elarlang", "V5.2.11", "Level changed from L1 to L2 because JNDI injection is Java-specific (#2694).", extra_cits=[issue_cit(2694)]),
                event("2025-03-20", "reworded", "43481db4", "tghosth", "V5.2.11", "Dropped the filler phrase 'as securely as possible' (#2751).", extra_cits=[issue_cit(2751)]),
                event("2025-03-27", "renumbered", "d3a825b4", "elarlang", "V1.3.8", "Renumbered from 5.2.11 to 1.3.8.", extra_cits=[issue_cit(2553)]),
                event("2025-05-24", "tag_cleanup", "104040a5", "elarlang", "V1.3.8", "Removed the v5.0.be tracking column."),
            ],
            "provenance": human_prov(),
        },
        "summaries": [
            summary(
                "origin",
                "v138-origin",
                "V1.3.8 is new in v5.0.0. ImanSharaf opened #1533 in January 2023 noting that ASVS covered SQL, LDAP and SMTP injection but not JNDI. jmanico called it a Log4Shell-shaped gap and argued the defence is allowlisting JNDI names plus least privilege on the context, not encoding. tghosth committed 5.2.11 in September 2023.",
                [issue_cit(1533), pr_cit(1736)],
            ),
            summary(
                "evolution",
                "v138-evolution",
                "Release preparation changed the level from L1 to L2 (#2694) and replaced 'configured as securely as possible' with 'configured securely' (#2751). The later renumber to V1.3.8 was chapter restructure only.",
                [issue_cit(2694), issue_cit(2751)],
            ),
            summary(
                "controversy",
                "v138-controversy",
                "Open issue #3220 asks whether the control should be made technology-agnostic (any naming/directory lookup) and whether 'sanitizes' is the right verb. jmanico favours genericizing; tghosth has asked for examples as damaging as JNDI remote class loading. #3214 (sanitization vs allowlisting) was closed as a duplicate of #3220.",
                [issue_cit(3220), issue_cit(3214)],
            ),
        ],
        "decisions": [
            claim(
                "dec",
                "v138-added",
                statement="A dedicated JNDI injection requirement was added rather than folding the risk into generic injection or LDAP controls.",
                kind="decision",
                subkind="added",
                date="2023-09-28",
                actors=["ImanSharaf", "tghosth", "jmanico"],
                status="settled",
                citations=[issue_cit(1533), pr_cit(1736)],
            ),
            claim(
                "dec",
                "v138-level",
                statement="Niche Java-specific injection was placed at L2, not L1, despite Log4Shell.",
                kind="decision",
                subkind="level_changed",
                date="2025-03-19",
                actors=["elarlang", "jmanico"],
                status="settled",
                citations=[issue_cit(2694)],
            ),
        ],
        "open_questions": [
            claim(
                "oq",
                "v138-generic",
                statement="Whether V1.3.8 should stay Java/JNDI-specific or become a general naming-service lookup control, and whether sanitization or allowlisting is the prescribed defence.",
                kind="open_question",
                subkind="unresolved",
                date="2025-07-21",
                actors=["ajayojha", "jmanico", "tghosth", "elarlang"],
                status="disputed",
                citations=[issue_cit(3220)],
            )
        ],
        "terminology": [
            claim(
                "trm",
                "v138-encoding",
                statement="Encoding was rejected as a JNDI defence; the issue is unsafe invocation of lookup with untrusted data.",
                kind="terminology",
                subkind="rejected_term",
                date="2023-09-27",
                actors=["jmanico"],
                status="settled",
                citations=[issue_cit(1533)],
            )
        ],
        "key_sources": [
            {"kind": "issue", "number": 1533, "role": "origin", "rank": 1},
            {"kind": "pr", "number": 1736, "role": "implemented", "rank": 2},
            {"kind": "issue", "number": 3220, "role": "open_wording", "rank": 3},
            {"kind": "issue", "number": 2694, "role": "level_change", "rank": 4},
        ],
        "related_requirements": [],
        "external_references": [
            {
                "kind": "cwe",
                "id": "CWE-917",
                "title": "Expression Language Injection",
                "url": "https://cwe.mitre.org/data/definitions/917.html",
                "cited_by": None,
            }
        ],
        "status": {
            "coverage": "authored",
            "lineage_state": "complete",
            "last_pipeline_run": None,
            "last_human_review": WHEN,
            "blocked_reason": None,
            "stale": False,
        },
    }


def requirement_v152() -> dict:
    row = load_csv_row("asvs_5.0.0.csv", "V1.5.2")
    pred_impl = load_csv_row("asvs_4.0.3.csv", "V5.5.3")
    pred_arch = load_csv_row("asvs_4.0.3.csv", "V1.5.2")
    return {
        "uid": mint_uid("V1.5.2"),
        "slug": "safe-deserialization",
        "current": {
            "release": "5.0.0",
            "id": "V1.5.2",
            "chapter_id": "V1",
            "chapter_name": "Encoding and Sanitization",
            "section_id": "V1.5",
            "section_name": "Safe Deserialization",
            "level": 2,
            "text": row["req_description"],
            "source": "sources/asvs/asvs_5.0.0.csv",
            "status": "current",
        },
        "master": {
            "id": "V1.5.2",
            "level": 2,
            "text": row["req_description"],
            "differs_from_release": False,
            "checked_at": "2026-08-24",
        },
        "identifiers": [
            {"release": "5.0.0", "id": "V1.5.2", "level": 2, "status": "current"},
            {"release": "4.0.3", "id": "V5.5.3", "level": 1, "status": "predecessor"},
            {"release": "4.0.3", "id": "V1.5.2", "level": 2, "status": "predecessor"},
        ],
        "lineage": {
            "origin_kind": "merged_from",
            "predecessors": [
                {
                    "release": "4.0.3",
                    "id": "V5.5.3",
                    "relation": "modified",
                    "text": pred_impl["req_description"],
                    "note": "Primary source. Kept the implementation-level identity through most of v5 development.",
                },
                {
                    "release": "4.0.3",
                    "id": "V1.5.2",
                    "relation": "merged",
                    "text": pred_arch["req_description"],
                    "note": "Architecture-level duplicate merged in 2021. Integrity/encryption fallback was dropped; type allowlisting replaced it.",
                },
            ],
            "mapping_entry": {
                "raw": "MODIFIED, MOVED FROM v4.0.3-5.5.3, MERGED FROM v4.0.3-1.5.2",
                "status": "MODIFIED",
                "agrees_with_git": True,
                "note": None,
            },
            "events": [
                event("2020-07-13", "reworded", "25783d0a", "jmanico", "V5.5.3", "First rewrite of V5.5.3 after #807 called the v4 text non-actionable.", extra_cits=[issue_cit(807)]),
                event("2021-10-23", "merged", "0f714f0d", "jmanico", "V5.5.3", "Merged v4 V1.5.2 into V5.5.3: if deserialization is used, do it safely with a type allowlist.", extra_cits=[issue_cit(1084)]),
                event("2021-10-24", "grammar", "71baa763", "jmanico", "V5.5.3", "Tagged MERGED FROM 1.5.2 and replaced 'white-list' with 'allow-list'.", extra_cits=[pr_cit(1095)]),
                event("2024-05-15", "reworded", "ae9793bf", "elarlang", "V5.5.3", "Softened 'deserialization is not used' into 'if used, handle safely' (#1903).", extra_cits=[issue_cit(1903)]),
                event("2024-11-07", "reworded", "c53b2bc4", "tghosth", "V5.5.3", "Clarified allowlisting and forbade known-insecure mechanisms such as BinaryFormatter (#2297).", extra_cits=[issue_cit(2297), pr_cit(2323)]),
                event("2025-03-19", "level_changed", "9019f849", "elarlang", "V5.5.3", "Level changed from L1 to L2 (#2694), against jmanico's L1 vote.", extra_cits=[issue_cit(2694)]),
                event("2025-03-27", "renumbered", "d3a825b4", "elarlang", "V1.5.2", "Renumbered from 5.5.3 to 1.5.2."),
                event("2025-04-07", "reworded", "bcc0e5d3", "tghosth", "V1.5.2", "Removed the .NET BinaryFormatter example (#2846).", extra_cits=[issue_cit(2846)]),
                event("2025-04-22", "reworded", "e36063dc", "elarlang", "V1.5.2", "Broadened 'untrusted clients' to 'untrusted data' (#2990).", extra_cits=[issue_cit(2990)]),
                event("2025-05-24", "tag_cleanup", "104040a5", "elarlang", "V1.5.2", "Removed the v5.0.be tracking column."),
            ],
            "provenance": human_prov(),
        },
        "summaries": [
            summary(
                "origin",
                "v152-origin",
                "V1.5.2 is the surviving deserialization-safety control. It merges v4 V5.5.3 (protect deserialization of untrusted data) with v4 V1.5.2 (do not serialize to untrusted clients). elarlang flagged the pair as duplicates in #1084; jmanico merged them in October 2021, dropping integrity stamps as a defence because they do not fix a vulnerable deserializer (#772).",
                [issue_cit(1084), issue_cit(772), issue_cit(807)],
            ),
            summary(
                "evolution",
                "v152-evolution",
                "Wording moved from 'avoid or protect' to concrete type-allowlisting, then to an explicit ban on known-insecure mechanisms, then dropped the BinaryFormatter example, then widened scope from clients to any untrusted data. Level went L1 to L2 in #2694. The v5 ID V1.5.2 coincidentally reuses a v4 number from the merged architecture requirement.",
                [issue_cit(2297), issue_cit(2846), issue_cit(2990), issue_cit(2694)],
            ),
        ],
        "decisions": [
            claim(
                "dec",
                "v152-merge",
                statement="v4 V1.5.2 was deleted and merged into V5.5.3 rather than kept as a separate architecture control.",
                kind="decision",
                subkind="merged",
                date="2021-10-24",
                actors=["elarlang", "jmanico"],
                status="settled",
                citations=[issue_cit(1084), pr_cit(1095)],
            ),
            claim(
                "dec",
                "v152-no-integrity",
                statement="Signing, encryption, or integrity stamps were rejected as a deserialization defence.",
                kind="decision",
                subkind="reworded",
                date="2020-06-15",
                actors=["jmanico"],
                status="settled",
                citations=[issue_cit(772)],
            ),
            claim(
                "dec",
                "v152-level",
                statement="Deserialization stayed at L2 rather than L1 after #2694, despite a strong L1 argument from jmanico.",
                kind="decision",
                subkind="level_changed",
                date="2025-03-19",
                actors=["elarlang", "tghosth", "jmanico"],
                status="settled",
                citations=[issue_cit(2694)],
            ),
        ],
        "open_questions": [],
        "terminology": [
            claim(
                "trm",
                "v152-allowlist",
                statement="'allow-list' / 'allowlist' of object types replaced 'white-list' in the merged text.",
                kind="terminology",
                subkind="renamed",
                date="2021-10-24",
                actors=["jmanico"],
                status="settled",
                citations=[commit_cit("71baa763")],
            )
        ],
        "key_sources": [
            {"kind": "issue", "number": 1084, "role": "drove_merge", "rank": 1},
            {"kind": "issue", "number": 807, "role": "made_actionable", "rank": 2},
            {"kind": "issue", "number": 2297, "role": "insecure_mechanisms", "rank": 3},
            {"kind": "issue", "number": 2990, "role": "untrusted_data", "rank": 4},
        ],
        "related_requirements": [],
        "external_references": [
            {
                "kind": "cwe",
                "id": "CWE-502",
                "title": "Deserialization of Untrusted Data",
                "url": "https://cwe.mitre.org/data/definitions/502.html",
                "cited_by": None,
            }
        ],
        "status": {
            "coverage": "authored",
            "lineage_state": "complete",
            "last_pipeline_run": None,
            "last_human_review": WHEN,
            "blocked_reason": None,
            "stale": False,
        },
    }


def requirement_v1112() -> dict:
    row = load_csv_row("asvs_5.0.0.csv", "V11.1.2")
    slot = load_csv_row("asvs_4.0.3.csv", "V1.6.4")
    return {
        "uid": mint_uid("V11.1.2"),
        "slug": "cryptographic-inventory",
        "current": {
            "release": "5.0.0",
            "id": "V11.1.2",
            "chapter_id": "V11",
            "chapter_name": "Cryptography",
            "section_id": "V11.1",
            "section_name": "Cryptographic Inventory and Documentation",
            "level": 2,
            "text": row["req_description"],
            "source": "sources/asvs/asvs_5.0.0.csv",
            "status": "current",
        },
        "master": {
            "id": "V11.1.2",
            "level": 2,
            "text": row["req_description"],
            "differs_from_release": False,
            "checked_at": "2026-08-24",
        },
        "identifiers": [
            {"release": "5.0.0", "id": "V11.1.2", "level": 2, "status": "current"},
            {"release": "pre-release", "id": "V1.6.4", "level": None, "status": "historical"},
            {"release": "pre-release", "id": "V1.6.5", "level": None, "status": "historical"},
            {"release": "4.0.3", "id": "V1.6.4", "level": 2, "status": "historical"},
        ],
        "lineage": {
            "origin_kind": "new_in_release",
            "predecessors": [
                {
                    "release": "4.0.3",
                    "id": "V1.6.4",
                    "relation": "replaced_slot",
                    "text": slot["req_description"],
                    "note": "ID-slot predecessor only. v4 V1.6.4 was about treating client-side secrets as insecure; that text was replaced, not modified, in commit 121e76b7.",
                }
            ],
            "mapping_entry": {
                "raw": "MODIFIED, MOVED FROM v4.0.3-1.6.4",
                "status": "MODIFIED",
                "agrees_with_git": False,
                "note": "Mapping tracks the 1.6.4 ID slot. Git shows new crypto-inventory content created as 1.6.5 then written into the 1.6.4 slot. Content is ADDED, not a modification of client-side secrets.",
            },
            "events": [
                event("2024-11-05", "added", "fddaa31a", "elarlang", "V1.6.5", "Created as 1.6.5 while importing inventory requirements from the V6 rewrite (#2212).", extra_cits=[pr_cit(2212)]),
                event("2024-11-20", "merged", "121e76b7", "tghosth", "V1.6.4", "Wrote crypto inventory into the 1.6.4 slot to resolve #685, replacing client-side secrets text.", extra_cits=[issue_cit(685), issue_cit(2376)]),
                event("2025-03-27", "renumbered", "d3a825b4", "elarlang", "V11.1.2", "Renumbered from 1.6.4 to 11.1.2 when V6 became V11."),
                event("2025-03-30", "reworded", "c270e676", "tghosth", "V11.1.2", "Changed 'should also document' to 'must also document' (#2820).", extra_cits=[pr_cit(2820)]),
                event("2025-04-10", "grammar", "64881b54", "elarlang", "V11.1.2", "Removed the doubled 'also' (#2908).", extra_cits=[issue_cit(2908)]),
            ],
            "provenance": human_prov(),
        },
        "summaries": [
            summary(
                "origin",
                "v1112-origin",
                "Cryptographic inventory is new in v5.0.0. It was drafted as 1.6.5 during the V6 cryptography rewrite, then tghosth reused the long-broken v4 1.6.4 (client-side secrets) slot so V1.6 would hold documentation requirements rather than a one-size-fits-all secrets rule (#685, open since 2019).",
                [issue_cit(685), pr_cit(2212)],
            ),
            summary(
                "evolution",
                "v1112-evolution",
                "After occupying 1.6.4, the control moved with cryptography from V1 to V6 to V11. Language was tightened from should to must, and a grammar fix removed a doubled 'also'. Mapping still says MODIFIED FROM 1.6.4; git disagrees on content.",
                [mapping_cit(), commit_cit("121e76b7")],
            ),
        ],
        "decisions": [
            claim(
                "dec",
                "v1112-replace",
                statement="The confusing client-side secrets requirement was replaced with a cryptographic inventory, rather than further reworded.",
                kind="decision",
                subkind="reworded",
                date="2024-11-20",
                actors=["tghosth"],
                status="settled",
                citations=[issue_cit(685), commit_cit("121e76b7")],
            )
        ],
        "open_questions": [],
        "terminology": [],
        "key_sources": [
            {"kind": "issue", "number": 685, "role": "slot_replacement", "rank": 1},
            {"kind": "pr", "number": 2212, "role": "crypto_rewrite", "rank": 2},
            {"kind": "issue", "number": 2376, "role": "documentation_scope", "rank": 3},
        ],
        "related_requirements": [
            {
                "uid": mint_uid("V11.1.4"),
                "id": "V11.1.4",
                "relation": "companion",
                "note": "Forward-looking migration plan for the same inventory, including post-quantum cryptography.",
            }
        ],
        "external_references": [],
        "status": {
            "coverage": "authored",
            "lineage_state": "complete",
            "last_pipeline_run": None,
            "last_human_review": WHEN,
            "blocked_reason": None,
            "stale": False,
        },
    }


def requirement_v1114() -> dict:
    row = load_csv_row("asvs_5.0.0.csv", "V11.1.4")
    return {
        "uid": mint_uid("V11.1.4"),
        "slug": "crypto-migration-plan",
        "current": {
            "release": "5.0.0",
            "id": "V11.1.4",
            "chapter_id": "V11",
            "chapter_name": "Cryptography",
            "section_id": "V11.1",
            "section_name": "Cryptographic Inventory and Documentation",
            "level": 3,
            "text": row["req_description"],
            "source": "sources/asvs/asvs_5.0.0.csv",
            "status": "current",
        },
        "master": {
            "id": "V11.1.4",
            "level": 3,
            "text": row["req_description"],
            "differs_from_release": False,
            "checked_at": "2026-08-24",
        },
        "identifiers": [
            {"release": "5.0.0", "id": "V11.1.4", "level": 3, "status": "current"},
            {"release": "pre-release", "id": "V11.8.1", "level": 3, "status": "historical"},
            {"release": "pre-release", "id": "V6.9.1", "level": 2, "status": "historical"},
        ],
        "lineage": {
            "origin_kind": "new_in_release",
            "predecessors": [],
            "mapping_entry": {
                "raw": "ADDED",
                "status": "ADDED",
                "agrees_with_git": True,
                "note": None,
            },
            "events": [
                event("2024-11-05", "added", "90c0053d", "elarlang", "V6.9.1", "Created as 6.9.1 requiring use of quantum-safe algorithms.", extra_cits=[issue_cit(2213)]),
                event("2024-11-12", "reworded", "fe13d57a", "danielcuthbert", "V6.9.1", "Rewrote from algorithm verification into inventory plus a PQC migration plan (#2251).", extra_cits=[issue_cit(2251)]),
                event("2025-03-23", "level_changed", "a9c34d63", "tghosth", "V6.9.1", "Level changed from 2 to 3 (#2695).", extra_cits=[issue_cit(2695)]),
                event("2025-03-27", "renumbered", "d3a825b4", "elarlang", "V11.8.1", "Renumbered from 6.9.1 to 11.8.1."),
                event("2025-04-17", "merged", "b4e61e64", "elarlang", "V11.1.4", "Merged 11.8.1 and 11.8.2 into 11.1.4 and generalised beyond PQC-only wording (#2912).", extra_cits=[issue_cit(2912), pr_cit(2972)]),
            ],
            "provenance": human_prov(),
        },
        "summaries": [
            summary(
                "origin",
                "v1114-origin",
                "V11.1.4 began as a v5 PQC implementation check (use quantum-safe algorithms). Within a week danielcuthbert rewrote it as documentation: keep an inventory and a migration plan, reflecting that PQC standards were still maturing (#2251).",
                [issue_cit(2251), commit_cit("fe13d57a")],
            ),
            summary(
                "evolution",
                "v1114-evolution",
                "The control moved from a dedicated PQC section (V6.9 / V11.8) into V11.1 after elarlang argued it was inventory, not implementation (#2912). randomstuff's wording — a plan for new cryptographic standards, such as PQC — was adopted in PR #2972. Level is 3.",
                [issue_cit(2912), pr_cit(2972), issue_cit(2695)],
            ),
        ],
        "decisions": [
            claim(
                "dec",
                "v1114-docs",
                statement="PQC coverage in ASVS is a documented migration plan, not a mandate to deploy PQC algorithms today.",
                kind="decision",
                subkind="reworded",
                date="2024-11-12",
                actors=["danielcuthbert"],
                status="settled",
                citations=[issue_cit(2251), commit_cit("fe13d57a")],
            ),
            claim(
                "dec",
                "v1114-merge",
                statement="The separate V11.8 PQC section was removed; 11.8.1 and 11.8.2 were merged into 11.1.4.",
                kind="decision",
                subkind="merged",
                date="2025-04-17",
                actors=["elarlang", "randomstuff", "danielcuthbert"],
                status="settled",
                citations=[issue_cit(2912), pr_cit(2972)],
            ),
        ],
        "open_questions": [],
        "terminology": [],
        "key_sources": [
            {"kind": "issue", "number": 2912, "role": "section_merge", "rank": 1},
            {"kind": "issue", "number": 2251, "role": "pqc_reframing", "rank": 2},
            {"kind": "pr", "number": 2972, "role": "implemented", "rank": 3},
        ],
        "related_requirements": [
            {
                "uid": mint_uid("V11.1.2"),
                "id": "V11.1.2",
                "relation": "depends_on",
                "note": "Current-state cryptographic inventory that this migration plan extends.",
            }
        ],
        "external_references": [],
        "status": {
            "coverage": "authored",
            "lineage_state": "complete",
            "last_pipeline_run": None,
            "last_human_review": WHEN,
            "blocked_reason": None,
            "stale": False,
        },
    }


def requirement_v1324() -> dict:
    row = load_csv_row("asvs_5.0.0.csv", "V13.2.4")
    slot = load_csv_row("asvs_4.0.3.csv", "V4.3.3")
    conceptual = load_csv_row("asvs_4.0.3.csv", "V12.6.1")
    return {
        "uid": mint_uid("V13.2.4"),
        "slug": "outbound-communication-allowlist",
        "current": {
            "release": "5.0.0",
            "id": "V13.2.4",
            "chapter_id": "V13",
            "chapter_name": "Configuration",
            "section_id": "V13.2",
            "section_name": "Backend Communication Configuration",
            "level": 2,
            "text": row["req_description"],
            "source": "sources/asvs/asvs_5.0.0.csv",
            "status": "current",
        },
        "master": {
            "id": "V13.2.4",
            "level": 2,
            "text": row["req_description"],
            "differs_from_release": False,
            "checked_at": "2026-08-24",
        },
        "identifiers": [
            {"release": "5.0.0", "id": "V13.2.4", "level": 2, "status": "current"},
            {"release": "pre-release", "id": "V14.7.3", "level": 2, "status": "historical"},
            {"release": "4.0.3", "id": "V4.3.3", "level": 2, "status": "historical"},
        ],
        "lineage": {
            "origin_kind": "new_in_release",
            "predecessors": [
                {
                    "release": "4.0.3",
                    "id": "V4.3.3",
                    "relation": "replaced_slot",
                    "text": slot["req_description"],
                    "note": "Mapping predecessor only. Step-up / anti-fraud text was deleted in April 2025 and is not in v5.0.0.",
                },
                {
                    "release": "4.0.3",
                    "id": "V12.6.1",
                    "relation": "conceptual",
                    "text": conceptual["req_description"],
                    "note": "Conceptual ancestor of the current allowlist text. The old 12.6.1 wording survives as V13.2.5.",
                },
            ],
            "mapping_entry": {
                "raw": "MODIFIED, MOVED FROM v4.0.3-4.3.3",
                "status": "MODIFIED",
                "agrees_with_git": False,
                "note": "Mapping follows the v5.0.be-14.7.3 slot (old 4.3.3). Commit e4c9d291 replaced that text entirely with a technology-agnostic allowlist drafted in #2951. Git wins; the mapping is misleading.",
            },
            "events": [
                event("2019-02-26", "added", "b6e0dfaf", "tghosth", "V12.6.1", "Conceptual origin: server allowlist of outbound resources (CWE 918)."),
                event("2023-10-01", "moved", "60f563df", "tghosth", "V14.7.1", "Moved 12.6.1 to configuration after #1324.", extra_cits=[issue_cit(1324), pr_cit(1343)]),
                event("2024-11-06", "moved", "1566dcf9", "tghosth", "V14.7.3", "v4 4.3.3 (config-change protection) landed in V14.7.3, the slot V13.2.4 would later inherit."),
                event("2025-04-14", "renumbered", "935c0292", "elarlang", "V13.2.4", "Reordered V13.2 so this slot briefly held the old 4.3.3 text (#2951).", extra_cits=[issue_cit(2951)]),
                event("2025-04-17", "reworded", "e4c9d291", "elarlang", "V13.2.4", "Replaced the 4.3.3-derived text with the technology-agnostic outbound allowlist from #2951.", extra_cits=[issue_cit(2951), pr_cit(2982)]),
            ],
            "provenance": human_prov(),
        },
        "summaries": [
            summary(
                "origin",
                "v1324-origin",
                "The current text is an April 2025 rewrite by elarlang, jmanico and tghosth (#2951, PR #2982): allowlist outbound communication at the application, web server, firewall, or a combination. It was written into the ID slot that had held v4 V4.3.3 (step-up authentication / anti-fraud), whose text was deleted and has no v5 successor. Anyone following the mapping file alone will be misled.",
                [issue_cit(2951), pr_cit(2982), mapping_cit()],
            ),
            summary(
                "evolution",
                "v1324-evolution",
                "The idea comes from V12.6.1, which #1324 recast as second-layer SSRF defence and moved to configuration. In #2951 the server-specific wording was judged too narrow (WAF or firewall may satisfy it). The old 12.6.1 text was kept as V13.2.5; the new broader principle took the 13.2.4 slot.",
                [issue_cit(1324), issue_cit(2951)],
            ),
            summary(
                "controversy",
                "v1324-controversy",
                "#3244, still open, now asks whether V1.3.6 should be removed and user-supplied URLs folded into V13.2.4, or whether V13.2.4 should be narrowed to global infrastructure allowlisting and a first-layer application control kept in V1/V2.",
                [issue_cit(3244)],
            ),
        ],
        "decisions": [
            claim(
                "dec",
                "v1324-agnostic",
                statement="The outbound allowlist must not dictate the implementation layer: application, web server, firewall, or a combination are all valid.",
                kind="decision",
                subkind="reworded",
                date="2025-04-17",
                actors=["elarlang", "jmanico", "tghosth"],
                status="settled",
                citations=[issue_cit(2951), pr_cit(2982)],
            )
        ],
        "open_questions": [
            claim(
                "oq",
                "v1324-ssrf-split",
                statement="Whether V13.2.4 should absorb V1.3.6's user-input SSRF concern or be narrowed to infrastructure-only allowlisting.",
                kind="open_question",
                subkind="unresolved",
                date="2026-02-19",
                actors=["elarlang", "tghosth", "jmanico"],
                status="disputed",
                citations=[issue_cit(3244)],
            )
        ],
        "terminology": [],
        "key_sources": [
            {"kind": "issue", "number": 2951, "role": "current_text", "rank": 1},
            {"kind": "pr", "number": 2982, "role": "implemented", "rank": 2},
            {"kind": "issue", "number": 1324, "role": "defence_in_depth", "rank": 3},
            {"kind": "issue", "number": 3244, "role": "open_overlap", "rank": 4},
        ],
        "related_requirements": [
            {
                "uid": mint_uid("V13.2.5"),
                "id": "V13.2.5",
                "relation": "companion",
                "note": "Retains the original server-configuration allowlist from V12.6.1.",
            },
            {
                "uid": mint_uid("V1.3.6"),
                "id": "V1.3.6",
                "relation": "overlaps",
                "note": "Application-layer SSRF allowlist whose sanitization language is under challenge in #3244.",
            },
        ],
        "external_references": [],
        "status": {
            "coverage": "authored",
            "lineage_state": "complete",
            "last_pipeline_run": None,
            "last_human_review": WHEN,
            "blocked_reason": None,
            "stale": False,
        },
    }


def requirement_v1325() -> dict:
    row = load_csv_row("asvs_5.0.0.csv", "V13.2.5")
    pred = load_csv_row("asvs_4.0.3.csv", "V12.6.1")
    return {
        "uid": mint_uid("V13.2.5"),
        "slug": "server-outbound-allowlist",
        "current": {
            "release": "5.0.0",
            "id": "V13.2.5",
            "chapter_id": "V13",
            "chapter_name": "Configuration",
            "section_id": "V13.2",
            "section_name": "Backend Communication Configuration",
            "level": 2,
            "text": row["req_description"],
            "source": "sources/asvs/asvs_5.0.0.csv",
            "status": "current",
        },
        "master": {
            "id": "V13.2.5",
            "level": 2,
            "text": row["req_description"],
            "differs_from_release": False,
            "checked_at": "2026-08-24",
        },
        "identifiers": [
            {"release": "5.0.0", "id": "V13.2.5", "level": 2, "status": "current"},
            {"release": "pre-release", "id": "V14.7.4", "level": 2, "status": "historical"},
            {"release": "pre-release", "id": "V14.6.1", "level": 1, "status": "historical"},
            {"release": "pre-release", "id": "V14.7.1", "level": 1, "status": "historical"},
            {"release": "4.0.3", "id": "V12.6.1", "level": 1, "status": "predecessor"},
        ],
        "lineage": {
            "origin_kind": "carried_forward",
            "predecessors": [
                {
                    "release": "4.0.3",
                    "id": "V12.6.1",
                    "relation": "grammar",
                    "text": pred["req_description"],
                    "note": "Near-verbatim move from Files/Resources SSRF protection to Configuration. 'allow list' became 'allowlist'; level L1 to L2.",
                }
            ],
            "mapping_entry": {
                "raw": "GRAMMAR, MOVED FROM v4.0.3-12.6.1",
                "status": "GRAMMAR",
                "agrees_with_git": True,
                "note": None,
            },
            "events": [
                event("2023-10-01", "moved", "60f563df", "tghosth", "V14.7.1", "Moved V12.6.1 to V14.7.1 as a configuration control (#1324).", extra_cits=[issue_cit(1324), pr_cit(1343)]),
                event("2024-09-15", "grammar", "5aec93ed", "tghosth", "V14.6.1", "Normalised 'allow list' to 'allowlist'."),
                event("2025-03-02", "moved", "f21d189e", "tghosth", "V14.7.4", "Config sections merged; requirement became 14.7.4.", extra_cits=[issue_cit(2657)]),
                event("2025-03-16", "level_changed", "33488d5d", "elarlang", "V14.7.4", "Level changed from L1 to L2 (#2703).", extra_cits=[issue_cit(2703)]),
                event("2025-03-27", "renumbered", "d3a825b4", "elarlang", "V13.2.4", "Renumbered to 13.2.4 during the V14 to V13 chapter move."),
                event("2025-04-14", "renumbered", "935c0292", "elarlang", "V13.2.5", "Reordered within V13.2; the 12.6.1 text settled at 13.2.5.", extra_cits=[issue_cit(2951)]),
            ],
            "provenance": human_prov(),
        },
        "summaries": [
            summary(
                "origin",
                "v1325-origin",
                "V13.2.5 is v4 V12.6.1: configure the web or application server with an allowlist of outbound resources. elarlang proposed moving it to configuration in 2019 (#610); tghosth then declined. #1324 later established it as second-layer SSRF defence, and PR #1343 moved it in 2023.",
                [issue_cit(1324), issue_cit(610), pr_cit(1343)],
            ),
            summary(
                "evolution",
                "v1325-evolution",
                "The text is almost unchanged aside from allowlist grammar. It passed through V14.7.1, V14.6.1, V14.7.4 and briefly V13.2.4 before landing at V13.2.5. Level is now L2. #2951 drafted broader technology-neutral wording that was applied to V13.2.4 instead of replacing this server-specific control. The v5 ID V13.2.5 previously belonged to an unrelated REST Content-Type check.",
                [issue_cit(2951), issue_cit(2703)],
            ),
        ],
        "decisions": [
            claim(
                "dec",
                "v1325-keep",
                statement="Server-level outbound allowlisting was kept as a separate layer from application-level SSRF validation (V5.2.6 / V1.3.6).",
                kind="decision",
                subkind="no_action",
                date="2022-08-08",
                actors=["elarlang", "tghosth"],
                status="settled",
                citations=[issue_cit(1324)],
            )
        ],
        "open_questions": [],
        "terminology": [
            claim(
                "trm",
                "v1325-allowlist",
                statement="'allow list' was standardised to 'allowlist' across the standard.",
                kind="terminology",
                subkind="renamed",
                date="2024-09-15",
                actors=["tghosth"],
                status="settled",
                citations=[commit_cit("5aec93ed")],
            )
        ],
        "key_sources": [
            {"kind": "issue", "number": 1324, "role": "defence_in_depth", "rank": 1},
            {"kind": "pr", "number": 1343, "role": "moved_to_config", "rank": 2},
            {"kind": "issue", "number": 2951, "role": "companion_split", "rank": 3},
        ],
        "related_requirements": [
            {
                "uid": mint_uid("V13.2.4"),
                "id": "V13.2.4",
                "relation": "companion",
                "note": "Broader, layer-agnostic allowlist written in 2025; this record keeps the original server-config wording.",
            },
            {
                "uid": mint_uid("V1.3.6"),
                "id": "V1.3.6",
                "relation": "companion",
                "note": "First-layer application SSRF allowlist in the #1324 model.",
            },
        ],
        "external_references": [
            {
                "kind": "cwe",
                "id": "CWE-918",
                "title": "Server-Side Request Forgery (SSRF)",
                "url": "https://cwe.mitre.org/data/definitions/918.html",
                "cited_by": None,
            }
        ],
        "status": {
            "coverage": "authored",
            "lineage_state": "complete",
            "last_pipeline_run": None,
            "last_human_review": WHEN,
            "blocked_reason": None,
            "stale": False,
        },
    }


def issue_3338() -> dict:
    snapshot_path = ROOT / "sources" / "issues" / "3338.json"
    raw = json.loads(snapshot_path.read_text(encoding="utf-8"))
    digest = sha256_bytes(canonical_json(raw).encode("utf-8"))
    comments = raw.get("comments") or []
    author = raw["author"]["login"] if isinstance(raw.get("author"), dict) else str(raw.get("author"))
    labels = [item["name"] if isinstance(item, dict) else str(item) for item in raw.get("labels") or []]
    participants = {author}
    for comment in comments:
        login = (comment.get("author") or {}).get("login")
        if login:
            participants.add(login)
    history = ROOT / "sources" / "issues" / "3338.history.json"
    return {
        "kind": "issue",
        "number": 3338,
        "url": "https://github.com/OWASP/ASVS/issues/3338",
        "title": raw["title"],
        "state": "open",
        "created_at": raw["createdAt"],
        "closed_at": None,
        "author": author,
        "participants": sorted(participants),
        "labels": labels,
        "source": {
            "snapshot": "sources/issues/3338.json",
            "snapshot_digest": digest,
            "history_snapshot": "sources/issues/3338.history.json" if history.exists() else None,
            "fetched_at": WHEN,
            "comment_count": len(comments),
            "has_edits": history.exists(),
            "previous_digest": None,
        },
        "triage": {
            "class": "proposal",
            "relevance": "requirement_bearing",
            "estimated_requirement_count": 3,
            "reason": "Proposes visual-deception / homoglyph protections and discusses V2.2.1, V1.1.1, and V1.5.3.",
            "provenance": human_prov(),
        },
        "summaries": [
            summary(
                "overview",
                "i3338-overview",
                "narfbg asked ASVS to address homoglyph and visual-deception attacks after a Wiz write-up of malicious OAuth app names. tghosth first argued that V1.1.1, V1.5.3 and V2.2.1 already form a canonicalize-then-validate pipeline. narfbg replied that mixed-script names are an attack on human cognition, not parsers, and that V2.2.1 is only an incidental home. The thread then drafted a dedicated control for unique authoritative names, rejected the word 'script' as colliding with executable code, and settled on 'writing system' plus section-level guidance citing Unicode TR #39. elarlang placed the likely home in V2.2. No text has been merged. jmanico's first comment was later edited.",
                [
                    issue_cit(
                        3338,
                        comment_id="IC_kwDOAYyWqM7rKkcV",
                        fragment="issuecomment-3945416469",
                        author="jmanico",
                        date="2026-02-23T15:24:31Z",
                        quote="homoglyphs are on the rise as an AI bypass",
                        edited_after=True,
                    )
                ],
            )
        ],
        "outcome": {
            "state": "unresolved",
            "resulting_changes": [],
            "closed_reason": None,
            "provenance": human_prov(),
        },
        "requirement_summaries": [
            {
                "id": mint_sub_id("rs", "3338-v221"),
                "requirement_uid": mint_uid("V2.2.1"),
                "requirement_id_at_time": "V2.2.1",
                "relevance": "primary",
                "body": "Discussion centred on whether homoglyph and mixed-writing-system checks belong in V2.2.1's general input validation or need a dedicated control. narfbg called V2.2.1 the closest existing match but incidental. Later drafts scoped the new text to unique authoritative names displayed for trust decisions, to be enforced on entry. elarlang agreed V2.2 is the first-choice section. No wording change to V2.2.1 itself has been agreed.",
                "decisions": [],
                "arguments": [
                    claim(
                        "arg",
                        "3338-v221-incidental",
                        statement="V2.2.1 can cover mixed-script checks only as a 'business expectation'; it does not hint at visual deception, so a dedicated requirement is preferred.",
                        kind="argument",
                        subkind="for",
                        date="2026-02-23",
                        actors=["narfbg"],
                        status="disputed",
                        citations=[
                            issue_cit(
                                3338,
                                comment_id="IC_kwDOAYyWqM7rPnWw",
                                fragment="issuecomment-3946739120",
                                author="narfbg",
                                date="2026-02-23T19:07:11Z",
                                edited_after=True,
                            )
                        ],
                    )
                ],
                "terminology": [
                    claim(
                        "trm",
                        "3338-writing-system",
                        statement="The thread dropped 'script' (which ASVS readers take as executable code) in favour of 'writing system', with homoglyph explanation in section text rather than the requirement.",
                        kind="terminology",
                        subkind="standardized",
                        date="2026-03-04",
                        actors=["tghosth", "elarlang", "narfbg"],
                        status="settled",
                        citations=[
                            issue_cit(
                                3338,
                                comment_id="IC_kwDOAYyWqM7uKsbN",
                                fragment="issuecomment-3995780813",
                                author="tghosth",
                                date="2026-03-04T07:25:12Z",
                            )
                        ],
                    )
                ],
                "open_questions": [
                    claim(
                        "oq",
                        "3338-new-req",
                        statement="Whether to add a dedicated V2.2 requirement for mixed writing systems in unique authoritative names, and the exact testable wording.",
                        kind="open_question",
                        subkind="unresolved",
                        date="2026-03-10",
                        actors=["narfbg", "tghosth", "elarlang"],
                        status="disputed",
                        citations=[issue_cit(3338)],
                    )
                ],
                "outcome": "no_change_yet",
                "citations": [issue_cit(3338)],
                "provenance": human_prov(),
            },
            {
                "id": mint_sub_id("rs", "3338-v111"),
                "requirement_uid": mint_uid("V1.1.1"),
                "requirement_id_at_time": "V1.1.1",
                "relevance": "mentioned",
                "body": "Raised as a canonicalize-first building block for confusable detection. narfbg rejected the link: a Cyrillic О in 'Outlook' is valid UTF-8 and an attack on human cognition, not on decoding.",
                "decisions": [],
                "arguments": [],
                "terminology": [],
                "open_questions": [],
                "outcome": "no_change_yet",
                "citations": [issue_cit(3338)],
                "provenance": human_prov(),
            },
            {
                "id": mint_sub_id("rs", "3338-v153"),
                "requirement_uid": mint_uid("V1.5.3"),
                "requirement_id_at_time": "V1.5.3",
                "relevance": "mentioned",
                "body": "Cited as encoding-consistency context only. Not proposed for change; the homoglyph threat does not require parser disagreement.",
                "decisions": [],
                "arguments": [],
                "terminology": [],
                "open_questions": [],
                "outcome": "no_change_yet",
                "citations": [issue_cit(3338)],
                "provenance": human_prov(),
            },
        ],
        "unmapped_topics": [
            {
                "topic": "Digit/letter confusion (0/O, 1/l) and font choice",
                "reason": "Raised by narfbg and explicitly deferred as a different mechanism from mixed writing systems.",
                "provenance": human_prov(),
            }
        ],
        "external_references": [
            {
                "kind": "spec",
                "id": None,
                "title": "Unicode Technical Standard #39",
                "url": "https://www.unicode.org/reports/tr39/",
                "cited_by": "tghosth",
            },
            {
                "kind": "article",
                "id": None,
                "title": "Detecting malicious OAuth applications",
                "url": "https://www.wiz.io/blog/detecting-malicious-oauth-applications",
                "cited_by": "narfbg",
            },
        ],
        "status": {
            "coverage": "authored",
            "last_pipeline_run": None,
            "last_human_review": WHEN,
            "stale": False,
        },
    }


def write_all() -> None:
    dump(ROOT / "data/requirements/V1/V1.3.6.json", requirement_v136())
    dump(ROOT / "data/requirements/V1/V1.3.8.json", requirement_v138())
    dump(ROOT / "data/requirements/V1/V1.5.2.json", requirement_v152())
    dump(ROOT / "data/requirements/V11/V11.1.2.json", requirement_v1112())
    dump(ROOT / "data/requirements/V11/V11.1.4.json", requirement_v1114())
    dump(ROOT / "data/requirements/V13/V13.2.4.json", requirement_v1324())
    dump(ROOT / "data/requirements/V13/V13.2.5.json", requirement_v1325())
    dump(ROOT / "data/issues/3338.json", issue_3338())
    for req_id, slug in [
        ("V1.1.1", "canonical-decode-once"),
        ("V1.5.3", "consistent-parser-encoding"),
        ("V2.2.1", "input-business-validation"),
        ("V5.3.2", "file-metadata-not-in-paths"),
    ]:
        chapter = req_id.split(".")[0]
        dump(
            ROOT / "data/requirements" / chapter / f"{req_id}.json",
            stub_requirement(req_id, slug),
        )


if __name__ == "__main__":
    write_all()
