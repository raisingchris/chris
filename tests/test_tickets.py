"""Tickets: public requests only a parent can act on, answered in the same file."""

from datetime import datetime, timezone

import frontmatter
import pytest

from agent import tickets, tools
from conftest import archive_text

T0 = datetime(2026, 9, 7, 14, 30, tzinfo=timezone.utc)
T1 = datetime(2026, 9, 8, 9, 12, tzinfo=timezone.utc)


def out_text(result: dict) -> str:
    return result["content"][0]["text"]


def test_open_list_resolve_round_trip(repo):
    p = tickets.open_ticket(repo, "A GitHub token", "1. Open github.com/settings/tokens\n2. Paste it back.", T0)
    assert p == repo / "governance" / "tickets" / "20260907T1430-a-github-token.md"
    post = frontmatter.load(p)
    assert post["id"] == "20260907T1430-a-github-token" and post["status"] == "open" and post["by"] == "chris"
    assert post["opened"] == "2026-09-07T14:30:00+00:00"  # a string, not a YAML timestamp
    assert post.content.startswith("1. Open github.com")

    [t] = tickets.list_tickets(repo)
    assert t["title"] == "A GitHub token" and t["status"] == "open" and t["reply"] == "" and t["closed"] == ""
    assert tickets.list_tickets(repo, "done") == []

    q = tickets.resolve(repo, t["id"], "done", "Pasted into your inbox.", "parent-a", T1)
    assert q == p
    post = frontmatter.load(p)
    assert post["status"] == "done" and post["closed"] == "2026-09-08T09:12:00+00:00"
    assert "\n## Reply\n\n*parent-a, 2026-09-08T09:12:00+00:00 — done*\n\nPasted into your inbox.\n" in p.read_text()
    [t] = tickets.list_tickets(repo)
    assert t["status"] == "done" and t["reply"].endswith("Pasted into your inbox.")
    assert t["body"] == "1. Open github.com/settings/tokens\n2. Paste it back."
    assert tickets.list_tickets(repo, "open") == []
    assert [x["id"] for x in tickets.list_tickets(repo, "done")] == [t["id"]]


def test_resolve_refuses_bad_input(repo):
    p = tickets.open_ticket(repo, "Money", "Add $20.", T0)
    tid = p.stem
    with pytest.raises(ValueError):
        tickets.resolve(repo, tid, "maybe", "long enough reply", "parent-a", T1)
    with pytest.raises(ValueError):
        tickets.resolve(repo, tid, "done", "ok", "parent-a", T1)  # too short
    with pytest.raises(ValueError):
        tickets.resolve(repo, "../soul/vows", "done", "long enough reply", "parent-a", T1)
    with pytest.raises(FileNotFoundError):
        tickets.resolve(repo, "20260101T0000-nothing", "done", "long enough reply", "parent-a", T1)
    tickets.resolve(repo, tid, "declined", "Not this week.", "parent-b", T1)
    with pytest.raises(ValueError):  # closed is closed
        tickets.resolve(repo, tid, "done", "Changed my mind.", "parent-a", T1)


def test_two_tickets_in_one_minute_get_distinct_ids(repo):
    a = tickets.open_ticket(repo, "Same title", "body one", T0)
    b = tickets.open_ticket(repo, "Same title", "body two", T0)
    assert a.stem == "20260907T1430-same-title" and b.stem == "20260907T1430-same-title-2"
    assert [t["body"] for t in tickets.list_tickets(repo)] == ["body two", "body one"]  # newest first


def test_open_ticket_needs_title_and_body(repo):
    with pytest.raises(ValueError):
        tickets.open_ticket(repo, "", "body", T0)
    with pytest.raises(ValueError):
        tickets.open_ticket(repo, "title", "  ", T0)


def test_summary_line(repo):
    assert tickets.summary_line(repo) == ""
    tickets.open_ticket(repo, "A key", "please", T0)
    tickets.open_ticket(repo, "A deploy", "please", T1)
    assert tickets.summary_line(repo) == "2 open ticket(s) for you: A deploy; A key"


async def test_ticket_tool_files_and_archives(services, repo):
    h = tools.make_handlers(services)
    got = out_text(await h["ticket"]({"title": "Stripe live key", "body": "1. Dashboard → Developers → Keys.\n2. Paste it."}))
    assert "governance/tickets/" in got and "-stripe-live-key.md" in got
    files = list((repo / "governance" / "tickets").glob("*-stripe-live-key.md"))
    assert len(files) == 1
    text = archive_text(services)
    assert '"kind": "ticket"' in text and '"title": "Stripe live key"' in text and f'"id": "{files[0].stem}"' in text

    listing = out_text(await h["tickets"]({}))
    assert "[open] Stripe live key" in listing
    tickets.resolve(repo, files[0].stem, "declined", "Not until the first sale.", "parent-b", T1)
    listing = out_text(await h["tickets"]({}))
    assert "[declined] Stripe live key" in listing and "Reply:" in listing and "Not until the first sale." in listing

    assert "Ticket refused" in out_text(await h["ticket"]({"title": "", "body": "x"}))


async def test_tickets_tool_empty(services):
    h = tools.make_handlers(services)
    assert out_text(await h["tickets"]({})) == "No tickets yet."


def test_ticket_tools_are_registered():
    assert "ticket" in tools.TOOL_NAMES and "tickets" in tools.TOOL_NAMES
    assert "only your parents can act on" in tools.SCHEMAS["ticket"][0]


def test_meters_line_counts_open_tickets(services, repo):
    assert "open tickets" not in services.meters_line()
    tickets.open_ticket(repo, "A", "b", T0)
    tickets.open_ticket(repo, "C", "d", T1)
    assert services.meters_line().endswith(" · 2 open tickets")


def test_ticket_file_survives_redaction(repo):
    from agent.redaction import redact

    p = tickets.open_ticket(repo, "A key", "1. Open the dashboard.\n2. Paste it back.", T0)
    tickets.resolve(repo, p.stem, "done", "Pasted into your inbox.", "parent-a", T1)
    clean, report = redact(p.read_text(), ["Alice Realname"])
    assert clean == p.read_text() and report == []  # the YYYYMMDDTHHMM stamp is not a phone number
