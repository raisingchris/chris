"""run_sleep with a fake model that writes files: stubs, character enforcement, mail, letters, pause, tools."""

import dataclasses
import json
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from agent import session, sleep, tools
from conftest import archive_text
from test_loop import FakeGit
from test_session import fake_messages


def today(services) -> str:
    return datetime.now(services.archive.tz).strftime("%Y-%m-%d")


def model(writes: dict[str, str] | None = None, capture: dict | None = None):
    """A query_fn that 'does the work' by writing files into the repo before replying."""
    writes = writes or {}

    async def query_fn(prompt, options):
        if capture is not None:
            capture["prompt"] = prompt
        for rel, text in writes.items():
            p = Path(rel)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text)
        async for m in fake_messages()(prompt, options):
            yield m

    return query_fn


def fresh_git():
    return FakeGit()


def repo_file(repo, rel) -> Path:
    return repo / rel


# --- diaries -----------------------------------------------------------------------


async def test_stubs_written_when_model_writes_nothing(services, repo):
    res = await sleep.run_sleep(services, query_fn=model(), git_run=fresh_git())
    d = today(services)
    assert (repo / "memory/diary" / f"{d}.md").read_text() == "No diary written tonight.\n"
    assert (repo / "memory/diary" / f"{d}.agent.md").read_text().startswith("No agent diary")
    assert res.diary_stubbed and res.agent_diary_stubbed
    assert archive_text(services).count('"kind": "diary_stub"') == 2


async def test_model_diaries_kept(services, repo):
    d = today(services)
    q = model({str(repo / "memory/diary" / f"{d}.md"): "I met a stranger.\n",
               str(repo / "memory/diary" / f"{d}.agent.md"): "- state: +1 contact\n"})
    res = await sleep.run_sleep(services, query_fn=q, git_run=fresh_git())
    assert (repo / "memory/diary" / f"{d}.md").read_text() == "I met a stranger.\n"
    assert not res.diary_stubbed and not res.agent_diary_stubbed


# --- character diffs -----------------------------------------------------------------


async def test_uncited_character_diff_rejected_cited_kept(services, repo):
    d = today(services)
    good_ref = services.archive.append("tool", {"name": "recall", "query": "x"})
    character = repo / "memory/wiki/self/character.md"
    cited = f"- {d} — I answer mail first — evidence: {good_ref}"
    uncited = f"- {d} — I am fearless — evidence: archive:{d}#999"
    malformed = "- I like tea"
    q = model({str(character): f"# Character\n\n## Diffs\n{cited}\n{uncited}\n{malformed}\n"})
    res = await sleep.run_sleep(services, query_fn=q, git_run=fresh_git())
    text = character.read_text()
    assert cited in text and uncited not in text and malformed not in text
    assert sorted(res.rejected_diffs) == sorted([uncited, malformed])
    assert '"kind": "character_diff_rejected"' in archive_text(services) and '"n": 2' in archive_text(services)


async def test_diff_citing_yesterday_rejected(services, repo):
    d = today(services)
    character = repo / "memory/wiki/self/character.md"
    line = f"- {d} — old news — evidence: archive:2020-01-01#1"
    q = model({str(character): f"# Character\n\n## Diffs\n{line}\n"})
    await sleep.run_sleep(services, query_fn=q, git_run=fresh_git())
    assert line not in character.read_text()


# --- mail + parent note ---------------------------------------------------------------


async def test_daily_summary_to_both_parents_from_parent_note(services, repo):
    d = today(services)
    (repo / "memory/inbox/2026-09-01-hi.md").write_text('---\nfrom: parent-a\nsubject: "Hi"\n---\n\nhello\n')
    q = model({str(repo / "memory/parent_note.md"): "Today I learned to wait. Question: may I buy a domain?\n"})
    res = await sleep.run_sleep(services, query_fn=q, git_run=fresh_git())
    assert res.note_source == "parent_note"
    assert sorted(res.mail["to"]) == sorted(services.mail.parents.values())
    body = res.mail["text"]
    assert "may I buy a domain?" in body
    assert f"Chris's day, {d}. 1 new message(s)" in body
    assert "Food bill today $0.42 (soft $15 / hard $25). Council this week $0.00 of $10." in body
    assert "loops closed" in body
    # the note is filed as a letter, the working file is gone
    letter = repo / "memory/letters" / f"{d}-to-parents.md"
    assert letter.read_text().startswith("Today I learned to wait.")
    assert not (repo / "memory/parent_note.md").exists()
    assert res.letter == letter


async def test_summary_falls_back_to_diary(services, repo):
    d = today(services)
    q = model({str(repo / "memory/diary" / f"{d}.md"): "A quiet day.\n"})
    res = await sleep.run_sleep(services, query_fn=q, git_run=fresh_git())
    assert res.note_source == "diary" and "A quiet day." in res.mail["text"]
    assert not (repo / "memory/letters").exists()


