"""Git as Chris: minimal environment, UTC timestamps, her identity, never force.

Every git call in the brain goes through ``git()``: it builds its environment
from scratch (never ``os.environ``), disables hooks and the fsmonitor on the
command line, and signs as Chris (or as "Parent" for the parent page). Chris's
sitting process cannot plant anything that brain would execute on commit.

``push_repo`` is gated: before anything leaves the box, the outgoing diff is run
through :mod:`agent.redaction` and the push is refused on any canary hit, and
``soul/vows.md`` / ``soul/constitution.md`` are reverted to ``origin/main`` if
a local commit touched them (they are not hers to edit).
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable

CHRIS = ("Chris", "chris@raisingchris.com")
PARENT = ("Parent", "parent@raisingchris.com")
CHRIS_NAME, CHRIS_EMAIL = CHRIS

UPSTREAM = "origin/main"
INVARIANT_FILES = ("soul/vows.md", "soul/constitution.md")
GIT_FLAGS = ("-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false")
BLOCKED_MARKER = "push_blocked"


def git_env(identity: tuple[str, str] = CHRIS) -> dict[str, str]:
    """A from-scratch environment for git: PATH, HOME, TZ=UTC, identity, no system config."""
    name, email = identity
    env = {
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "HOME": os.environ.get("GIT_HOME") or os.environ.get("HOME", ""),
        "TZ": "UTC",
        "GIT_AUTHOR_NAME": name,
        "GIT_AUTHOR_EMAIL": email,
        "GIT_COMMITTER_NAME": name,
        "GIT_COMMITTER_EMAIL": email,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_TERMINAL_PROMPT": "0",
    }
    ssh = os.environ.get("GIT_SSH_COMMAND")
    if ssh:
        env["GIT_SSH_COMMAND"] = ssh
    return env


def git(repo_dir: str | Path, *args: str, check: bool = True,
        identity: tuple[str, str] = CHRIS) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *GIT_FLAGS, *args], cwd=str(repo_dir), env=git_env(identity),
        capture_output=True, text=True, check=check,
    )


def git_as_parent(repo_dir: str | Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return git(repo_dir, *args, check=check, identity=PARENT)


def has_changes(repo_dir: str | Path, run=git) -> bool:
    return bool(run(repo_dir, "status", "--porcelain").stdout.strip())


@dataclass
class PushGate:
    """What ``push_repo`` needs to refuse a push that would leak or break an invariant."""

    canaries: list[str] = field(default_factory=list)
    archive_append: Callable[[str, dict], str] | None = None
    state_dir: Path | None = None

    @classmethod
    def from_services(cls, services) -> "PushGate":
        return cls(canaries=list(getattr(services.cfg, "canaries", []) or []),
                   archive_append=services.archive.append,
                   state_dir=Path(services.cfg.state_dir))

    def archive(self, kind: str, payload: dict) -> None:
        if self.archive_append is not None:
            try:
                self.archive_append(kind, {"kind": kind, **payload})
            except Exception:  # noqa: BLE001 — the gate must never raise
                pass

    def mark_blocked(self, why: str) -> None:
        if self.state_dir is not None:
            try:
                self.state_dir.mkdir(parents=True, exist_ok=True)
                (self.state_dir / BLOCKED_MARKER).write_text(why)
            except OSError:
                pass

    def clear_blocked(self) -> None:
        if self.state_dir is not None:
            try:
                (self.state_dir / BLOCKED_MARKER).unlink()
            except OSError:
                pass


def push_blocked_reason(state_dir: str | Path) -> str:
    """The reason the last push was refused by the gate, or "" if it was not."""
    try:
        return (Path(state_dir) / BLOCKED_MARKER).read_text().strip()
    except OSError:
        return ""


def _stdout(r) -> str:
    return str(getattr(r, "stdout", "") or "")


def enforce_invariants(repo_dir: str | Path, run=git, gate: PushGate | None = None) -> list[str]:
    """Revert any local change to the vows/constitution since upstream; returns the reverted paths."""
    r = run(repo_dir, "diff", "--name-only", UPSTREAM, "HEAD", "--", *INVARIANT_FILES, check=False)
    if getattr(r, "returncode", 0) != 0:
        return []
    changed = [ln.strip() for ln in _stdout(r).splitlines() if ln.strip()]
    if not changed:
        return []
    for path in changed:
        run(repo_dir, "checkout", UPSTREAM, "--", path, check=False)
    run(repo_dir, "commit", "-m", "revert: vows are not editable", "--", *changed, check=False)
    if gate is not None:
        gate.archive("invariant_violation", {"files": changed, "action": "reverted to " + UPSTREAM})
    return changed


def canary_hits(repo_dir: str | Path, canaries: Iterable[str], run=git) -> tuple[bool, list[dict]]:
    """(ok, report) for the outgoing diff. ok=False if the diff could not be read or holds a canary."""
    from agent import redaction

    r = run(repo_dir, "diff", f"{UPSTREAM}..HEAD", check=False)
    if getattr(r, "returncode", 0) != 0:
        return False, [{"kind": "diff_unavailable", "count": 1}]
    _, report = redaction.redact(_stdout(r), list(canaries))
    return not any(h["kind"] == "canary" for h in report), report


def push_repo(repo_dir: str | Path, run=git, gate: PushGate | None = None) -> tuple[bool, str]:
    """Push; never raises. Returns (ok, stderr excerpt). A failed or blocked push leaves the commit local."""
    try:
        if gate is not None:
            enforce_invariants(repo_dir, run, gate)
            ok, report = canary_hits(repo_dir, gate.canaries, run)
            if not ok:
                gate.archive("push_blocked_canary", {"report": report})
                gate.mark_blocked("identity hit")
                return False, "push blocked: identity hit"
        # A parent may have pushed since we last pulled (a deploy, a lesson, a changelog line).
        # Rebase our commits on top so her work lands instead of being rejected.
        f = run(repo_dir, "fetch", "--quiet", "origin", check=False)
        if f.returncode == 0:
            rb = run(repo_dir, "rebase", "--quiet", "origin/main", check=False)
            if rb.returncode != 0:
                run(repo_dir, "rebase", "--abort", check=False)
                return False, "push skipped: local and remote diverged and the rebase conflicted"
        r = run(repo_dir, "push", check=False)
    except Exception as exc:  # noqa: BLE001 — git missing, network down, timeout
        return False, f"{type(exc).__name__}: {exc}"[:500]
    if getattr(r, "returncode", 0) != 0:
        return False, str(getattr(r, "stderr", "") or "").strip()[:500]
    if gate is not None:
        gate.clear_blocked()
    return True, ""


def unpushed_count(repo_dir: str | Path, run=git) -> int:
    """Commits ahead of the upstream branch; 0 on any error (no upstream, no git)."""
    try:
        r = run(repo_dir, "rev-list", "--count", "@{u}..HEAD", check=False)
        return int(str(r.stdout).strip() or 0) if getattr(r, "returncode", 0) == 0 else 0
    except Exception:  # noqa: BLE001
        return 0


def head_sha(repo_dir: str | Path, ref: str = "HEAD", run=git) -> str:
    """Full sha of ``ref`` in the repo, or "" on any error (no git, unknown ref)."""
    try:
        r = run(repo_dir, "rev-parse", ref, check=False)
        return str(r.stdout).strip() if getattr(r, "returncode", 0) == 0 else ""
    except Exception:  # noqa: BLE001
        return ""


def running_sha(env: dict[str, str] | None = None) -> str:
    """The commit this image was built from (``GIT_SHA``, set by the Dockerfile), or ""."""
    return (os.environ if env is None else env).get("GIT_SHA", "").strip()


def commit_all(repo_dir: str | Path, message: str, push: bool = True, run=git,
               on_push_failed: Callable[[str], None] | None = None, gate: PushGate | None = None) -> str | None:
    """Stage everything, commit as Chris, optionally push through the gate. Returns the hash or None if clean.

    A push failure is not fatal: the commit stays local, ``on_push_failed(stderr)`` is called.
    """
    run(repo_dir, "add", "-A")
    if not has_changes(repo_dir, run):
        return None
    run(repo_dir, "commit", "-m", message)
    sha = run(repo_dir, "rev-parse", "HEAD").stdout.strip()
    if push:
        ok, err = push_repo(repo_dir, run, gate)
        if not ok and on_push_failed is not None:
            on_push_failed(err)
    return sha
