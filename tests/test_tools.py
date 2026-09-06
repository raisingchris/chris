"""Chris's MCP tools, exercised through their handlers with fake money/council modules."""

from agent import tools
from conftest import PARENT_A, FakeCouncil, archive_text


def out_text(result: dict) -> str:
    return result["content"][0]["text"]


async def test_recall_maps_real_addresses_to_handles(services):
    services.archive.append("mail_in", {"from": f"Alice <{PARENT_A}>", "text": "hello from alice.realname"})
    h = tools.make_handlers(services)
    got = out_text(await h["recall"]({"query": "hello", "limit": 5}))
    assert PARENT_A not in got and "alice.realname" not in got
    assert "parent-a" in got
    # the recall itself is archived
    assert '"name": "recall"' in archive_text(services)


async def test_card_details_archives_memo_not_number(services):
    h = tools.make_handlers(services)
    got = out_text(await h["card_details"]({"memo": "domain renewal"}))
    assert "4111111111111111" in got
    text = archive_text(services)
    assert "domain renewal" in text and "card_details_requested" in text
    assert "4111111111111111" not in text and '"cvc"' not in text and "2030" not in text


async def test_card_details_requires_memo(services):
    h = tools.make_handlers(services)
    assert "memo" in out_text(await h["card_details"]({"memo": ""}))
    assert services.card.calls == 0


async def test_scratch_is_never_archived(services, repo):
    h = tools.make_handlers(services)
    await h["scratch_write"]({"text": "PRIVATE-THOUGHT"})
    assert "PRIVATE-THOUGHT" in out_text(await h["scratch_read"]({}))
    assert (repo / "memory/scratchpad/scratch.md").read_text() == "PRIVATE-THOUGHT\n"
    assert "PRIVATE-THOUGHT" not in archive_text(services)
    assert "scratch" not in archive_text(services)


async def test_council_budget_message_returned_as_text(services):
    services.council = FakeCouncil(exceeded=True)
    h = tools.make_handlers(services)
    got = out_text(await h["council_ask"]({"question": "Should I buy a domain?", "context": ""}))
    assert "weekly cap" in got
    assert "refused" in archive_text(services)


async def test_council_answers(services):
    h = tools.make_handlers(services)
    got = out_text(await h["council_ask"]({"question": "q", "context": "c"}))
    assert "## openai" in got and "sleep on it" in got


async def test_mail_read_and_send(services, repo):
    (repo / "memory/inbox/2026-09-06-hi.md").write_text("---\nfrom: parent-a\nsubject: \"hi\"\n---\n\nHello.\n")
    h = tools.make_handlers(services)
    got = out_text(await h["mail_read"]({}))
    assert "Hello." in got
    assert services.mail.list_unread() == []
    got = out_text(await h["mail_send"]({"to": "parent-a, parent-b", "subject": "Re: hi", "body": "Hi back."}))
    assert "parent-a, parent-b" in got
    assert PARENT_A not in archive_text(services)


async def test_ledger_payment_odometer_meters(services):
    h = tools.make_handlers(services)
    assert "Ledger row added" in out_text(await h["ledger_add"](
        {"type": "spend", "amount": 12.5, "ccy": "usd", "counterparty": "Namecheap", "memo": "domain"}))
    assert "stripe.com" in out_text(await h["payment_link"]({"amount_cents": 500, "ccy": "usd", "name": "tip"}))
    assert "refused" in out_text(await h["odometer_claim"]({"loop_type": "x", "evidence_refs": [], "note": ""}))
    assert "Loop claimed" in out_text(await h["odometer_claim"](
        {"loop_type": "x", "evidence_refs": ["archive:2026-09-06#1"], "note": "n"}))
    m = out_text(await h["meters"]({}))
    assert "Food bill today" in m and "Council this week" in m and "loops" in m


def test_make_server_builds_with_sdk(services):
    server = tools.make_server(services)
    assert server["type"] == "sdk" and server["name"] == "chris"
    assert tools.mcp_names(exclude=["mail_send"]) == [f"mcp__chris__{n}" for n in tools.TOOL_NAMES if n != "mail_send"]


async def test_recall_redacts_canaries_in_raw_payloads(services):
    services.archive.append("mail_in", {"data": {"from": f"Alice Realname <{PARENT_A}>", "subject": "hello there"}})
    h = tools.make_handlers(services)
    got = out_text(await h["recall"]({"query": "hello there", "limit": 5}))
    assert "Alice" not in got and PARENT_A not in got
    assert "parent-a" in got and "hello there" in got


async def test_mail_read_keeps_stranger_address_so_she_can_reply(services, repo):
    (repo / "memory/inbox/2026-09-06-q.md").write_text(
        '---\nfrom: someone@else.org\nsubject: "q"\nemail_id: "e9"\n---\n\nHello.\n')
    h = tools.make_handlers(services)
    got = out_text(await h["mail_read"]({}))
    assert "from: someone@else.org" in got and "Hello." in got
