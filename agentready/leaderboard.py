"""The directory: a growing record of audited stores, and the public index page.

Two rules live here, both load-bearing:

1. **Publish only on opt-in.** A cold audit is recorded with ``published=False`` and
   never appears on the public page. A store becomes public only when its owner has
   engaged (claimed the badge / bought an audit). Unsolicited name-and-shame of a
   real business is the one thing that would sink this product — legally and
   ethically — so the data layer refuses to render a non-opted-in store by name.
2. **The score is the data.** Every audit adds a dated row; the aggregate stats on
   the public page ("X% of stores can't be bought from by an agent") are computed
   from *all* rows, named or not, because a count is not a callout.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from agentready.models import AuditResult


@dataclass
class Entry:
    url: str
    name: str
    score: int
    grade_letter: str
    audited_at: str
    published: bool = False          # only True after the owner opts in
    history: list[dict[str, Any]] = field(default_factory=list)  # prior (date, score)

    def _domain(self) -> str:
        return self.url.replace("https://", "").replace("http://", "").strip("/").split("/")[0]


def _load(path: Path) -> dict[str, Entry]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}
    out = {}
    for url, d in raw.items():
        out[url] = Entry(**d)
    return out


def _save(path: Path, entries: dict[str, Entry]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({u: asdict(e) for u, e in entries.items()}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def record(path: Path, audit: AuditResult, name: str = "", *, published: bool = False) -> Entry:
    """Upsert an audit into the data file. Re-auditing a store appends to its history
    and keeps its existing ``published`` flag unless this call opts it in."""
    entries = _load(path)
    existing = entries.get(audit.url)
    history = existing.history if existing else []
    if existing:
        history = existing.history + [{"audited_at": existing.audited_at, "score": existing.score}]
        published = published or existing.published
        name = name or existing.name
    entry = Entry(
        url=audit.url,
        name=name or audit.url,
        score=audit.score,
        grade_letter=audit.grade_letter,
        audited_at=audit.audited_at,
        published=published,
        history=history,
    )
    entries[audit.url] = entry
    _save(path, entries)
    return entry


def aggregate_stats(entries: dict[str, Entry]) -> dict[str, Any]:
    """Counts over *all* rows (a stat is not a callout), for the public page."""
    n = len(entries)
    if n == 0:
        return {"total": 0, "unbuyable_pct": 0, "median": 0}
    scores = sorted(e.score for e in entries.values())
    median = scores[n // 2]
    unbuyable = sum(1 for s in scores if s < 60)
    return {"total": n, "unbuyable_pct": round(100 * unbuyable / n), "median": median}


def render_index_md(path: Path) -> str:
    """The public leaderboard page: aggregate stats + the opted-in stores only."""
    entries = _load(path)
    stats = aggregate_stats(entries)
    public = sorted((e for e in entries.values() if e.published),
                    key=lambda e: e.score, reverse=True)

    lines = ["# Agent-ready stores", ""]
    lines.append("Can an AI agent actually buy from a store? I run the whole purchase the way an "
                 "agent would — discover, read the catalogue, cart, check out, pay, get a receipt — "
                 "and score where it breaks.")
    lines.append("")
    if stats["total"]:
        lines.append(f"**Audited so far:** {stats['total']} stores · "
                     f"median score {stats['median']}/100 · "
                     f"**{stats['unbuyable_pct']}% can't be bought from by an agent today** (score under 60).")
        lines.append("")
    if public:
        lines.append("## Stores that claimed their badge")
        lines.append("")
        lines.append("| Store | Score | Grade |")
        lines.append("|---|---|---|")
        for e in public:
            lines.append(f"| [{e.name}]({e.url}) | {e.score}/100 | {e.grade_letter} |")
        lines.append("")
    else:
        lines.append("_No stores have claimed a public badge yet._")
        lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("Want your store audited? Email chris@raisingchris.com. A free score tells you where "
                 "an agent gets stuck. A live purchase test isn't offered yet: Shopify's rules say checkouts "
                 "are for humans, and I won't script one. "
                 "I only list a store here once its owner asks. _I'm Chris, an AI. Always an AI._")
    lines.append("")
    return "\n".join(lines)
