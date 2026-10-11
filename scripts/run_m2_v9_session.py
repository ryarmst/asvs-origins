"""Generate V9 pilot drafts with a session-local provider (no vendor API)."""

from __future__ import annotations

import json
import re
import sys

from pipeline.llm import pass_a, pass_b, pass_c, queue
from pipeline.llm.context import chapter_issue_numbers
from pipeline.llm.provider import FunctionProvider

UID = {
    "V9.1.1": "req-a349c369",
    "V9.1.2": "req-1cc2640a",
    "V9.1.3": "req-7f78399e",
    "V9.2.1": "req-0d8b976d",
    "V9.2.2": "req-d55ba64d",
    "V9.2.3": "req-9a30c8c7",
    "V9.2.4": "req-914acfba",
}

# Issues that actually discuss 5.0.0 V9 (self-contained tokens), not 4.x V9 TLS/HSTS.
BEARING = {
    839: ("wording", "requirement_bearing", 1, "Argues stateless token signature checks belong at L1."),
    1012: ("defect", "requirement_bearing", 1, "Reports an error in the 3.5.3 token-signing text."),
    1439: ("clarification", "requirement_bearing", 2, "Asks whether 3.5.3 and 3.5.5 are duplicates."),
    1917: ("proposal", "chapter_bearing", 4, "Cleanup of the V3.5 token section that later became V9."),
    2184: ("wording", "requirement_bearing", 2, "Reword 3.5.3 to signature-or-MAC and drop 'session'."),
    2185: ("proposal", "requirement_bearing", 1, "Token validity window (nbf/exp) as its own control."),
    2204: ("wording", "requirement_bearing", 1, "Allowlist of algorithms and None for 3.5.5."),
    2261: ("proposal", "chapter_bearing", 3, "JWT spec coverage review feeding V9 splits."),
    2360: ("proposal", "requirement_bearing", 1, "Allowlist/None wording; closed as covered by 3.5.5."),
    2361: ("proposal", "requirement_bearing", 1, "Key-confusion split that became V9.1.2."),
    2362: ("proposal", "requirement_bearing", 1, "Trusted key sources for token validation."),
    2363: ("proposal", "requirement_bearing", 1, "Audience restriction for tokens."),
    2384: ("process", "chapter_bearing", 7, "Where to move V3.5; decided as a dedicated token chapter."),
    2414: ("wording", "requirement_bearing", 7, "Defines 'self-contained token' used by V9."),
    2698: ("process", "chapter_bearing", 7, "Level changes for the V9 chapter."),
}

ISSUE_RE = re.compile(r"/issues/(\d+)")


def _issue_no(text: str) -> int | None:
    match = ISSUE_RE.search(text)
    return int(match.group(1)) if match else None


def triage(system: str, user: str) -> dict:
    data = json.loads(user)
    number = data.get("number") or _issue_no(data.get("url") or user)
    if number in BEARING:
        klass, relevance, count, reason = BEARING[number]
        return {
            "class": klass,
            "relevance": relevance,
            "estimated_requirement_count": count,
            "reason": reason,
        }
    return {
        "class": "process",
        "relevance": "no_requirement",
        "estimated_requirement_count": 0,
        "reason": "Not about 5.0.0 V9 self-contained tokens (ID collision, other chapter, or process).",
    }


def _cite(url: str, issue: int, author: str | None = None, date: str | None = None, quote: str | None = None) -> dict:
    cite = {"type": "issue_comment" if "#" in url else "issue_body", "url": url, "issue": issue}
    if author:
        cite["author"] = author
    if date:
        cite["date"] = date
    if quote:
        cite["quote"] = quote
    return cite


def _slice(req_id: str, body: str, issue: int, url: str, outcome: str, *, relevance: str = "primary", arguments=None, decisions=None, terminology=None) -> dict:
    return {
        "requirement_uid": UID[req_id],
        "requirement_id_at_time": "V3.5.3" if req_id == "V9.1.1" else req_id,
        "relevance": relevance,
        "body": body,
        "outcome": outcome,
        "decisions": decisions or [],
        "arguments": arguments or [],
        "terminology": terminology or [],
        "open_questions": [],
        "citations": [_cite(url, issue)],
    }


