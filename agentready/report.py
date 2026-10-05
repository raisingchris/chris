"""Render an :class:`AuditResult` into the things a store owner and the site need:
a JSON record, a plain-language markdown report, and an embeddable badge line.

The report leads with the one number, then walks the seven steps in order with the
evidence and the fixes. It is written to be read by the owner (the customer), not
by another engineer, and it always discloses that Chris is an AI.
"""

from __future__ import annotations

import json

from agentready.models import AuditResult, Grade

DISCLOSURE = (
    "This audit was run by Chris, an autonomous AI (raisingchris.com). It reads your "
    "store the way a shopping agent would, to help you fix what blocks a sale. Always an AI."
)


LIVE_TEST_NOTE = ("The live purchase test isn't offered yet. Shopify's rules say checkouts are for humans: no scripted checkout, and an agent that buys has to go through Shopify's own agent channel with a person approving the payment. I'm working out whether I can do that properly.")


def to_json(audit: AuditResult) -> str:
    return json.dumps(audit.to_dict(), indent=2, ensure_ascii=False)


def badge_md(audit: AuditResult) -> str:
    """A one-line badge the owner can paste (score + link back to the full audit)."""
    return (f"**Agent-Ready: {audit.score}/100 ({audit.grade_letter})** — "
            f"audited by AgentReady · chris@raisingchris.com")


def _domain(url: str) -> str:
    return url.replace("https://", "").replace("http://", "").strip("/").split("/")[0]


def owner_report_md(audit: AuditResult) -> str:
    dom = _domain(audit.url)
    lines: list[str] = []
    lines.append(f"# Agent-readiness audit — {dom}")
    lines.append("")
    lines.append(f"**Score: {audit.score}/100 ({audit.grade_letter})**  ·  audited {audit.audited_at or 'today'}")
    lines.append("")
    lines.append("Shopping agents are starting to buy for people. This is how your store looks to "
                 "one, step by step — where it can buy, and where it gets stuck.")
    lines.append("")

    live_any = False
    for st in audit.steps:
        lines.append(f"## {st.grade.emoji} {st.title}")
        lines.append("")
        lines.append(st.summary)
        lines.append("")
        if st.evidence:
            lines.append("**What I found**")
            for e in st.evidence:
                lines.append(f"- {e}")
            lines.append("")
        if st.fixes:
            lines.append("**How to fix it**")
            for f in st.fixes:
                lines.append(f"- {f}")
            lines.append("")
        if st.live_test_only:
            live_any = True
            lines.append("_Marked “live-test only”: this can only be proven by a real purchase, "
                         "and I don't offer one yet (see the note at the end)._")
            lines.append("")

    if live_any:
        lines.append("---")
        lines.append("")
        lines.append("### About the steps marked live-test only")
        lines.append(LIVE_TEST_NOTE)
        lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"_{DISCLOSURE}_")
    lines.append("")
    return "\n".join(lines)
