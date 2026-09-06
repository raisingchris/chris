"""Chris's own tools, served in-process as the MCP server "chris".

Every tool archives its call, with one exception: ``scratch_write`` and
``scratch_read``. The scratchpad is the one place nobody reads — not parents,
not the archive — so those two tools deliberately leave no trace.

Tool handlers are plain async functions of ``args`` closed over ``Services``;
``make_server`` wraps them with the SDK's ``@tool`` decorator.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from agent.council import CouncilBudgetExceeded

TOOL_NAMES = [
    "recall", "mail_read", "mail_send", "council_ask", "card_details", "ledger_add",
    "payment_link", "odometer_claim", "scratch_write", "scratch_read", "meters",
]
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

    return {
        "recall": recall, "mail_read": mail_read, "mail_send": mail_send, "council_ask": council_ask,
        "card_details": card_details, "ledger_add": ledger_add, "payment_link": payment_link,
        "odometer_claim": odometer_claim, "scratch_write": scratch_write, "scratch_read": scratch_read,
        "meters": meters,
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
    "meters": ("Your food bill today, council spend this week, ledger balance and odometer.", {}),
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