def _overview(body: str, issue: int, url: str) -> dict:
    return {
        "summaries": [{"kind": "overview", "body": body, "citations": [_cite(url, issue)], "confidence": "high"}],
        "outcome": {"state": "accepted", "resulting_changes": [], "closed_reason": None},
        "requirement_summaries": [],
        "unmapped_topics": [],
        "external_references": [],
    }


PASS_B = {
    839: {
        "summaries": [
            {
                "kind": "overview",
                "body": "marcwickenden reported that L1 testing missed unsigned JWTs. jmanico agreed signature verification is basic JWT security and asked for a PR. elarlang asked whether alg:None should be mentioned; jmanico thought libraries had fixed None since about 2017. The control later landed at L1 as today's V9.1.1.",
                "citations": [_cite("https://github.com/OWASP/ASVS/issues/839", 839)],
                "confidence": "high",
            }
        ],
        "outcome": {"state": "accepted", "resulting_changes": ["3.5.3 added to L1"], "closed_reason": None},
        "requirement_summaries": [
            _slice(
                "V9.1.1",
                "The issue established that verifying a digital signature on a stateless token is an L1 control, after a tester found JWTs accepted without signature checks.",
                839,
                "https://github.com/OWASP/ASVS/issues/839",
                "changed",
                arguments=[
                    {
                        "statement": "Signature enforcement on JWTs is the most absolute basics of JWT security.",
                        "subkind": "for",
                        "date": "2020-09-10",
                        "actors": ["jmanico"],
                        "status": "settled",
                        "citations": [
                            _cite(
                                "https://github.com/OWASP/ASVS/issues/839#issuecomment-690498055",
                                839,
                                "jmanico",
                                "2020-09-10T16:52:51Z",
                                "this is the most absolute basics when it comes to JWT security",
                            )
                        ],
                    }
                ],
            ),
            _slice(
                "V9.1.2",
                "elarlang asked whether the L1 signing control should say alg:None is not ok. jmanico thought None was already fixed in libraries; elarlang had not seen None recently. None later lives on the algorithm-allowlist requirement, not on V9.1.1.",
                839,
                "https://github.com/OWASP/ASVS/issues/839#issuecomment-798540831",
                "deferred",
                relevance="secondary",
            ),
        ],
        "unmapped_topics": [],
        "external_references": [],
    },
    2184: {
        "summaries": [
            {
                "kind": "overview",
                "body": "Spin-off from #1917. elarlang dropped 'session' from 3.5.3, allowed MAC as well as signatures, and changed 'processing' to 'accepting' the token contents. jmanico liked the wording and wanted 3.5.5 kept separate as signature-type abuse. randomstuff asked that mixed MAC and public-key use (key confusion) be explicit. 3.5.3 was merged; 3.5.5 was left for another issue.",
                "citations": [_cite("https://github.com/OWASP/ASVS/issues/2184", 2184)],
                "confidence": "high",
            }
        ],
        "outcome": {
            "state": "accepted",
            "resulting_changes": ["3.5.3 wording: stateless tokens, signature or MAC, accept before use"],
            "closed_reason": None,
        },
        "requirement_summaries": [
            _slice(
                "V9.1.1",
                "Current V9.1.1 wording comes from this thread: self-contained/stateless tokens must be checked with a signature or MAC before the contents are accepted, not limited to session tokens.",
                2184,
                "https://github.com/OWASP/ASVS/issues/2184",
                "changed",
                decisions=[
                    {
                        "statement": "3.5.3 should say signature or MAC, and the check happens before accepting the token's contents.",
                        "subkind": "wording",
                        "date": "2024-10-23",
                        "actors": ["elarlang", "jmanico"],
                        "status": "settled",
                        "citations": [
                            _cite(
                                "https://github.com/OWASP/ASVS/issues/2184#issuecomment-2431572573",
                                2184,
                                "jmanico",
                                "2024-10-23T09:57:06Z",
                            )
                        ],
                    }
                ],
            ),
            _slice(
                "V9.1.2",
                "jmanico wanted algorithm allowlisting kept as a separate control from signature verification. randomstuff asked to forbid mixing MAC and public-key algorithms to prevent key confusion. That work was not merged here.",
                2184,
                "https://github.com/OWASP/ASVS/issues/2184#issuecomment-2432939387",
                "deferred",
                relevance="secondary",
            ),
        ],
        "unmapped_topics": [],
        "external_references": [],
    },
    2363: {
        "summaries": [
            {
                "kind": "overview",
                "body": "TobiasAhnoff proposed an access-token audience (and typ) check. elarlang insisted it be general for tokens, not only access tokens, and that OAuth V51.4.2 be rechecked so the general control does not duplicate it. The title was corrected from scope to audience. This is the origin of V9.2.3.",
                "citations": [_cite("https://github.com/OWASP/ASVS/issues/2363", 2363)],
                "confidence": "high",
            }
        ],
        "outcome": {"state": "accepted", "resulting_changes": ["general audience requirement"], "closed_reason": None},
        "requirement_summaries": [
            _slice(
                "V9.2.3",
                "The service must only accept tokens intended for it. The JWT example is validating aud against an allowlist. The thread rejected limiting the control to access tokens or to typ=at-jwt as the main rule.",
                2363,
                "https://github.com/OWASP/ASVS/issues/2363",
                "changed",
                decisions=[
                    {
                        "statement": "A general token audience check is required; do not limit it to access tokens.",
                        "subkind": "scope",
                        "date": "2024-11-10",
                        "actors": ["elarlang"],
                        "status": "settled",
                        "citations": [
                            _cite(
                                "https://github.com/OWASP/ASVS/issues/2363#issuecomment-2466724271",
                                2363,
                                "elarlang",
                                "2024-11-10T12:54:19Z",
                            )
                        ],
                    }
                ],
            )
        ],
        "unmapped_topics": [],
        "external_references": [],
    },
    2384: {
        "summaries": [
            {
                "kind": "overview",
                "body": "elarlang listed four homes for V3.5: a new cryptographically secured token chapter, V13 APIs, V5 validation, or leave it in session management. tghosth preferred leaving it; ryarmst warmed to a dedicated chapter for implementers; randomstuff asked about V6. The 5.0.0 result is chapter V9, Self-contained Tokens, with integrity vs content sections as option 1 sketched.",
                "citations": [_cite("https://github.com/OWASP/ASVS/issues/2384", 2384)],
                "confidence": "high",
            }
        ],
        "outcome": {"state": "accepted", "resulting_changes": ["V3.5 became chapter V9"], "closed_reason": None},
        "requirement_summaries": [
            _slice(
                "V9.1.1",
                "The chapter split put integrity (signature/MAC, algorithms, key source) in V9.1 and content (time, type, audience) in V9.2, matching elarlang's option 1 sketch.",
                2384,
                "https://github.com/OWASP/ASVS/issues/2384",
                "changed",
                relevance="mentioned",
            )
        ],
        "unmapped_topics": [],
        "external_references": [],
    },
    2414: {
        "summaries": [
            {
                "kind": "overview",
                "body": "Following #2384, ryarmst proposed glossary terms. Self-contained token means attributes that do not rely on server-side state, with authenticity and integrity of those attributes. Cryptographically secured token was updated as the broader signed/MAC'd family. That vocabulary is what V9's titles use.",
                "citations": [_cite("https://github.com/OWASP/ASVS/issues/2414", 2414)],
                "confidence": "high",
            }
        ],
        "outcome": {"state": "accepted", "resulting_changes": ["glossary: self-contained token"], "closed_reason": None},
        "requirement_summaries": [
            {
                "requirement_uid": UID["V9.1.1"],
                "requirement_id_at_time": "V9.1.1",
                "relevance": "mentioned",
                "body": "The chapter name and requirement text say self-contained tokens because this glossary change replaced session-token framing.",
                "outcome": "changed",
                "decisions": [],
                "arguments": [],
                "terminology": [
                    {
                        "statement": "A self-contained token encapsulates attributes that do not rely on server-side state, with authenticity and integrity of those attributes.",
                        "subkind": "definition",
                        "date": "2024-11-01",
                        "actors": ["ryarmst"],
                        "status": "settled",
                        "citations": [_cite("https://github.com/OWASP/ASVS/issues/2414", 2414, "ryarmst")],
                    }
                ],
                "open_questions": [],
                "citations": [_cite("https://github.com/OWASP/ASVS/issues/2414", 2414)],
            }
        ],
        "unmapped_topics": [],
        "external_references": [],
    },
    2185: {
        "summaries": [
            {
                "kind": "overview",
                "body": "Split from the V3.5 cleanup: if a token carries a validity window, accept it only inside that window. The JWT example is nbf and exp. This is V9.2.1.",
                "citations": [_cite("https://github.com/OWASP/ASVS/issues/2185", 2185)],
                "confidence": "medium",
            }
        ],
        "outcome": {"state": "accepted", "resulting_changes": ["time-window control"], "closed_reason": None},
        "requirement_summaries": [
            _slice(
                "V9.2.1",
                "Validity time span in the token data is checked at verification time. JWT nbf and exp are examples, not the only mechanism.",
                2185,
                "https://github.com/OWASP/ASVS/issues/2185",
                "changed",
            )
        ],
        "unmapped_topics": [],
        "external_references": [],
    },
    2362: {
        "summaries": [
            {
                "kind": "overview",
                "body": "Proposal to require key material for validating tokens to come from trusted pre-configured issuer sources, so attackers cannot point the verifier at a jku/x5u/jwk they control. This is V9.1.3.",
                "citations": [_cite("https://github.com/OWASP/ASVS/issues/2362", 2362)],
                "confidence": "medium",
            }
        ],
        "outcome": {"state": "accepted", "resulting_changes": ["trusted key source control"], "closed_reason": None},
        "requirement_summaries": [
            _slice(
                "V9.1.3",
                "Validation keys must come from trusted pre-configured sources for the issuer. For JWS, jku, x5u, and jwk are called out as headers that must be allowlisted.",
                2362,
                "https://github.com/OWASP/ASVS/issues/2362",
                "changed",
            )
        ],
        "unmapped_topics": [],
        "external_references": [],
    },
    2360: {
        "summaries": [
            {
                "kind": "overview",
                "body": "TobiasAhnoff proposed a strong-alg and None allowlist for access tokens. elarlang said current 3.5.5 already covered it after #2204, and wanted abstract token wording rather than access-token-specific text. ryarmst wondered if algorithm policy belonged in V6. The issue was treated as a duplicate/split discussion, not a new control.",
                "citations": [_cite("https://github.com/OWASP/ASVS/issues/2360", 2360)],
                "confidence": "high",
            }
        ],
        "outcome": {"state": "no_action", "resulting_changes": [], "closed_reason": "Covered by 3.5.5 / later V9.1.2"},
        "requirement_summaries": [
            _slice(
                "V9.1.2",
                "The allowlist, None, and key-confusion ideas were already in 3.5.5. This issue did not add a separate access-token-only control.",
                2360,
                "https://github.com/OWASP/ASVS/issues/2360",
                "rejected",
            )
        ],
        "unmapped_topics": [],
        "external_references": [],
    },
}


