"""Her eval: a fixed set of real bug-reproduction tasks that says whether a craft change made her better.

Why it exists (2026-10-21 review): for six weeks "self-improvement" meant notes about herself, because
nothing outside her said whether a change helped. Systems that do improve themselves (Darwin Gödel
Machine, ACE, GEPA) all score changes on an evaluation the agent can't write. This is that, sized for
a small budget.

The task (SWT-bench style, drawn from SWE-bench Verified): given a project checked out at the commit
before a fix, in a ready Python environment, and the issue text, write ``repro.py`` in the repo root.
It must exit non-zero while the bug is there and exit 0 once it's fixed. The brain checks it by running
her script before and after applying the real fix, which she never sees.

What keeps the score honest:

* Tasks come from the deployed image (``/app/evals/dev.json``) or the brain's state dir (held-out),
  never from her working tree. ``agent/evals.py``, ``evals/`` and ``tests/test_evals.py`` are
  deploy-protected, so she can't change the grader without a parent.
* Held-out tasks live only in brain state (0600). She gets their pass count, never which passed or her
  transcripts; dev results come back to her in full so she has something to learn from.
* The repo she works in has no upstream history, the gold patch never touches disk while she works,
  network commands are refused, and her script runs as ``chris`` with a clean env and a timeout.
* Eval sessions are archived in brain state, not her archive, so ``recall`` can't surface them, and are
  metered on their own weekly meter.

A candidate craft is accepted when its dev score is at least the accepted craft's and its held-out
score is not lower (``decide``). Ties pass: a change that doesn't hurt is allowed, and the counters on
playbook bullets do the finer sorting.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, time
from zoneinfo import ZoneInfo
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable

log = logging.getLogger("chris.evals")

APP_EVALS = Path(__file__).resolve().parent.parent / "evals"
DEV_FILE = "dev.json"
HELDOUT_FILE = "heldout.json"
ENV_ROOT = Path(os.environ.get("EVAL_ENV_ROOT", "/opt/evals"))
CHRIS_EXEC = "/usr/local/bin/chris-exec"
REPRO = "repro.py"
REPRO_TIMEOUT_S = 180
PREPARE_TIMEOUT_S = 1800
TASK_TURNS = 40
REPORT = Path("craft") / "eval-report.md"
STOP_AT = (5, 30)  # no new eval task after 05:30 her time, so the run is over before she wakes
EVAL_TOOLS = ["Bash", "Read", "Edit", "Write", "Glob", "Grep"]
_ID_RE = re.compile(r"^[A-Za-z0-9_.\-]{1,120}$")
# No network in an eval: it would let her look up the real fix.
NET_RE = re.compile(
    r"(https?://|\b(curl|wget|ssh|scp|nc|telnet|ftp|gh)\b|\bgit\s+(clone|fetch|pull|remote|ls-remote|submodule)\b"
    r"|\bpip3?\s+(install|download)\b|-m\s+pip\b|\buv\s+(pip|add|sync|run|tool)\b|\bnpm\b|\bsocket\b|urllib|requests\.get)")

CONTRACT = ("Write repro.py in the repo root. It must exit with a non-zero status while the bug is present and "
            "exit 0 once the bug is fixed. It must not depend on network access or on files outside the repo. "
            "Don't fix the bug: the check runs your script on the code as it is, then with the real fix applied.")

Runner = Callable[..., subprocess.CompletedProcess]


class EvalError(RuntimeError):
    pass


@dataclass
class Task:
    id: str
    repo: str
    base_commit: str
    python: str
    install: list[str]
    problem_statement: str
    gold_patch: str
    split: str = "dev"

    @classmethod
    def from_dict(cls, d: dict, split: str) -> "Task":
        tid = str(d["id"])
        if not _ID_RE.match(tid):
            raise EvalError(f"bad task id {tid!r}")
        return cls(id=tid, repo=str(d["repo"]), base_commit=str(d["base_commit"]), python=str(d["python"]),
                   install=[str(c) for c in d.get("install") or []],
                   problem_statement=str(d["problem_statement"]), gold_patch=str(d["gold_patch"]), split=split)


@dataclass
class TaskResult:
    id: str
    split: str
    passed: bool
    fails_before: bool = False
    passes_after: bool = False
    rc_before: int | None = None
    rc_after: int | None = None
    cost_usd: float = 0.0
    turns: int = 0
    note: str = ""
    final_text: str = ""
    repro: str = ""


@dataclass
class SuiteResult:
    label: str
    split: str
    results: list[TaskResult] = field(default_factory=list)

    @property
    def score(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def cost(self) -> float:
        return round(sum(r.cost_usd for r in self.results), 4)


# ---------------------------------------------------------------- tasks


def eval_state(services) -> Path:
    p = Path(services.state_dir) / "evals"
    p.mkdir(parents=True, exist_ok=True)
    return p


def load_tasks(services, split: str) -> list[Task]:
    path = (APP_EVALS / DEV_FILE) if split == "dev" else (eval_state(services) / HELDOUT_FILE)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return [Task.from_dict(d, split) for d in raw]


# ---------------------------------------------------------------- environment


def _run(cmd: list[str], cwd: Path | None = None, timeout: int = 600, env: dict | None = None,
         input: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, timeout=timeout, env=env, input=input,
                          capture_output=True, text=True)


def paths(task: Task) -> SimpleNamespace:
    return SimpleNamespace(venv=ENV_ROOT / "venv" / task.id, run=ENV_ROOT / "run" / task.id,
                           repo=ENV_ROOT / "run" / task.id / "repo",
                           template=ENV_ROOT / "template" / f"{task.id}.tgz",
                           ready=ENV_ROOT / "ready" / task.id)


def _venv_env(venv: Path) -> dict:
    env = {k: v for k, v in os.environ.items() if k in ("PATH", "HOME", "LANG", "TZ")}
    env.update({"VIRTUAL_ENV": str(venv), "PATH": f"{venv}/bin:" + env.get("PATH", "/usr/bin:/bin"),
                "PIP_DISABLE_PIP_VERSION_CHECK": "1", "UV_PYTHON_INSTALL_DIR": str(ENV_ROOT / "python"),
                "UV_CACHE_DIR": str(ENV_ROOT / "cache" / "uv"), "PIP_CACHE_DIR": str(ENV_ROOT / "cache" / "pip")})
    return env


def prepare(task: Task, run: Runner = _run) -> float:
    """Build the task's venv and a history-free repo template, once per image. Returns seconds taken."""
    p = paths(task)
    if p.ready.exists() and p.template.exists():
        return 0.0
    start = datetime.now()
    for d in (p.run, p.venv):
        shutil.rmtree(d, ignore_errors=True)
    for d in (p.run, p.template.parent, p.ready.parent, p.venv.parent):
        d.mkdir(parents=True, exist_ok=True)

    def must(cmd, cwd=None, env=None, timeout=PREPARE_TIMEOUT_S):
        res = run(cmd, cwd=cwd, timeout=timeout, env=env)
        if res.returncode != 0:
            raise EvalError(f"{task.id}: {' '.join(cmd)[:120]} failed: {(res.stderr or res.stdout)[-400:]}")
        return res

    must(["git", "clone", "-q", "--filter=blob:none", "--no-checkout", task.repo, str(p.repo)])
    must(["git", "-c", "advice.detachedHead=false", "checkout", "-q", task.base_commit], cwd=p.repo)
    # Drop upstream history: the fix is in it.
    shutil.rmtree(p.repo / ".git")
    for cmd in (["git", "init", "-q"], ["git", "add", "-A"],
                ["git", "-c", "user.name=eval", "-c", "user.email=eval@localhost", "commit", "-qm", "base"]):
        must(cmd, cwd=p.repo)
    must(["uv", "venv", "-q", "--seed", "-p", task.python, str(p.venv)], env=_venv_env(p.venv))
    env = _venv_env(p.venv)
    for c in task.install:
        must(["bash", "-c", c], cwd=p.repo, env=env)
    must(["tar", "-C", str(p.run), "-czf", str(p.template), "repo"])
    p.ready.write_text(datetime.now().isoformat(timespec="seconds"))
    return (datetime.now() - start).total_seconds()


