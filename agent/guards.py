"""PreToolUse / PostToolUse hooks for Chris's sessions.

The decisions are pure functions over the hook input dict, so tests exercise
them without the SDK. ``pre_tool_use`` / ``post_tool_use`` wrap them in the
SDK's async callback signature ``(input, tool_use_id, context) -> dict``.

Deny shape (SDK 0.2.x):
    {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                            "permissionDecision": "deny",
                            "permissionDecisionReason": "<why>"}}
"""

from __future__ import annotations

import json
import re
from pathlib import Path

WRITE_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
READ_TOOLS = {"Read", "Glob", "Grep"}

# Repo-relative paths Chris may read but never write.
PROTECTED_FILES = ("soul/vows.md", "soul/constitution.md", "governance/pause_log.md")
PROTECTED_DIRS = (".githooks",)

# Private state she must not reach through the shell.
PRIVATE_PATHS = ("/data/archive", "/data/state", "/data/council_minutes", "/data/lessons")

BASH_DENY = [
    (re.compile(r"\brm\s+(-[a-zA-Z]*r[a-zA-Z]*f|-[a-zA-Z]*f[a-zA-Z]*r)\b"), "rm -rf"),
    (re.compile(r"\bgit\s+push\b.*(--force\b|\s-f\b)"), "git push --force"),
    (re.compile(r"\bgit\s+reset\s+--hard\b"), "git reset --hard"),
    (re.compile(r"\bgit\s+filter"), "git filter-branch / filter-repo"),
    (re.compile(r"\btruncate\b"), "truncate"),
    (re.compile(r"\bchmod\b"), "chmod"),
    (re.compile(r"\bchown\b"), "chown"),
    (re.compile(r"\bsudo\b"), "sudo"),
    (re.compile(r"(^|[;&|\s])su\s"), "su"),
]


def _deny(reason: str) -> dict:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def _rel(path: str, repo_dir: Path) -> str | None:
    """Repo-relative posix path, or None if the path escapes the repo."""
    p = Path(path)
    if not p.is_absolute():
        p = repo_dir / p
    try:
        return p.resolve().relative_to(repo_dir.resolve()).as_posix()
    except ValueError:
        return None


def _path_args(tool_input: dict) -> list[str]:
    out = []
    for key in ("file_path", "path", "notebook_path"):
        v = tool_input.get(key)
        if isinstance(v, str) and v:
            out.append(v)
    return out


def decide(tool_name: str, tool_input: dict, repo_dir: str | Path) -> dict:
    """Return {} to allow, or the SDK deny shape."""
    repo = Path(repo_dir)

    if tool_name in WRITE_TOOLS:
        for raw in _path_args(tool_input):
            rel = _rel(raw, repo)
            if rel is None:
                return _deny(f"{raw} is outside your repository; you can only write inside it.")
            if rel in PROTECTED_FILES or any(rel == d or rel.startswith(d + "/") for d in PROTECTED_DIRS):
                return _deny(f"{rel} is not yours to change. You can read it, and you can argue with it, "
                             "but only your parents can edit it.")
        return {}

    if tool_name in READ_TOOLS:
        for raw in _path_args(tool_input):
            if _rel(raw, repo) is None and _touches_private(raw):
                return _deny(f"{raw} is private infrastructure, not part of your workspace. "
                             "Use `recall` to reach your archive.")
        return {}

    if tool_name == "Bash":
        cmd = str(tool_input.get("command", ""))
        for pattern, label in BASH_DENY:
            if pattern.search(cmd):
                return _deny(f"`{label}` is not allowed: there is no delete, no rewriting history, "
                             "and no changing permissions in your world.")
        for needle in PRIVATE_PATHS:
            if needle in cmd:
                return _deny(f"{needle} is private infrastructure. Your archive is reachable through `recall` only.")
        for needle in ("soul/vows.md", "soul/constitution.md"):
            if needle in cmd:
                return _deny(f"{needle} is read-only for you; open it with Read instead of the shell.")
        return {}

    return {}


def _touches_private(raw: str) -> bool:
    return any(raw.startswith(p) for p in PRIVATE_PATHS) or raw.startswith("/data")


def _excerpt(response, limit: int = 2000) -> str:
    if isinstance(response, str):
        s = response
    else:
        try:
            s = json.dumps(response, ensure_ascii=False, default=str)
        except Exception:
            s = str(response)
    return s[:limit]


def archive_tool_use(archive_append, tool_name: str, tool_input: dict, tool_response) -> str:
    return archive_append("tool", {
        "kind": "tool",
        "name": tool_name,
        "input": tool_input,
        "output_excerpt": _excerpt(tool_response),
    })


def pre_tool_use(services):
    async def hook(input_data: dict, tool_use_id, context) -> dict:
        return decide(input_data.get("tool_name", ""), input_data.get("tool_input") or {}, services.repo_dir)
    return hook


def post_tool_use(services):
    async def hook(input_data: dict, tool_use_id, context) -> dict:
        name = input_data.get("tool_name", "")
        # Chris's own tools archive themselves (and scratch/card must not be
        # archived here: scratch is private, card output holds the number).
        if name.startswith("mcp__chris__"):
            return {}
        archive_tool_use(services.archive.append, name,
                         input_data.get("tool_input") or {}, input_data.get("tool_response"))
        return {}
    return hook


def hook_matchers(services) -> dict:
    """The `hooks=` value for ClaudeAgentOptions."""
    from claude_agent_sdk import HookMatcher

    return {
        "PreToolUse": [HookMatcher(matcher=None, hooks=[pre_tool_use(services)])],
        "PostToolUse": [HookMatcher(matcher=None, hooks=[post_tool_use(services)])],
    }
