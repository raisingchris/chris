"""Self-deploy: Chris ships her own committed code, with a hard safety boundary.

She may deploy anything EXCEPT a protected set of safety-critical files — her
conscience (vows/constitution), the identity-safety code (redaction), the tool
guards, the deploy gate itself, and the tests that prove them. A change touching
any of those still needs a parent (a proposal, then the Deploy button on the
parent page).

``self_deploy`` is the guarded path the ``deploy`` tool calls. Every failure
returns ``{"ok": False, "reason": ..., "detail": ...}`` and it never raises.
The green happy path runs her whole test suite, then triggers the same GitHub
Actions workflow a parent's Deploy button uses.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable
from zoneinfo import ZoneInfo

from agent import gitops, pause

log = logging.getLogger("chris.deploy")

# The "armory locks": paths Chris may never deploy on her own. A path matches if
# it equals an entry, or (for a "…/" directory entry) starts with it.
PROTECTED_PATHS = (
    "soul/vows.md",
    "soul/constitution.md",
    ".github/workflows/",
    "agent/guards.py",
    "agent/deploy.py",
    "agent/redaction.py",
    "tests/test_guards.py",
    "tests/test_redaction.py",
    "tests/test_invariants.py",
)

STATE_FILE = "self_deploy.json"
CHANGELOG = Path("governance") / "changelog.md"
TEST_TIMEOUT_S = 600
MAX_LISTED_FILES = 8


def _read_json(path: Path, default):
    try:
        return json.loads(path.read_text() or "null") or default
    except (OSError, json.JSONDecodeError):
        return default


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1))


def is_protected(path: str) -> bool:
    """True when ``path`` is one of the armory-locked files (or under a locked dir)."""
    for entry in PROTECTED_PATHS:
        if entry.endswith("/"):
            if path.startswith(entry):
                return True
        elif path == entry:
            return True
    return False


def _diff_names(repo_dir, base_sha: str, run) -> list[str]:
    """The files changed between ``base_sha`` and HEAD, or [] on any error."""
    try:
        r = run(repo_dir, "diff", "--name-only", f"{base_sha}..HEAD", check=False)
    except Exception:  # noqa: BLE001 — git missing, bad sha
        return []
    if getattr(r, "returncode", 0) != 0:
        return []
    out = str(getattr(r, "stdout", "") or "")
    return [ln.strip() for ln in out.splitlines() if ln.strip()]


def changed_protected(repo_dir, base_sha: str, run: Callable = gitops.git) -> list[str]:
    """The protected files changed between ``base_sha`` and HEAD (``git diff --name-only``)."""
    return [p for p in _diff_names(repo_dir, base_sha, run) if is_protected(p)]


def run_tests(repo_dir, run: Callable = subprocess.run) -> tuple[bool, str]:
    """Run the whole suite in ``repo_dir`` with a subprocess; return (ok, last summary line).

    In production the brain image carries pytest (pyproject ``[dev]``); the tool
    runs from /app but tests live in /data/repo, so pytest runs with cwd=repo_dir.
    """
    try:
        proc = run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
            cwd=str(repo_dir), capture_output=True, text=True, timeout=TEST_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        return False, f"tests timed out after {TEST_TIMEOUT_S}s"
    except Exception as exc:  # noqa: BLE001 — python/pytest missing
        return False, f"could not run tests: {type(exc).__name__}: {exc}"
    out = (getattr(proc, "stdout", "") or "") + "\n" + (getattr(proc, "stderr", "") or "")
    last = next((ln.strip() for ln in reversed(out.splitlines()) if ln.strip()), "")
    return getattr(proc, "returncode", 1) == 0, last


def self_deploys_today(state_dir, now: datetime) -> int:
    """How many times Chris has self-deployed on ``now``'s day (her tz), from the state file."""
    rec = _read_json(Path(state_dir) / STATE_FILE, {})
    return int(rec.get("count", 0)) if rec.get("day") == now.strftime("%Y-%m-%d") else 0


