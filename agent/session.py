"""One Claude Agent SDK session: build options, stream it, archive it, meter it.

``query_fn`` is injectable so tests feed a fake async generator of messages
instead of launching the CLI. Only ``build_options`` touches SDK types.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any, AsyncIterator, Callable

from agent import guards, tools

BUILTIN_TOOLS = ["Bash", "Read", "Edit", "Write", "Glob", "Grep", "WebFetch", "WebSearch"]


@dataclass
class SessionResult:
    cost_usd: float
    turns: int
    transcript_ref: str
    final_text: str
    is_error: bool = False


def allowed_tools(tools_allowed: list[str], excluded: list[str] | tuple[str, ...] = ()) -> list[str]:
    """Built-ins plus every mcp__chris__* tool, minus the ones this kind of session may not use."""
    return [t for t in tools_allowed if t not in excluded] + tools.mcp_names(exclude=excluded)


def build_options(services, system_prompt: str, tools_allowed: list[str], max_turns: int,
                  excluded: list[str] | tuple[str, ...] = ()):
    from claude_agent_sdk import ClaudeAgentOptions

    cfg = services.cfg
    env = {"ANTHROPIC_API_KEY": services.secrets.anthropic_key} if services.secrets.anthropic_key else {}
    # In production the CLI runs as a different OS user through this wrapper (see Dockerfile);
    # locally it is unset and the SDK uses its bundled CLI.
    cli_path = os.environ.get("CHRIS_CLI_PATH") or None
    return ClaudeAgentOptions(
        system_prompt=system_prompt,
        model=cfg.model,
        cwd=str(cfg.repo_dir),
        tools=list(tools_allowed),
        allowed_tools=allowed_tools(tools_allowed, excluded),
        permission_mode="dontAsk",
        mcp_servers={"chris": tools.make_server(services)},
        strict_mcp_config=True,
        setting_sources=[],  # nothing from the machine's ~/.claude or repo .claude leaks in
        hooks=guards.hook_matchers(services),
        env=env,
        cli_path=cli_path,
        max_turns=max_turns,
    )


async def _default_query(prompt: str, options) -> AsyncIterator[Any]:
    from claude_agent_sdk import query

    async for msg in query(prompt=prompt, options=options):
        yield msg


def _text_blocks(msg) -> list[str]:
    out = []
    for block in getattr(msg, "content", None) or []:
        t = getattr(block, "text", None)
        if isinstance(t, str) and t.strip():
            out.append(t)
    return out


async def run_session(
    services,
    kind: str,
    system_prompt: str,
    user_prompt: str,
    tools_allowed: list[str] | None = None,
    max_turns: int = 80,
    excluded: list[str] | tuple[str, ...] = (),
    query_fn: Callable[..., AsyncIterator[Any]] | None = None,
    options: Any = None,
) -> SessionResult:
    tools_allowed = BUILTIN_TOOLS if tools_allowed is None else tools_allowed
    archive = services.archive
    query_fn = query_fn or _default_query
    if options is None and query_fn is _default_query:
        options = build_options(services, system_prompt, tools_allowed, max_turns, excluded)

    start_ref = archive.append("session_start", {
        "kind": kind, "model": services.cfg.model, "max_turns": max_turns,
        "system_prompt": system_prompt, "user_prompt": user_prompt,
    })

    texts: list[str] = []
    cost = 0.0
    turns = 0
    is_error = False
    result_text = ""
    async for msg in query_fn(user_prompt, options):
        name = type(msg).__name__
        if name == "AssistantMessage":
            for t in _text_blocks(msg):
                texts.append(t)
                archive.append("assistant", {"kind": kind, "text": t})
        elif name == "ResultMessage":
            cost = float(getattr(msg, "total_cost_usd", None) or 0.0)
            turns = int(getattr(msg, "num_turns", 0) or 0)
            is_error = bool(getattr(msg, "is_error", False))
            result_text = getattr(msg, "result", None) or ""
            archive.append("session_result", {
                "kind": kind, "subtype": getattr(msg, "subtype", ""), "cost_usd": cost, "turns": turns,
                "is_error": is_error, "duration_ms": getattr(msg, "duration_ms", None),
                "result": result_text, "start": start_ref,
            })

    if cost:
        services.inference.add_usd(cost, f"{kind} session")
    final_text = result_text or (texts[-1] if texts else "")
    return SessionResult(cost_usd=cost, turns=turns, transcript_ref=start_ref,
                         final_text=final_text, is_error=is_error)
