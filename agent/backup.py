"""Nightly off-box backup of Chris's private state to a private git repo.

Copies ``archive_dir``, ``state_dir`` and the council minutes into a local
clone (``<state_dir>/../backup-repo``, under ``archive/``, ``state/`` and
``council_minutes/``), commits as Chris and pushes. Files are only ever added
or updated in the clone, never deleted, so the history is append-only.

Env (brain-only): ``BACKUP_GIT_URL`` — the ssh URL of a private repo — and
``BACKUP_DEPLOY_KEY`` — the private key text. Without both the backup is
skipped and archived as such. The key is written once to
``<state_dir>/../backup_key`` (mode 600) and handed to git only by path via
``GIT_SSH_COMMAND``; its text never reaches a command line, a log line or an
archive record — only error *types* and a scrubbed stderr excerpt do.

Every git call goes through an injectable runner (``run=``, as in
:mod:`agent.gitops`) built from :func:`agent.gitops.git_env`: a from-scratch
environment with hooks disabled on the command line.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Callable
from zoneinfo import ZoneInfo

from agent import gitops

log = logging.getLogger("chris.backup")

KEY_FILE = "backup_key"
REPO_DIR = "backup-repo"
BRANCH = "main"
GIT_TIMEOUT_S = 600
STDERR_EXCERPT = 300

Runner = Callable[..., subprocess.CompletedProcess]


def backup_dirs(cfg) -> list[Path]:
    """The three private directories, in a stable order: archive, state, council minutes."""
    state = Path(cfg.state_dir)
    minutes = Path(os.environ.get("COUNCIL_MINUTES_DIR") or state.parent / "council_minutes")
    return [Path(cfg.archive_dir), state, minutes]


def backup_paths(cfg) -> tuple[Path, Path]:
    """(key file, clone dir), both siblings of ``state_dir``."""
    base = Path(cfg.state_dir).parent
    return base / KEY_FILE, base / REPO_DIR


def ssh_command(key_path: Path) -> str:
    return f"ssh -i {key_path} -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"


def make_runner(key_path: Path) -> Runner:
    """A git runner in the style of :func:`agent.gitops.git`, keyed to the backup deploy key."""

    def run(repo_dir: str | Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        env = gitops.git_env(gitops.CHRIS)
        env["GIT_SSH_COMMAND"] = ssh_command(key_path)
        return subprocess.run(
            ["git", *gitops.GIT_FLAGS, *args], cwd=str(repo_dir), env=env,
            capture_output=True, text=True, check=check, timeout=GIT_TIMEOUT_S,
        )

    return run


def ensure_key(key_path: Path, key_text: str) -> bool:
    """Write the deploy key (mode 600) if it is not there yet. Returns True if written."""
    if key_path.exists():
        return False
    key_path.parent.mkdir(parents=True, exist_ok=True)
    text = key_text if key_text.endswith("\n") else key_text + "\n"
    fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(text)
    os.chmod(key_path, 0o600)
    return True


def _stderr(r) -> str:
    return str(getattr(r, "stderr", "") or "")


def clone_repo(repo: Path, url: str, run: Runner) -> str:
    """Clone into ``repo``; an empty remote becomes ``git init`` + ``remote add``. Returns "clone" or "init"."""
    repo.parent.mkdir(parents=True, exist_ok=True)
    r = run(repo.parent, "clone", url, str(repo), check=False)
    if getattr(r, "returncode", 0) == 0:
        return "clone"
    if "empty repository" not in _stderr(r).lower():
        raise subprocess.CalledProcessError(r.returncode, ["git", "clone"], r.stdout, r.stderr)
    shutil.rmtree(repo, ignore_errors=True)
    repo.mkdir(parents=True, exist_ok=True)
    run(repo, "init")
    run(repo, "symbolic-ref", "HEAD", f"refs/heads/{BRANCH}")
    run(repo, "remote", "add", "origin", url)
    return "init"


def ensure_repo(repo: Path, url: str, run: Runner) -> str:
    """Bring the clone up to date; a clone that will not pull is thrown away and cloned afresh."""
    if not (repo / ".git").is_dir():
        return clone_repo(repo, url, run)
    r = run(repo, "pull", "--rebase", check=False)
    if getattr(r, "returncode", 0) == 0:
        return "pull"
    log.warning("backup clone would not pull; re-cloning")
    shutil.rmtree(repo, ignore_errors=True)
    return "re" + clone_repo(repo, url, run)


def sync_dir(src: Path, dst: Path) -> int:
    """Copy new or changed files from ``src`` into ``dst`` (never deleting); returns the number copied."""
    if not src.is_dir():
        return 0
    copied = 0
    for path in sorted(src.rglob("*")):
        if not path.is_file():
            continue
        target = dst / path.relative_to(src)
        try:
            same = target.is_file() and target.stat().st_size == path.stat().st_size \
                and int(target.stat().st_mtime) >= int(path.stat().st_mtime)
        except OSError:
            same = False
        if same:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        copied += 1
    return copied


def sync_all(cfg, repo: Path) -> int:
    archive, state, minutes = backup_dirs(cfg)
    return (sync_dir(archive, repo / "archive") + sync_dir(state, repo / "state")
            + sync_dir(minutes, repo / "council_minutes"))


def scrub(text: str, key_path: Path, key_text: str) -> str:
    """Remove the key (and its path) from anything that might be stored."""
    text = text.replace(key_text.strip(), "<key>") if key_text.strip() else text
    return text.replace(str(key_path), "<key-path>")


def run_backup(services, env: dict[str, str] | None = None, run: Runner | None = None) -> dict:
    """Copy + commit + push; archives ``backup_skipped`` / ``backup_done`` / ``backup_failed``. Never raises."""
    e = os.environ if env is None else env
    cfg = services.cfg
    url = e.get("BACKUP_GIT_URL", "").strip()
    key_text = e.get("BACKUP_DEPLOY_KEY", "")
    if not url or not key_text.strip():
        missing = [k for k, v in (("BACKUP_GIT_URL", url), ("BACKUP_DEPLOY_KEY", key_text.strip())) if not v]
        log.info("backup skipped: %s not set", ", ".join(missing))
        payload = {"kind": "backup_skipped", "missing": missing}
        services.archive.append("backup", payload)
        return payload

    key_path, repo = backup_paths(cfg)
    try:
        ensure_key(key_path, key_text)
        if run is None:
            run = make_runner(key_path)
        ensure_repo(repo, url, run)
        files = sync_all(cfg, repo)
        run(repo, "add", "-A")
        if not gitops.has_changes(repo, run):
            payload = {"kind": "backup_done", "changed": False, "commit": None, "files": files}
        else:
            ts = datetime.now(ZoneInfo(cfg.tz)).isoformat(timespec="seconds")
            run(repo, "commit", "-m", f"backup {ts}")
            sha = str(run(repo, "rev-parse", "HEAD").stdout).strip()[:7]
            run(repo, "push", "-u", "origin", "HEAD")
            payload = {"kind": "backup_done", "changed": True, "commit": sha, "files": files}
    except Exception as exc:  # noqa: BLE001 — never let the key or its errors escape
        err = type(exc).__name__
        raw = _stderr(exc) if isinstance(exc, subprocess.CalledProcessError) else str(exc)
        log.warning("backup failed: %s", err)
        payload = {"kind": "backup_failed", "error": err,
                   "stderr": scrub(raw, key_path, key_text).strip()[:STDERR_EXCERPT]}
        services.archive.append("backup", payload)
        return payload
    log.info("backup done: changed=%s files=%d commit=%s", payload["changed"], files, payload["commit"])
    services.archive.append("backup", payload)
    return payload