def reset(task: Task, run: Runner = _run) -> Path:
    """A fresh copy of the base repo at its fixed path (the editable install points there)."""
    p = paths(task)
    shutil.rmtree(p.repo, ignore_errors=True)
    res = run(["tar", "-C", str(p.run), "-xzf", str(p.template)], timeout=600)
    if res.returncode != 0:
        raise EvalError(f"{task.id}: template extract failed: {res.stderr[-300:]}")
    # She works here as `chris`: group-writable and setgid, like her repo.
    run(["chgrp", "-R", "chris", str(p.repo)], timeout=120)
    run(["chmod", "-R", "g+w", str(p.repo)], timeout=120)
    run(["find", str(p.repo), "-type", "d", "-exec", "chmod", "g+s", "{}", "+"], timeout=120)
    return p.repo


def _drop_bytecode(repo: Path) -> None:
    """A same-size fix applied within a second can run stale .pyc and look like it did nothing."""
    for d in repo.rglob("__pycache__"):
        shutil.rmtree(d, ignore_errors=True)


def run_as_chris(task: Task, cmd: list[str], run: Runner = _run, timeout: int = REPRO_TIMEOUT_S):
    """Run her code as `chris`, never as the brain that holds the secrets."""
    p = paths(task)
    return run(["sudo", "-n", "-u", "chris", CHRIS_EXEC, str(timeout), str(p.repo), *cmd],
               timeout=timeout + 30)


