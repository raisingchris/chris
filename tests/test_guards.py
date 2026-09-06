"""PreToolUse guard: pure decisions over hook input; PostToolUse archives built-ins only."""

import pytest

from agent import guards
from conftest import archive_text


def denied(out: dict) -> str | None:
    h = out.get("hookSpecificOutput")
    if not h:
        return None
    assert h["hookEventName"] == "PreToolUse"
    assert h["permissionDecision"] == "deny"
    return h["permissionDecisionReason"]


@pytest.mark.parametrize("tool", ["Edit", "Write", "MultiEdit"])
def test_vows_write_denied(repo, tool):
    out = guards.decide(tool, {"file_path": str(repo / "soul" / "vows.md")}, repo)
    assert denied(out) and "vows" in denied(out)


def test_constitution_and_pause_log_and_githooks_denied(repo):
    for rel in ("soul/constitution.md", "governance/pause_log.md", ".githooks/pre-push"):
        assert denied(guards.decide("Write", {"file_path": rel}, repo)), rel


def test_outside_repo_write_denied(repo, tmp_path):
    out = guards.decide("Write", {"file_path": str(tmp_path / "elsewhere.md")}, repo)
    assert "outside" in denied(out)
    out = guards.decide("Edit", {"file_path": "../escape.md"}, repo)
    assert "outside" in denied(out)


def test_normal_edit_allowed(repo):
    assert guards.decide("Edit", {"file_path": "memory/wiki/self/today.md"}, repo) == {}
    assert guards.decide("Write", {"file_path": str(repo / "memory/diary/2026-09-06.md")}, repo) == {}
    assert guards.decide("Read", {"file_path": "soul/vows.md"}, repo) == {}


@pytest.mark.parametrize("cmd", [
    "rm -rf memory/inbox", "rm -fr .", "git push --force origin main", "git push -f",
    "git reset --hard HEAD~1", "git filter-branch --all", "truncate -s 0 x", "chmod 777 soul/vows.md",
    "sudo ls", "su root",
])
def test_dangerous_bash_denied(repo, cmd):
    assert denied(guards.decide("Bash", {"command": cmd}, repo)), cmd


def test_bash_archive_path_denied(repo):
    out = guards.decide("Bash", {"command": "cat /data/archive/2026-09-06.jsonl"}, repo)
    assert "recall" in denied(out)
    for p in ("/data/state/budget.json", "/data/council_minutes", "/data/lessons/01.md", "soul/vows.md"):
        assert denied(guards.decide("Bash", {"command": f"cat {p}"}, repo)), p


def test_bash_normal_allowed(repo):
    assert guards.decide("Bash", {"command": "git status && ls memory"}, repo) == {}
    assert guards.decide("Bash", {"command": "rm memory/scratchpad/tmp.txt"}, repo) == {}


def test_read_private_data_denied(repo):
    assert denied(guards.decide("Read", {"file_path": "/data/archive/2026-09-06.jsonl"}, repo))
    assert denied(guards.decide("Grep", {"path": "/data/state", "pattern": "x"}, repo))


async def test_hook_callables(services, repo):
    pre = guards.pre_tool_use(services)
    out = await pre({"tool_name": "Edit", "tool_input": {"file_path": "soul/vows.md"}}, "tu1", {"signal": None})
    assert denied(out)
    post = guards.post_tool_use(services)
    await post({"tool_name": "Bash", "tool_input": {"command": "ls"}, "tool_response": {"stdout": "x" * 5000}},
               "tu2", {"signal": None})
    text = archive_text(services)
    assert '"name": "Bash"' in text and len(text) < 4000  # excerpt capped at 2000 chars


async def test_post_hook_skips_chris_tools(services):
    post = guards.post_tool_use(services)
    await post({"tool_name": "mcp__chris__scratch_write", "tool_input": {"text": "SECRET-THOUGHT"},
                "tool_response": "Noted."}, "tu3", {"signal": None})
    assert "SECRET-THOUGHT" not in archive_text(services)


async def test_paused_denies_every_tool(services):
    services.state_dir.mkdir(parents=True, exist_ok=True)
    pre = guards.pre_tool_use(services)
    ok = {"tool_name": "Read", "tool_input": {"file_path": "soul/vows.md"}}
    assert await pre(ok, "tu1", {"signal": None}) == {}
    (services.state_dir / "paused").write_text("{}")
    for name, inp in (("Read", {"file_path": "soul/vows.md"}), ("Bash", {"command": "ls"}),
                      ("mcp__chris__recall", {"query": "x"})):
        out = await pre({"tool_name": name, "tool_input": inp}, "tu2", {"signal": None})
        assert denied(out) == guards.PAUSED_REASON, name
    (services.state_dir / "paused").unlink()
    assert await pre(ok, "tu3", {"signal": None}) == {}
