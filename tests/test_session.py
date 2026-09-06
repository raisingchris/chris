"""run_session with a fake query_fn: cost metered, transcript archived, options shaped right."""

from types import SimpleNamespace

from agent import session
from conftest import archive_text


def fake_messages(cost=0.42, turns=3):
    """Mimics the SDK's AssistantMessage / ResultMessage by class name only."""
    AssistantMessage = type("AssistantMessage", (), {})
    ResultMessage = type("ResultMessage", (), {})

    async def query_fn(prompt, options):
        a = AssistantMessage()
        a.content = [SimpleNamespace(text="I read the letter."), SimpleNamespace(name="Read", input={})]
        yield a
        r = ResultMessage()
        r.subtype, r.total_cost_usd, r.num_turns, r.is_error = "success", cost, turns, False
        r.duration_ms, r.result = 1200, "Done for now."
        yield r

    return query_fn


async def test_cost_added_and_transcript_archived(services):
    res = await session.run_session(services, "sitting", "SYS", "USER", query_fn=fake_messages())
    assert res.cost_usd == 0.42 and res.turns == 3 and res.final_text == "Done for now."
    assert services.inference.spent() == 0.42
    assert res.transcript_ref.startswith("archive:")
    text = archive_text(services)
    assert "I read the letter." in text and "session_result" in text and '"user_prompt": "USER"' in text


async def test_zero_cost_not_metered(services):
    await session.run_session(services, "sitting", "S", "U", query_fn=fake_messages(cost=None))
    assert services.inference.spent() == 0.0


def test_allowed_tools_excludes_per_kind():
    got = session.allowed_tools(["Bash", "Read"], excluded=["mail_send", "Bash"])
    assert "Bash" not in got and "mcp__chris__mail_send" not in got
    assert "mcp__chris__recall" in got and "Read" in got


def test_build_options_shape(services):
    services.secrets.anthropic_key = "sk-test"
    opts = session.build_options(services, "SYS", session.BUILTIN_TOOLS, 80, excluded=["card_details"])
    assert opts.system_prompt == "SYS"
    assert opts.model == services.cfg.model
    assert opts.cwd == str(services.repo_dir)
    assert opts.permission_mode == "dontAsk"
    assert opts.max_turns == 80
    assert opts.env == {"ANTHROPIC_API_KEY": "sk-test"}
    assert opts.tools == session.BUILTIN_TOOLS
    assert "mcp__chris__recall" in opts.allowed_tools and "mcp__chris__card_details" not in opts.allowed_tools
    assert opts.mcp_servers["chris"]["type"] == "sdk"
    assert set(opts.hooks) == {"PreToolUse", "PostToolUse"}