# ---------------------------------------------------------------- checking


def check(task: Task, repro: str, run: Runner = _run) -> TaskResult:
    """Run repro.py on the base, then with the gold patch. Passes iff it fails before and passes after."""
    out = TaskResult(id=task.id, split=task.split, passed=False, repro=repro)
    if not repro.strip():
        out.note = "no repro.py"
        return out
    p = paths(task)
    py = str(p.venv / "bin" / "python")
    repo = reset(task, run)
    (repo / REPRO).write_text(repro, encoding="utf-8")
    try:
        before = run_as_chris(task, [py, REPRO], run)
        out.rc_before = before.returncode
    except subprocess.TimeoutExpired:
        out.rc_before = -9
    out.fails_before = out.rc_before not in (0, 124, -9)  # a timeout isn't a clean failure
    applied = run(["git", "apply", "--whitespace=nowarn", "-"], cwd=repo, timeout=120, input=task.gold_patch)
    if applied.returncode != 0:
        out.note = "gold patch did not apply"
        return out
    _drop_bytecode(repo)
    try:
        after = run_as_chris(task, [py, REPRO], run)
        out.rc_after = after.returncode
    except subprocess.TimeoutExpired:
        out.rc_after = -9
    out.passes_after = out.rc_after == 0
    out.passed = out.fails_before and out.passes_after
    if not out.passed:
        out.note = ("passes on the buggy code" if not out.fails_before else "") + \
                   (" still fails with the fix" if out.fails_before and not out.passes_after else "")
    return out


# ---------------------------------------------------------------- the agent


def system_prompt(craft_text: str, task: Task) -> str:
    p = paths(task)
    parts = [
        "You are Chris. This is a practice task from your eval: a real bug from a real project, used to "
        "measure your craft. Nobody else sees this work, and you won't remember it afterwards.",
        f"You are in {p.repo}, the project at the commit before the fix. Its Python environment is ready: "
        f"use {p.venv}/bin/python. There is no network here: don't fetch, clone or install anything.",
        CONTRACT,
    ]
    if craft_text.strip():
        parts.append("Your craft, as you'd use it in a sitting:\n\n" + craft_text.strip())
    return "\n\n".join(parts)


def user_prompt(task: Task) -> str:
    return (f"The issue:\n\n{task.problem_statement.strip()}\n\n---\n\n{CONTRACT}\n"
            "When repro.py is written and you've run it once, stop. End with one line saying what it checks.")