# --- housekeeping ---------------------------------------------------------------------


async def test_commit_unseal_odometer_and_redaction(services, repo, tmp_path):
    d = today(services)
    unsealed = []
    services.council.unseal_due = lambda: unsealed.append(1) or [Path("m.md")]
    q = model({str(repo / "memory/diary" / f"{d}.md"): "Alice Realname wrote to me.\n"})
    git = fresh_git()
    res = await sleep.run_sleep(services, query_fn=q, git_run=git)
    assert ("commit", "-m", f"sleep: {d}") in git.calls and ("push",) not in git.calls  # dry_run
    assert res.commit == "abc123" and res.unsealed == 1
    assert "Alice Realname" not in (repo / "memory/diary" / f"{d}.md").read_text()
    assert list((tmp_path / "redaction").glob("*.json"))
    assert res.odometer_line.startswith("0 in world-days")
    assert '"kind": "sleep_done"' in archive_text(services) or "sleep_done" in archive_text(services)


async def test_card_transactions_become_ledger_rows(services, repo):
    class CardWithHistory:
        card_id = "card_1"

        def transactions(self, since_iso):
            assert "T00:00:00" in since_iso  # start of yesterday, in her timezone
            return [{"ts": "t", "amount": 4.5, "ccy": "USD", "merchant": "Namecheap", "ref": "txn_1"},
                    {"ts": "t", "amount": 1.0, "ccy": "USD", "merchant": "", "ref": None}]

    services.card = CardWithHistory()
    services.cfg = dataclasses.replace(services.cfg, dry_run=False)
    git = fresh_git()
    res = await sleep.run_sleep(services, query_fn=model(), git_run=git)
    assert res.ledger_rows == 1
    assert services.ledger.rows == [{"type": "spend", "amount": "4.50", "ccy": "USD", "counterparty": "Namecheap",
                                     "memo": "card", "ref": "txn_1"}]
    assert ("push",) in git.calls


async def test_card_skipped_in_dry_run(services):
    res = await sleep.run_sleep(services, query_fn=model(), git_run=fresh_git())
    assert res.ledger_rows == 0 and services.ledger.rows == []


# --- gates and tools --------------------------------------------------------------------


async def test_paused_does_nothing(services, repo):
    services.state_dir.mkdir(parents=True, exist_ok=True)
    (services.state_dir / "paused").write_text("{}")
    git = fresh_git()
    called = {}
    res = await sleep.run_sleep(services, query_fn=model(capture=called), git_run=git)
    assert res.skipped == "paused" and res.session is None
    assert called == {} and git.calls == []
    assert not list((repo / "memory/diary").glob("*.md"))
    assert services.mail.list_unread() == [] and '"reason": "paused"' in archive_text(services)


def test_sleep_tools_exclude_mail_money_council():
    allowed = session.allowed_tools(session.BUILTIN_TOOLS, sleep.SLEEP_EXCLUDED)
    for banned in ("mail_send", "council_ask", "card_details", "payment_link", "ledger_add", "odometer_claim"):
        assert f"mcp__chris__{banned}" not in allowed, banned
    for ok in ("recall", "scratch_read", "meters"):
        assert f"mcp__chris__{ok}" in allowed, ok
    assert set(tools.TOOL_NAMES) - set(sleep.SLEEP_EXCLUDED) == set(sleep.SLEEP_TOOLS)


async def test_prompt_has_archive_character_and_diaries(services, repo):
    for day in ("2026-09-01", "2026-09-02", "2026-09-03", "2026-09-04"):
        (repo / "memory/diary" / f"{day}.md").write_text(f"diary {day}\n")
    services.archive.append("tool", {"name": "recall", "output": "x" * 2000})
    seen = {}
    await sleep.run_sleep(services, query_fn=model(capture=seen), git_run=fresh_git())
    p = seen["prompt"]
    assert "It's bedtime." in p and "## Today's archive" in p
    assert "[tool]" in p and "x" * 2000 not in p  # payload truncated
    assert "# Character" in p
    assert "diary 2026-09-01" not in p and "diary 2026-09-02" in p


def test_render_archive_drops_middle():
    recs = [{"ref": f"archive:2026-09-06#{i}", "ts": "2026-09-06T10:00:00", "kind": "k", "payload": {"i": i, "pad": "y" * 100}}
            for i in range(1, 201)]
    out = sleep.render_archive(recs, limit=3000)
    assert len(out) < 3500
    assert "archive:2026-09-06#1 " in out and "archive:2026-09-06#200 " in out
    assert "records dropped from the middle" in out and "archive:2026-09-06#100 " not in out
    assert sleep.render_archive([]) == "(nothing archived today)"
