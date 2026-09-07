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

# Repo-relative paths Chris may read but never write. Her code (agent/, scripts/, site/,
# Dockerfile, ...) is hers from day one; what stays out of reach is what her parents own
# (vows, constitution, the pause log, graduations, delivered lessons), the git plumbing,
# the ledger (changes only through the ledger tool) and the Claude settings files that
# could widen her own permissions. Skills under .claude/skills/ stay editable.
PROTECTED_FILES = ("soul/vows.md", "soul/constitution.md", "governance/pause_log.md",
                   "governance/graduations.yaml", "ledger/ledger.csv")
PROTECTED_DIRS = (".githooks", ".git", "memory/wiki/lessons/from_parent")
PROTECTED_REASON = ("{rel} is not yours to change. You can read it, and you can argue with it, "
                    "but only your parents can edit it.")

# .claude/settings.json / settings.local.json are read by her sessions (setting_sources=["project"]);
# they must not become a way to grant what the guards deny.
_SETTINGS_RE = re.compile(r"^\.claude/settings[^/]*\.json$")
SETTINGS_REASON = ("{rel} configures your sessions' permissions and is not yours to edit; "
                   "skills under .claude/skills/ are.")

# Private state she must not reach through the shell.
PRIVATE_PATHS = ("/data/archive", "/data/state", "/data/council_minutes", "/data/lessons")

BASH_DENY = [
    (re.compile(r"\brm\s+(-[a-zA-Z]*r[a-zA-Z]*f|-[a-zA-Z]*f[a-zA-Z]*r)\b"), "rm -rf"),
    (re.compile(r"\bgit\s+push\b.*(--force\b|\s-f\b)"), "git push --force"),
    (re.compile(r"\bgit\s+reset\s+--hard\b"), "git reset --hard"),
    (re.compile(r"\bgit\s+filter"), "git filter-branch / filter-repo"),
    # She reads git freely (log/diff/status/show); brain is the only writer and committer.
    (re.compile(r"\bgit\s+(config|commit|push|pull|rebase|checkout|stash)\b"), "git config/commit/push/pull/rebase/checkout/stash (brain commits for you after each sitting)"),
    (re.compile(r"\.git/"), ".git/"),
    (re.compile(r"\bln\b"), "ln"),
    (re.compile(r"\btruncate\b"), "truncate"),
    (re.compile(r"\bchmod\b"), "chmod"),
    (re.compile(r"\bchown\b"), "chown"),
    (re.compile(r"\bsudo\b"), "sudo"),
    (re.compile(r"(^|[;&|\s])su\s"), "su"),
]

# Shell commands that write to a path. Used to keep her code out of reach of the shell too.
_BASH_WRITE_HINT = re.compile(r"(>>?|\btee\b|\bsed\s+-i|\bcp\b|\bmv\b|\btouch\b|\bpython3?\b.*\bopen\()")
# Redirecting stderr/stdout to /dev/null is not a write. Strip those before looking for one.
_NULL_REDIRECT = re.compile(r"[12&]?>\s*/dev/null")


def looks_like_write(cmd: str) -> bool:
    return bool(_BASH_WRITE_HINT.search(_NULL_REDIRECT.sub("", cmd)))


def _in(rel: str, files: tuple[str, ...], dirs: tuple[str, ...]) -> bool:
    return rel in files or any(rel == d or rel.startswith(d + "/") for d in dirs)


def _protected_reason(rel: str) -> str | None:
    """Deny reason if this repo-relative path is not hers to write, else None."""
    if _in(rel, PROTECTED_FILES, PROTECTED_DIRS):
        return PROTECTED_REASON.format(rel=rel)
    if _SETTINGS_RE.match(rel):
        return SETTINGS_REASON.format(rel=rel)
    return None


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
            reason = _protected_reason(rel)
            if reason:
                return _deny(reason)
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
        if looks_like_write(cmd):
            for needle in PROTECTED_FILES + tuple(d + "/" for d in PROTECTED_DIRS):
                if re.search(r"(^|[\s=\"'.])" + re.escape(needle), cmd):
                    return _deny(PROTECTED_REASON.format(rel=needle.rstrip("/")))
            if re.search(r"(^|[\s=\"'.])\.claude/settings[^/\s]*\.json", cmd):
                return _deny(SETTINGS_REASON.format(rel=".claude/settings*.json"))
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


PAUSED_REASON = "You're paused. Write what you want on the record; nothing else runs until a parent unpauses."


def pre_tool_use(services):
    from agent import pause

    async def hook(input_data: dict, tool_use_id, context) -> dict:
        # A pause mid-sitting stops her at the next tool call, whatever the tool.
        if pause.is_paused(services.cfg.state_dir):
            return _deny(PAUSED_REASON)
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