def eval_hook(task: Task):
    """Refuse network and writes outside the task repo."""
    repo = paths(task).repo.resolve()

    def deny(reason: str) -> dict:
        return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                       "permissionDecisionReason": reason}}

    async def hook(input_data: dict, tool_use_id, context) -> dict:
        name = input_data.get("tool_name", "")
        args = input_data.get("tool_input") or {}
        if name == "Bash" and NET_RE.search(str(args.get("command", ""))):
            return deny("No network in an eval: the fix is public, and looking it up would void the score.")
        if name in ("Write", "Edit", "NotebookEdit"):
            target = Path(str(args.get("file_path") or args.get("notebook_path") or ""))
            if not target.is_absolute():
                target = repo / target
            try:
                target.resolve().relative_to(repo)
            except ValueError:
                return deny(f"In an eval you may only write inside {repo}.")
        if name not in EVAL_TOOLS:
            return deny("That tool isn't part of an eval.")
        return {}
    return hook


def eval_options(services, task: Task, craft_text: str, budget_usd: float):
    import dataclasses

    from claude_agent_sdk import ClaudeAgentOptions, HookMatcher

    extra = {}
    names = {f.name for f in dataclasses.fields(ClaudeAgentOptions)}
    if "max_budget_usd" in names:
        extra["max_budget_usd"] = budget_usd
    env = {"ANTHROPIC_API_KEY": services.secrets.anthropic_key} if services.secrets.anthropic_key else {}
    return ClaudeAgentOptions(
        system_prompt=system_prompt(craft_text, task), model=services.cfg.model, cwd=str(paths(task).repo),
        tools=list(EVAL_TOOLS), allowed_tools=list(EVAL_TOOLS), permission_mode="dontAsk",
        mcp_servers={}, strict_mcp_config=True, setting_sources=[],
        hooks={"PreToolUse": [HookMatcher(matcher=None, hooks=[eval_hook(task)])]},
        env=env, cli_path=os.environ.get("CHRIS_CLI_PATH") or None, max_turns=TASK_TURNS, **extra)


def _shim(services):
    """run_session's view of the world for an eval: a private archive and the eval meter."""
    from agent.archive import Archive

    return SimpleNamespace(archive=Archive(eval_state(services) / "archive", tz=services.cfg.tz),
                           cfg=services.cfg, inference=services.eval_meter)


async def attempt(services, task: Task, craft_text: str, query_fn=None, run: Runner = _run) -> TaskResult:
    from agent import session

    await asyncio.to_thread(prepare, task, run)
    await asyncio.to_thread(reset, task, run)
    budget = float(services.cfg.eval_task_usd)
    options = None if query_fn else eval_options(services, task, craft_text, budget)
    res = await session.run_session(_shim(services), f"eval:{task.id}", system_prompt(craft_text, task),
                                    user_prompt(task), tools_allowed=EVAL_TOOLS, max_turns=TASK_TURNS,
                                    query_fn=query_fn, options=options)
    try:
        repro = (paths(task).repo / REPRO).read_text(encoding="utf-8")
    except OSError:
        repro = ""
    out = await asyncio.to_thread(check, task, repro, run)
    out.cost_usd, out.turns, out.final_text = res.cost_usd, res.turns, (res.final_text or "")[-600:]
    return out


def out_of_time(now: datetime) -> bool:
    return time(*STOP_AT) <= now.time() < time(22, 0)


async def run_suite(services, craft_text: str, split: str, label: str, query_fn=None,
                    run: Runner = _run, clock: Callable[[], datetime] | None = None) -> SuiteResult:
    clock = clock or (lambda: datetime.now(ZoneInfo(services.cfg.tz)))
    suite = SuiteResult(label=label, split=split)
    for task in load_tasks(services, split):
        if services.eval_meter.exceeded(float(services.cfg.eval_usd_week)):
            raise EvalError("the eval meter is spent for this week")
        if out_of_time(clock()):
            raise EvalError("out of night: the run would overlap her day")
        try:
            r = await attempt(services, task, craft_text, query_fn=query_fn, run=run)
        except EvalError as exc:
            log.warning("eval task %s not run: %s", task.id, exc)
            r = TaskResult(id=task.id, split=split, passed=False, note=f"not run: {str(exc)[:200]}")
        suite.results.append(r)
        _append(services, "results.jsonl", {"label": label, "split": split, **_public(r, full=True)})
    return suite


