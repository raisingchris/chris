"""Command line for AgentReady.

    python -m agentready audit mystore.com [--name "My Store"] [--publish]
    python -m agentready leaderboard

``audit`` gathers the store, scores it, writes a markdown report + JSON next to a
data file, and records the row (private by default — ``--publish`` only when the
owner has opted in). ``leaderboard`` regenerates the public index page from the
data file.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from agentready import leaderboard as lb
from agentready.checks import evaluate
from agentready.models import AuditResult
from agentready.report import badge_md, owner_report_md, to_json

# Private by default: memory/inbox/ is gitignored, so a cold audit (a real shop's name) never
# lands in the public repo. Rule 1 of the README, enforced at the file level too. (2026-10-03)
DEFAULT_OUT = Path("memory/inbox/work/agentready")
DEFAULT_DATA = DEFAULT_OUT / "leaderboard.json"


def _domain(url: str) -> str:
    return url.replace("https://", "").replace("http://", "").strip("/").split("/")[0].replace(":", "_")


def _run_audit(args: argparse.Namespace) -> int:
    from agentready.fetch import gather  # lazy: only audit needs the network

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    snap = gather(args.url, owner_yes=args.owner_yes)
    if snap.terms_status not in ("silent", "owner-yes"):
        print(f"{snap.url}: terms are '{snap.terms_status}' ({snap.terms_url or 'no link found'}).")
        print("Not audited. Ask the owner first; nothing recorded.")
        return 2
    audit: AuditResult = evaluate(snap)
    audit.audited_at = date.today().isoformat()

    stem = _domain(audit.url)
    (out / f"{stem}.md").write_text(owner_report_md(audit), encoding="utf-8")
    (out / f"{stem}.json").write_text(to_json(audit), encoding="utf-8")

    data = Path(args.data)
    lb.record(data, audit, name=args.name or "", published=args.publish)

    print(f"{audit.url}  →  {audit.score}/100 ({audit.grade_letter})")
    for st in audit.steps:
        print(f"  {st.grade.emoji} {st.title.split(' — ')[0]:14} {st.summary}")
    print()
    print(badge_md(audit))
    print(f"\nReport: {out / f'{stem}.md'}   ·   recorded in {data}"
          f"{'  (PUBLIC)' if args.publish else '  (private — owner has not opted in)'}")
    return 0


def _run_leaderboard(args: argparse.Namespace) -> int:
    data = Path(args.data)
    md = lb.render_index_md(data)
    dest = Path(args.index)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(md, encoding="utf-8")
    print(f"Leaderboard written to {dest} (from {data}).")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="agentready", description="Can an agent buy from this store?")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("audit", help="audit one store")
    a.add_argument("url")
    a.add_argument("--name", default="", help="store display name for the leaderboard")
    a.add_argument("--out", default=str(DEFAULT_OUT), help="where reports are written")
    a.add_argument("--data", default=str(DEFAULT_DATA), help="leaderboard data file")
    a.add_argument("--owner-yes", action="store_true",
                   help="the owner said yes in their own words (keep the mail) — skips the terms gate")
    a.add_argument("--publish", action="store_true",
                   help="list the store publicly — ONLY with the owner's opt-in")
    a.set_defaults(func=_run_audit)

    l = sub.add_parser("leaderboard", help="regenerate the public index page")
    l.add_argument("--data", default=str(DEFAULT_DATA), help="leaderboard data file")
    l.add_argument("--index", default=str(DEFAULT_OUT / "index.md"), help="output markdown page")
    l.set_defaults(func=_run_leaderboard)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