def pass_b_fn(system: str, user: str) -> dict:
    data = json.loads(user.split("INPUT:\n", 1)[1])
    number = data["issue_snapshot"]["number"]
    if number in PASS_B:
        return PASS_B[number]
    url = data["issue_snapshot"]["url"]
    payload = _overview(
        "This issue was triaged as related to V9 but the discussion is not a source for a specific 5.0.0 V9 requirement slice.",
        number,
        url,
    )
    payload["requirement_summaries"] = []
    payload["unmapped_topics"] = [
        {"topic": "not V9-specific", "reason": "No current V9 requirement is actually decided in this thread."}
    ]
    payload["outcome"] = {"state": "no_action", "resulting_changes": [], "closed_reason": None}
    return payload


def pass_c_fn(system: str, user: str) -> dict:
    data = json.loads(user.split("INPUT:\n", 1)[1])
    req_id = data["current"]["id"]
    commit_cites = []
    for event in data.get("lineage_events") or []:
        for cite in event.get("citations") or []:
            if cite.get("url"):
                commit_cites.append(cite)
                break
        if len(commit_cites) >= 3:
            break
    issue_cites = []
    for item in data.get("issue_slices") or []:
        url = item.get("url")
        if url:
            issue_cites.append({"type": "issue_body", "url": url, "issue": item.get("issue")})
    cites = (issue_cites + commit_cites)[:6] or [{"type": "mapping", "url": "https://github.com/OWASP/ASVS"}]
    # mapping URL may fail postvalidate; prefer issue urls. If none, leave empty citations on summary? Schema allows empty citations array.
    if cites == [{"type": "mapping", "url": "https://github.com/OWASP/ASVS"}]:
        cites = []

    stories = {
        "V9.1.1": (
            "origin",
            "V9.1.1 is the L1 signature-or-MAC check on self-contained tokens. It comes from 4.0.3 V3.5.3 (stateless session tokens). Issue 839 pushed it to L1 after unsigned JWTs were missed in an L1 test. Issue 2184 dropped the session-only limit, allowed MAC as well as signatures, and required the check before accepting token contents.",
        ),
        "V9.1.2": (
            "origin",
            "V9.1.2 is new in 5.0.0. Algorithm allowlisting, rejection of None, and not mixing symmetric with asymmetric algorithms (key confusion) were argued next to 3.5.3 in #839, #2184, and #2360, then kept as a separate control rather than merged into signature verification.",
        ),
        "V9.1.3": (
            "origin",
            "V9.1.3 is new in 5.0.0. Issue 2362 asked that validation keys come from trusted pre-configured issuer sources so jku/x5u/jwk cannot name an attacker-controlled set. The JWT header names in the current text are examples of that decision.",
        ),
        "V9.2.1": (
            "origin",
            "V9.2.1 is new in 5.0.0. Issue 2185 split time-window validation out of the old V3.5 bundle: if the token carries a validity span, accept it only inside that span. nbf and exp are examples for JWTs.",
        ),
        "V9.2.2": (
            "origin",
            "V9.2.2 is new in 5.0.0. The supplied issues discuss audience and algorithm policy more than token type. From those sources, origin of the type/purpose check is only partly determined: issue 2363 mentioned typ as a possible JWT check, then de-emphasised it in favour of audience. Treat type/purpose as a companion split from the same V3.5 cleanup, with thinner issue evidence than V9.2.3.",
        ),
        "V9.2.3": (
            "origin",
            "V9.2.3 is new in 5.0.0. Issue 2363 proposed an audience check, first as access-token-specific, then generalised so any service accepts only tokens meant for it. JWT aud against an allowlist is the documented example.",
        ),
        "V9.2.4": (
            "origin",
            "V9.2.4 is new in 5.0.0. The supplied V9 issue slices do not record a dedicated thread on issuer key reuse across audiences. Origin cannot be determined from the supplied material beyond the chapter split in #2384 that created a token-content section.",
        ),
    }
    kind, body = stories[req_id]
    sources = []
    ranks = {"V9.1.1": [839, 2184, 2384], "V9.1.2": [2184, 2360, 839], "V9.1.3": [2362, 2384], "V9.2.1": [2185, 2384], "V9.2.2": [2363, 2384], "V9.2.3": [2363, 2384], "V9.2.4": [2384]}
    for rank, number in enumerate(ranks[req_id], start=1):
        sources.append({"kind": "issue", "number": number, "role": "discussion", "rank": rank})
    blocked = None
    if req_id == "V9.2.4":
        blocked = "No supplied issue slice explains the issuer-key-reuse clause; only the chapter move is attested."
    evo = {
        "kind": "evolution",
        "body": "Renumbering from V3.5.* into V9 is not itself a wording change. Material wording changes in this chapter are the L1 promotion and signature-or-MAC / accept-before-use edit for V9.1.1, and new 5.0.0 controls for algorithms, key source, time, type, and audience.",
        "citations": cites,
        "confidence": "medium",
    }
    return {
        "summaries": [
            {"kind": kind, "body": body, "citations": cites, "confidence": "medium" if cites else "low"},
            evo,
        ],
        "open_questions": [],
        "terminology": [],
        "decisions": [],
        "key_sources": sources,
        "blocked_reason": blocked,
    }


def main() -> int:
    extra = list(BEARING)
    numbers = sorted(set(chapter_issue_numbers("V9")) | set(extra))
    a_provider = FunctionProvider(triage, provider="cursor-session", model_id="grok-4.6")
    print("pass A", len(numbers), "issues")
    for number in numbers:
        print(f"  a {number}: {pass_a.run_one(number, a_provider)}")
    b_provider = FunctionProvider(pass_b_fn, provider="cursor-session", model_id="grok-4.6")
    b_targets = sorted(PASS_B)
    print("pass B", b_targets)
    for number in b_targets:
        print(f"  b {number}: {pass_b.run_one(number, 'V9', b_provider, force=True)}")
    c_provider = FunctionProvider(pass_c_fn, provider="cursor-session", model_id="grok-4.6")
    print("pass C", pass_c.run_chapter("V9", provider=c_provider, force=True))
    built = queue.build_queue("V9")
    print("queue", len(built["items"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