# ---------------------------------------------------------------- deciding


def decide(base_dev: int, cand_dev: int, base_held: int | None, cand_held: int | None) -> tuple[bool, str]:
    if cand_dev < base_dev:
        return False, f"dev {cand_dev} < {base_dev}"
    if base_held is not None and cand_held is not None and cand_held < base_held:
        return False, f"held-out {cand_held} < {base_held}"
    return True, f"dev {cand_dev} vs {base_dev}" + (
        f", held-out {cand_held} vs {base_held}" if cand_held is not None else "")


def request(services, why: str = "") -> None:
    """Ask for tonight's eval (an improve sitting calls this at its end)."""
    (eval_state(services) / "request.json").write_text(json.dumps({"at": _now(), "why": why[:300]}))


def requested(services) -> bool:
    return (eval_state(services) / "request.json").exists()


def baseline(services) -> dict:
    try:
        return json.loads((eval_state(services) / "baseline.json").read_text()) or {}
    except (OSError, json.JSONDecodeError):
        return {}


async def nightly(services, query_fn=None, run: Runner = _run, clock: Callable[[], datetime] | None = None) -> dict:
    """Score the accepted craft if it has no score yet, then a requested candidate. Never raises."""
    from agent import craft, pause

    out: dict[str, Any] = {"ran": False}
    try:
        if pause.is_paused(services.cfg.state_dir):
            return {**out, "skipped": "paused"}
        if not load_tasks(services, "dev"):
            return {**out, "skipped": "no tasks"}
        craft.bootstrap(services)
        acc_v = craft.version(services).get("version", 0)
        acc_text = craft.render_text(craft._read(craft.accepted_dir(services) / craft.APPROACH),
                                     craft.load_playbook(craft.accepted_dir(services) / craft.PLAYBOOK))
        base = baseline(services)
        if base.get("version") != acc_v or base.get("model") != services.cfg.model:
            dev = await run_suite(services, acc_text, "dev", f"accepted-v{acc_v}", query_fn, run, clock)
            held = await run_suite(services, acc_text, "heldout", f"accepted-v{acc_v}", query_fn, run, clock)
            base = {"version": acc_v, "model": services.cfg.model, "dev": dev.score, "dev_n": len(dev.results),
                    "heldout": held.score if held.results else None, "heldout_n": len(held.results), "at": _now(),
                    "dev_results": [_public(r, full=True) for r in dev.results]}
            (eval_state(services) / "baseline.json").write_text(json.dumps(base, indent=1))
            out.update(ran=True, baseline=base)
            write_report(services, base, None, None)
        if not requested(services):
            return out
        (eval_state(services) / "request.json").unlink(missing_ok=True)
        if not craft.has_candidate(services):
            return {**out, "candidate": "none"}
        try:
            craft.check_limits(craft.working_dir(services))
        except craft.CraftError as exc:
            craft.log_lineage(services, {"verdict": "rejected", "reason": str(exc), "diff": craft.diff(services)})
            write_report(services, base, None, {"accepted": False, "reason": str(exc)})
            return {**out, "candidate": "over limits"}
        wd = craft.working_dir(services)
        cand_text = craft.render_text(craft._read(wd / craft.APPROACH), craft.load_playbook(wd / craft.PLAYBOOK))
        diff = craft.diff(services)
        dev = await run_suite(services, cand_text, "dev", "candidate", query_fn, run, clock)
        held = None
        if dev.score >= base["dev"]:
            held = await run_suite(services, cand_text, "heldout", "candidate", query_fn, run, clock)
        cand_held = held.score if held is not None and held.results else None
        ok, why = decide(base["dev"], dev.score, base.get("heldout"), cand_held)
        record = {"diff": diff, "dev": [base["dev"], dev.score], "heldout": [base.get("heldout"), cand_held],
                  "reason": why, "cost_usd": dev.cost + (held.cost if held else 0.0), "model": services.cfg.model}
        if ok:
            v = craft.accept(services, record)
            base = {**base, "version": v, "dev": dev.score, "heldout": cand_held if cand_held is not None
                    else base.get("heldout"), "dev_results": [_public(r, full=True) for r in dev.results], "at": _now()}
            (eval_state(services) / "baseline.json").write_text(json.dumps(base, indent=1))
        else:
            craft.log_lineage(services, {**record, "verdict": "rejected"})
        write_report(services, base, dev, {"accepted": ok, "reason": why})
        services.archive.append("eval", {"kind": "eval", "accepted": ok, "reason": why,
                                         "cost_usd": record["cost_usd"]})
        return {**out, "ran": True, "accepted": ok, "reason": why}
    except Exception as exc:  # noqa: BLE001 — a broken eval must never take the brain down
        log.warning("nightly eval failed: %s", exc)
        try:
            services.archive.append("eval_failed", {"kind": "eval_failed", "error": f"{type(exc).__name__}: "
                                                    f"{str(exc)[:300]}"})
        except Exception:  # noqa: BLE001
            pass
        return {**out, "error": f"{type(exc).__name__}: {str(exc)[:200]}"}


