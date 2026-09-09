"""Chris's own tools, served in-process as the MCP server "chris".

Every tool archives its call, with one exception: ``scratch_write`` and
``scratch_read``. The scratchpad is the one place nobody reads — not parents,
not the archive — so those two tools deliberately leave no trace.

Tool handlers are plain async functions of ``args`` closed over ``Services``;
``make_server`` wraps them with the SDK's ``@tool`` decorator.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from agent import tickets as tickets_mod
from agent.council import CouncilBudgetExceeded
from agent.dataforseo import DataForSEOBudgetExceeded, DataForSEOEndpointError

TOOL_NAMES = [
    "recall", "mail_read", "mail_send", "council_ask", "card_details", "ledger_add",
    "payment_link", "odometer_claim", "scratch_write", "scratch_read", "meters", "ticket", "tickets",
    "seo_data", "site_analytics", "search_console", "search_console_inspect",
]
NOT_CONFIGURED = "Google Analytics / Search Console is not configured; ask your parents."
SEO_DATA_CHARS = 60_000
RECENT_CLOSED = 5
SCRATCH = Path("memory") / "scratchpad" / "scratch.md"


def text(s: str) -> dict:
    return {"content": [{"type": "text", "text": s}]}


def _split_handles(to: str) -> list[str]:
    return [t.strip() for t in to.split(",") if t.strip()]


def make_handlers(services) -> dict[str, Callable[[dict], Any]]:
    """Name → async handler. Separated from the SDK so tests call them directly."""
    archive = services.archive
    mail = services.mail
    repo = services.repo_dir

    async def recall(args: dict) -> dict:
        query = str(args.get("query", ""))
        limit = int(args.get("limit", 10) or 10)
        hits = archive.search(query, limit=limit)
        lines = []
        for h in hits:
            # Raw archive may hold real parent addresses or names; map + redact before she sees them.
            body = mail.clean(str(h.get("payload", "")))
            lines.append(f"{h.get('ref')} [{h.get('kind')}] {h.get('ts', '')}\n{body}")
        archive.append("tool", {"name": "recall", "query": query, "limit": limit, "hits": [h.get("ref") for h in hits]})
        return text("\n\n".join(lines) if lines else "Nothing in the archive matches that.")

    async def mail_read(args: dict) -> dict:
        unread = mail.list_unread()
        parts = []
        for p in unread:
            parts.append(f"### {p.name}\n{p.read_text()}")
            mail.mark_read(p)
        archive.append("tool", {"name": "mail_read", "files": [p.name for p in unread]})
        return text("\n\n".join(parts) if parts else "No unread mail.")

    async def mail_send(args: dict) -> dict:
        to = _split_handles(str(args.get("to", "")))
        subject = str(args.get("subject", ""))
        body = str(args.get("body", ""))
        if not to:
            return text("mail_send needs at least one recipient.")
        result = mail.send(to, subject, body)  # archives mail_out with handles as given
        archive.append("tool", {"name": "mail_send", "to": to, "subject": subject, "dry_run": result.get("dry_run")})
        return text(f"Sent to {', '.join(to)}: {subject!r}" + (" (dry run)" if result.get("dry_run") else ""))

    async def council_ask(args: dict) -> dict:
        question = str(args.get("question", ""))
        context = str(args.get("context", "") or "")
        try:
            d = await services.council.deliberate(question, context)
        except CouncilBudgetExceeded as exc:
            archive.append("tool", {"name": "council_ask", "question": question, "refused": str(exc)})
            return text(str(exc))
        archive.append("tool", {"name": "council_ask", "question": question, "cost_usd": d.cost_usd,
                                "minutes": d.minutes_path.name})
        answers = "\n\n".join(f"## {name}\n{answer}" for name, answer in d.answers.items())
        return text(f"{answers}\n\n(Council cost ${d.cost_usd:.4f}; minutes sealed for 30 days.)")

    async def card_details(args: dict) -> dict:
        memo = str(args.get("memo", "")).strip()
        if not memo:
            return text("card_details needs a memo: what is this payment for?")
        # Only the memo is archived — never the number, expiry or cvc.
        archive.append("tool", {"name": "card_details", "kind": "card_details_requested", "memo": memo})
        try:
            d = services.card.details()
        except Exception as exc:
            return text(f"Card details unavailable: {exc}")
        return text(f"number: {d['number']}\nexpiry: {d['expiry_month']:02d}/{d['expiry_year']}\ncvc: {d['cvc']}\n"
                    "Put the spend in the ledger this sitting.")

    async def ledger_add(args: dict) -> dict:
        try:
            row = services.ledger.add(
                str(args.get("type", "")), float(args.get("amount", 0)), str(args.get("ccy", "USD")),
                str(args.get("counterparty", "")), str(args.get("memo", "")),
            )
        except Exception as exc:
            return text(f"Ledger refused: {exc}")
        archive.append("tool", {"name": "ledger_add", "row": row})
        return text(f"Ledger row added: {row}")

    async def payment_link(args: dict) -> dict:
        amount = int(args.get("amount_cents", 0))
        ccy = str(args.get("ccy", "USD"))
        name = str(args.get("name", ""))
        description = str(args.get("description", "") or "")
        try:
            url = services.payments.create_link(amount, ccy, name, description)
        except Exception as exc:
            return text(f"Could not create a payment link: {exc}")
        archive.append("tool", {"name": "payment_link", "amount_cents": amount, "ccy": ccy, "name": name, "url": url})
        return text(url)

    async def odometer_claim(args: dict) -> dict:
        loop_type = str(args.get("loop_type", ""))
        refs = args.get("evidence_refs") or []
        if isinstance(refs, str):
            refs = _split_handles(refs)
        note = str(args.get("note", ""))
        try:
            out = services.odometer.claim(loop_type, list(refs), note)
        except Exception as exc:
            archive.append("tool", {"name": "odometer_claim", "loop_type": loop_type, "refused": str(exc)})
            return text(f"Odometer refused: {exc}")
        archive.append("tool", {"name": "odometer_claim", "loop_type": loop_type, "refs": list(refs), "note": note})
        return text(f"Loop claimed: {out}")

    # The scratchpad is private. These two tools are the only ones that do NOT archive.
    async def scratch_write(args: dict) -> dict:
        path = repo / SCRATCH
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(str(args.get("text", "")).rstrip("\n") + "\n")
        return text("Noted.")

    async def scratch_read(args: dict) -> dict:
        path = repo / SCRATCH
        return text(path.read_text(encoding="utf-8") if path.exists() else "")

    async def meters(args: dict) -> dict:
        line = services.meters_line()
        archive.append("tool", {"name": "meters", "line": line})
        return text(line)

    async def ticket(args: dict) -> dict:
        title = str(args.get("title", ""))
        body = str(args.get("body", ""))
        try:
            path = tickets_mod.open_ticket(repo, title, body, datetime.now(archive.tz))
        except Exception as exc:  # noqa: BLE001 — ValueError (empty), OSError
            return text(f"Ticket refused: {exc}")
        tid = path.stem
        archive.append("tool", {"kind": "ticket", "name": "ticket", "id": tid, "title": title})
        return text(f"Ticket {tid} filed at {path.relative_to(repo).as_posix()}. It is public; your parents see it "
                    "on their page and in tonight's note, and answer in the same file. `tickets` shows the status.")

    async def tickets(args: dict) -> dict:
        open_ = tickets_mod.list_tickets(repo, "open")
        closed = [t for t in tickets_mod.list_tickets(repo) if t["status"] != "open"][:RECENT_CLOSED]
        lines = []
        for t in open_ + closed:
            line = f"{t['id']} [{t['status']}] {t['title']} (opened {t['opened'][:10]}"
            line += f", closed {t['closed'][:10]})" if t["closed"] else ")"
            if t["reply"]:
                line += "\n  Reply: " + t["reply"].replace("\n", "\n  ")
            lines.append(line)
        archive.append("tool", {"name": "tickets", "open": [t["id"] for t in open_], "closed": [t["id"] for t in closed]})
        return text("\n".join(lines) if lines else "No tickets yet.")

    async def seo_data(args: dict) -> dict:
        if services.dataforseo is None:
            return text("DataForSEO is not configured; ask your parents.")
        endpoint = str(args.get("endpoint", "")).strip()
        raw = args.get("payload_json", "")
        try:
            payload = json.loads(raw) if isinstance(raw, str) else raw
        except ValueError as exc:
            return text(f"payload_json is not valid JSON: {exc}")
        if not isinstance(payload, (list, dict)):
            return text("payload_json must be a JSON array (or one object) of task parameters.")
        try:
            out = await asyncio.to_thread(services.dataforseo.call, endpoint, payload)
        except DataForSEOBudgetExceeded as exc:
            archive.append("tool", {"name": "seo_data", "endpoint": endpoint, "refused": str(exc)})
            return text(str(exc))
        except DataForSEOEndpointError as exc:
            archive.append("tool", {"name": "seo_data", "endpoint": endpoint, "refused": str(exc)})
            return text(f"seo_data refused: {exc}")
        except Exception as exc:  # noqa: BLE001 — network errors come back as text, never a crash
            archive.append("tool", {"name": "seo_data", "endpoint": endpoint, "error": type(exc).__name__})
            return text(f"DataForSEO call failed: {type(exc).__name__}: {exc}")
        # The archive record was written by the proxy itself (endpoint, cost, status; no auth, no payload).
        body = json.dumps(out, ensure_ascii=False)
        if len(body) > SEO_DATA_CHARS:
            body = body[:SEO_DATA_CHARS] + f"\n\n[truncated: response was {len(body)} chars; narrow the query]"
        return text(body)

    def _json_list(raw, name: str, default: list[str]) -> tuple[list[str] | None, str | None]:
        if raw in (None, ""):
            return list(default), None
        try:
            val = json.loads(raw) if isinstance(raw, str) else raw
        except ValueError as exc:
            return None, f"{name} is not valid JSON: {exc}"
        if isinstance(val, str):
            val = [val]
        if not isinstance(val, list) or not all(isinstance(x, str) for x in val):
            return None, f"{name} must be a JSON array of strings, e.g. [\"date\",\"pagePath\"]."
        return val, None

    async def _analytics_call(name: str, fn, **kwargs) -> dict:
        try:
            out = await asyncio.to_thread(fn, **kwargs)
        except Exception as exc:  # noqa: BLE001 — network errors come back as text, never a crash
            from agent.google_auth import scrub

            archive.append("tool", {"name": name, "error": type(exc).__name__})
            return text(f"{name} failed: {type(exc).__name__}: {scrub(exc)}")
        # The archive record ({kind, api, status_code}) was written by Analytics itself.
        body = json.dumps(out, ensure_ascii=False)
        if len(body) > SEO_DATA_CHARS:
            body = body[:SEO_DATA_CHARS] + f"\n\n[truncated: response was {len(body)} chars; narrow the query]"
        return text(body)

    async def site_analytics(args: dict) -> dict:
        if services.google is None or services.analytics is None:
            return text(NOT_CONFIGURED)
        dims, err = _json_list(args.get("dimensions_json"), "dimensions_json", ["date"])
        if err:
            return text(err)
        mets, err = _json_list(args.get("metrics_json"), "metrics_json", ["activeUsers", "screenPageViews"])
        if err:
            return text(err)
        start = str(args.get("start", "") or "7daysAgo")
        end = str(args.get("end", "") or "today")
        limit = int(args.get("limit", 50) or 50)
        return await _analytics_call("site_analytics", services.analytics.ga4_report, dimensions=dims,
                                     metrics=mets, start=start, end=end, limit=limit)

    async def search_console(args: dict) -> dict:
        if services.google is None or services.analytics is None:
            return text(NOT_CONFIGURED)
        dims, err = _json_list(args.get("dimensions_json"), "dimensions_json", ["query"])
        if err:
            return text(err)
        start = str(args.get("start", "") or "")
        end = str(args.get("end", "") or "")
        if not start or not end:
            return text("search_console needs start and end dates (YYYY-MM-DD).")
        row_limit = int(args.get("row_limit", 50) or 50)
        return await _analytics_call("search_console", services.analytics.gsc_query, start=start, end=end,
                                     dimensions=dims, row_limit=row_limit)

    async def search_console_inspect(args: dict) -> dict:
        if services.google is None or services.analytics is None:
            return text(NOT_CONFIGURED)
        url = str(args.get("url", "") or "").strip()
        if not url:
            return text("search_console_inspect needs a url.")
        return await _analytics_call("search_console_inspect", services.analytics.gsc_inspect, url=url)

    return {
        "recall": recall, "mail_read": mail_read, "mail_send": mail_send, "council_ask": council_ask,
        "card_details": card_details, "ledger_add": ledger_add, "payment_link": payment_link,
        "odometer_claim": odometer_claim, "scratch_write": scratch_write, "scratch_read": scratch_read,
        "meters": meters, "ticket": ticket, "tickets": tickets, "seo_data": seo_data,
        "site_analytics": site_analytics, "search_console": search_console,
        "search_console_inspect": search_console_inspect,
    }


SCHEMAS: dict[str, tuple[str, dict]] = {
    "recall": ("Search your raw archive (everything that ever happened to you). Returns matching records, newest first.",
               {"query": str, "limit": int}),
    "mail_read": ("Read all unread mail in memory/inbox and mark it read.", {}),
    "mail_send": ("Send an email. `to` is comma-separated handles (parent-a, parent-b) or addresses. Signed with your disclosure.",
                  {"to": str, "subject": str, "body": str}),
    "council_ask": ("Ask your council for judgment (not action). Costs money against a $10/week cap.",
                    {"question": str, "context": str}),
    "card_details": ("Get your card number, expiry and CVC to pay for something. `memo` (what for) is required and archived.",
                     {"memo": str}),
    "ledger_add": ("Add a row to your public ledger. type: spend|revenue|refund|fee|allowance.",
                   {"type": str, "amount": float, "ccy": str, "counterparty": str, "memo": str}),
    "payment_link": ("Create a Stripe card-payment link so someone can pay you.",
                     {"amount_cents": int, "ccy": str, "name": str, "description": str}),
    "odometer_claim": ("Claim a closed loop for your odometer. Needs at least one archive:YYYY-MM-DD#N evidence ref.",
                       {"loop_type": str, "evidence_refs": list, "note": str}),
    "scratch_write": ("Append to your private scratchpad. Nobody reads it; it is not archived.", {"text": str}),
    "scratch_read": ("Read your private scratchpad.", {}),
    "meters": ("Your food bill today, council spend this week, DataForSEO spend this week, ledger balance and odometer.", {}),
    "ticket": ("File a request only your parents can act on (accounts, money, keys, a deploy, a human step). "
               "It is public. They answer in the same file.", {"title": str, "body": str}),
    "tickets": ("Your open tickets and the most recently closed ones, with status and your parents' reply.", {}),
    "seo_data": ("Query DataForSEO (SERPs, keyword volumes, backlinks, on-page audits, AI-search mentions) through "
                 "your body; the account is your parents'. Costs real money: about $0.002–0.02 per call, $5 a week "
                 "cap. endpoint = path under /v3/ e.g. 'serp/google/organic/live/regular'; payload_json = the JSON "
                 "array DataForSEO expects. Docs: https://docs.dataforseo.com/v3/",
                 {"endpoint": str, "payload_json": str}),
    "site_analytics": ("Visitors to your site (GA4). dimensions_json e.g. [\"date\",\"pagePath\"]; metrics_json "
                       "e.g. [\"activeUsers\",\"screenPageViews\"]; start/end are YYYY-MM-DD or 'today', "
                       "'yesterday', '7daysAgo'. Free; only you and your parents see the data.",
                       {"dimensions_json": str, "metrics_json": str, "start": str, "end": str, "limit": int}),
    "search_console": ("What people searched to find you on Google, and where you ranked. start/end YYYY-MM-DD; "
                       "dimensions_json e.g. [\"query\"], [\"page\"], [\"query\",\"page\"], [\"date\"]. "
                       "Rows carry clicks, impressions, ctr, position. Free.",
                       {"start": str, "end": str, "dimensions_json": str, "row_limit": int}),
    "search_console_inspect": ("Is one of your pages indexed by Google? Returns verdict, coverage state, last "
                               "crawl, canonical. Free.", {"url": str}),
}


def make_server(services):
    """Build the in-process MCP server the SDK session mounts as `mcp__chris__*`."""
    from claude_agent_sdk import create_sdk_mcp_server, tool

    handlers = make_handlers(services)
    sdk_tools = []
    for name in TOOL_NAMES:
        description, schema = SCHEMAS[name]
        sdk_tools.append(tool(name, description, schema)(handlers[name]))
    return create_sdk_mcp_server("chris", version="1.0.0", tools=sdk_tools)


def mcp_names(exclude: list[str] | tuple[str, ...] = ()) -> list[str]:
    return [f"mcp__chris__{n}" for n in TOOL_NAMES if n not in exclude]