def self_deploy(services, dispatch: Callable | None = None, run_tests_fn: Callable | None = None,
                git_run: Callable | None = None, now: Callable | None = None) -> dict:
    """Deploy Chris's current code if it's safe and green. Never raises.

    Steps, each failure returning ``{"ok": False, "reason": ..., "detail": ...}``:
    paused → protected files → running==HEAD → daily cap → tests → dispatch.
    """
    try:
        cfg = services.cfg
        repo = Path(cfg.repo_dir)
        state = Path(cfg.state_dir)
        tz = ZoneInfo(cfg.tz)
        now_fn = now or (lambda: datetime.now(tz))
        git = git_run or gitops.git

        # a. paused
        if pause.is_paused(state):
            return {"ok": False, "reason": "paused",
                    "detail": "You're paused; a parent must lift the pause before you can deploy."}

        # b. running code vs HEAD
        deployed_sha = gitops.running_sha()
        head = gitops.head_sha(repo, run=git)
        head7 = head[:7]
        if deployed_sha and head and deployed_sha == head:
            return {"ok": False, "reason": "nothing_to_deploy",
                    "detail": "running code already matches HEAD"}

        # c. protected files — these need a parent
        protected = changed_protected(repo, deployed_sha, run=git)
        if protected:
            return {"ok": False, "reason": "protected_files",
                    "detail": "You changed protected safety files: " + ", ".join(protected)
                    + ". These need a parent — file a proposal; a parent deploys with the button."}

        # d. daily cap
        day = now_fn().strftime("%Y-%m-%d")
        rec = _read_json(state / STATE_FILE, {})
        count = int(rec.get("count", 0)) if rec.get("day") == day else 0
        cap = cfg.self_deploy_per_day
        if count >= cap:
            return {"ok": False, "reason": "daily_cap",
                    "detail": f"You've already deployed yourself {count} times today; the cap is {cap} a day. "
                    "It resets tomorrow."}

        # e. tests
        ok, summary = (run_tests_fn or run_tests)(repo)
        if not ok:
            return {"ok": False, "reason": "tests_failed", "detail": summary}

        # f. dispatch the deploy
        token = os.environ.get("GITHUB_DEPLOY_TOKEN", "")
        if dispatch is None:
            if not token:
                return {"ok": False, "reason": "not_configured",
                        "detail": "GITHUB_DEPLOY_TOKEN isn't set; a parent must configure deploys."}
            from agent import server
            dispatch = server.dispatch_deploy
        try:
            dispatch(token)
        except Exception as exc:  # noqa: BLE001 — network / GitHub errors
            return {"ok": False, "reason": "dispatch_failed", "detail": f"{type(exc).__name__}: {exc}"}

        # Success. From here nothing may fail the (already-dispatched) deploy.
        changed = _diff_names(repo, deployed_sha, run=git)
        n = len(changed)
        _write_json(state / STATE_FILE, {"day": day, "count": count + 1})

        try:
            files = ", ".join(changed[:MAX_LISTED_FILES])
            line = f"- {day} — Chris deployed herself: {head7} ({n} files: {files})\n"
            changelog = repo / CHANGELOG
            changelog.parent.mkdir(parents=True, exist_ok=True)
            with open(changelog, "a", encoding="utf-8") as f:
                f.write(line)
            gitops.commit_all(repo, f"governance: self-deploy {head7}", push=True,
                              gate=gitops.PushGate.from_services(services))
        except Exception as exc:  # noqa: BLE001 — the deploy is already out; the record is a bonus
            log.warning("self-deploy changelog commit failed: %s", exc)

        try:
            services.archive.append("self_deploy", {"kind": "self_deploy", "sha": head7, "files": n})
        except Exception:  # noqa: BLE001
            pass
        try:
            from agent import wiring
            wiring.note_last_run(state, "last_deploy", tz=tz, sha=head7)
        except Exception:  # noqa: BLE001
            pass

        return {"ok": True, "sha": head7,
                "note": "deploying; ~2 min. Your new code is live when /health git_sha matches."}
    except Exception as exc:  # noqa: BLE001 — self_deploy must never raise
        log.warning("self_deploy failed unexpectedly: %s", exc)
        return {"ok": False, "reason": "error", "detail": f"{type(exc).__name__}: {exc}"}