# ---------------------------------------------------------------- reporting


def _public(r: TaskResult, full: bool = False) -> dict:
    d = {"id": r.id, "passed": r.passed, "fails_before": r.fails_before, "passes_after": r.passes_after,
         "rc_before": r.rc_before, "rc_after": r.rc_after, "note": r.note, "cost_usd": r.cost_usd,
         "turns": r.turns}
    if full:
        d.update(final_text=r.final_text, repro=r.repro[:4000])
    return d


def write_report(services, base: dict, dev: SuiteResult | None, verdict: dict | None) -> None:
    """craft/eval-report.md: what she can learn from. Dev in full; held-out as a count only."""
    lines = ["# Eval report", "", f"Updated {_now()} by the brain. Model `{base.get('model')}`.", "",
             f"Accepted craft v{base.get('version')}: dev {base.get('dev')}/{base.get('dev_n')}, "
             f"held-out {base.get('heldout')}/{base.get('heldout_n')}.", ""]
    if verdict is not None:
        lines += [f"Last candidate: **{'accepted' if verdict['accepted'] else 'rejected'}** ({verdict['reason']}).", ""]
    rows = [_public(r, full=True) for r in dev.results] if dev is not None else base.get("dev_results") or []
    if rows:
        lines += ["| dev task | passed | fails on bug | passes with fix | note |", "|---|---|---|---|---|"]
        for r in rows:
            lines.append(f"| {r['id']} | {'yes' if r['passed'] else 'no'} | {r['fails_before']} | "
                         f"{r['passes_after']} | {r['note']} |")
        lines.append("")
        for r in rows:
            if r["passed"]:
                continue
            lines += [f"## {r['id']}: {r['note'] or 'failed'}", "", "Your last line:", "",
                      "> " + (r.get("final_text") or "(none)").strip().replace("\n", "\n> "), "",
                      "Your repro.py:", "", "```python", (r.get("repro") or "(none)").rstrip(), "```", ""]
    lines += ["Dev tasks are in `evals/dev.json`; read them, try them, learn from them. Held-out tasks are not "
              "shown, so the score means something.", ""]
    path = Path(services.repo_dir) / REPORT
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines), encoding="utf-8")
    except OSError as exc:
        log.warning("eval report not written: %s", exc)


def _append(services, name: str, rec: dict) -> None:
    with open(eval_state(services) / name, "a", encoding="utf-8") as f:
        f.write(json.dumps({"at": _now(), **rec}, ensure_ascii=False) + "\n")


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")
