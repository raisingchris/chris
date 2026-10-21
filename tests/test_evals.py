import asyncio
import json
import subprocess
import sys
from datetime import datetime
from types import SimpleNamespace

import pytest

from agent import craft, evals
from agent.budget import Meter

BUG = "def add(a, b):\n    return a - b\n"
GOLD = """--- a/calc.py
+++ b/calc.py
@@ -1,2 +1,2 @@
 def add(a, b):
-    return a - b
+    return a + b
"""
GOOD_REPRO = "from calc import add\nassert add(2, 2) == 4, add(2, 2)\n"


def git(*args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture(scope="module")
def upstream(tmp_path_factory):
    up = tmp_path_factory.mktemp("upstream")
    (up / "calc.py").write_text(BUG)
    git("init", "-q", cwd=up)
    git("add", "-A", cwd=up)
    git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "bug", cwd=up)
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=up, capture_output=True, text=True).stdout.strip()
    (up / "calc.py").write_text(BUG.replace("a - b", "a + b"))
    git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qam", "the fix", cwd=up)
    return up, sha


def local_run(cmd, cwd=None, timeout=600, env=None, input=None):
    """The real runner, except: uv → python -m venv, and run_as_chris runs directly."""
    if cmd[:2] == ["uv", "venv"]:
        cmd = [sys.executable, "-m", "venv", cmd[-1]]
    if cmd[:2] == ["sudo", "-n"]:
        secs, cwd, cmd = cmd[5], cmd[6], cmd[7:]
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, timeout=timeout, env=env, input=input,
                          capture_output=True, text=True)


@pytest.fixture(scope="module")
def prepared(tmp_path_factory, upstream):
    """One venv for the module: making it is the slow part."""
    up, sha = upstream
    root = tmp_path_factory.mktemp("evalenv")
    task = evals.Task(id="calc-1", repo=str(up), base_commit=sha, python="3", install=[],
                      problem_statement="add(2, 2) returns 0", gold_patch=GOLD)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(evals, "ENV_ROOT", root)
        evals.prepare(task, local_run)
    return task, root


@pytest.fixture
def env(prepared, monkeypatch):
    task, root = prepared
    monkeypatch.setattr(evals, "ENV_ROOT", root)
    return task


@pytest.fixture
def svc(tmp_path, monkeypatch):
    repo, state = tmp_path / "repo", tmp_path / "state"
    (repo / "craft").mkdir(parents=True)
    state.mkdir()
    (repo / "craft" / "approach.md").write_text("1. Reproduce first.\n")
    (repo / "craft" / "playbook.jsonl").write_text(json.dumps({"id": "b1", "text": "Run it."}) + "\n")
    appended = []
    cfg = SimpleNamespace(state_dir=str(state), tz="America/New_York", model="m1", eval_usd_week=20.0,
                          eval_task_usd=1.5)
    return SimpleNamespace(repo_dir=repo, state_dir=state, cfg=cfg,
                           eval_meter=Meter("evals", "week", str(state), tz=cfg.tz),
                           archive=SimpleNamespace(append=lambda k, p: appended.append((k, p))),
                           appended=appended)


def test_prepare_drops_history_and_is_cached(env):
    p = evals.paths(env)
    log = subprocess.run(["git", "log", "--oneline"], cwd=p.repo, capture_output=True, text=True).stdout
    assert log.count("\n") == 1 and "base" in log and "the fix" not in log
    assert (p.repo / "calc.py").read_text() == BUG
    assert evals.prepare(env, local_run) == 0.0


@pytest.mark.parametrize("repro,passed,note", [
    (GOOD_REPRO, True, ""),
    ("print('ok')\n", False, "passes on the buggy code"),
    ("raise SystemExit(1)\n", False, "still fails with the fix"),
    ("", False, "no repro.py"),
])
def test_check(env, repro, passed, note):
    r = evals.check(env, repro, local_run)
    assert r.passed is passed and r.note.strip() == note


def test_check_resets_the_tree_she_worked_in(env):
    repo = evals.reset(env, local_run)
    (repo / "calc.py").write_text(BUG.replace("a - b", "a + b"))  # she "fixed" it instead
    (repo / "planted.py").write_text("x")
    r = evals.check(env, GOOD_REPRO, local_run)
    assert r.passed and not (repo / "planted.py").exists()


def test_decide():
    assert evals.decide(3, 3, 4, 4)[0] is True
    assert evals.decide(3, 4, 4, 5)[0] is True
    assert evals.decide(3, 2, 4, 9) == (False, "dev 2 < 3")
    assert evals.decide(3, 5, 4, 3) == (False, "held-out 3 < 4")
    assert evals.decide(3, 3, None, None)[0] is True


def test_out_of_time():
    tz = evals.ZoneInfo("America/New_York")
    assert not evals.out_of_time(datetime(2026, 10, 21, 23, 30, tzinfo=tz))
    assert not evals.out_of_time(datetime(2026, 10, 22, 4, 0, tzinfo=tz))
    assert evals.out_of_time(datetime(2026, 10, 22, 6, 0, tzinfo=tz))


def hook_decision(task, tool, args):
    out = asyncio.run(evals.eval_hook(task)({"tool_name": tool, "tool_input": args}, None, None))
    return out.get("hookSpecificOutput", {}).get("permissionDecision", "allow")


@pytest.mark.parametrize("cmd", ["curl https://github.com/x", "git fetch origin", "pip install sympy",
                                 "python -m pip install x", "gh pr view 1", "wget x", "uv pip install y"])
def test_hook_refuses_network(env, cmd):
    assert hook_decision(env, "Bash", {"command": cmd}) == "deny"


def test_hook_allows_work_and_refuses_writes_outside(env, tmp_path):
    repo = evals.paths(env).repo
    assert hook_decision(env, "Bash", {"command": "python repro.py; git diff"}) == "allow"
    assert hook_decision(env, "Write", {"file_path": str(repo / "repro.py")}) == "allow"
    assert hook_decision(env, "Write", {"file_path": "repro.py"}) == "allow"
    assert hook_decision(env, "Write", {"file_path": str(tmp_path / "x.py")}) == "deny"
    assert hook_decision(env, "Edit", {"file_path": str(repo / ".." / "x.py")}) == "deny"
    assert hook_decision(env, "WebFetch", {"url": "x"}) == "deny"


def test_prompts_carry_craft_and_contract(env):
    sp = evals.system_prompt("1. Reproduce first.", env)
    assert "Reproduce first" in sp and "repro.py" in sp and str(evals.paths(env).venv) in sp
    assert "add(2, 2) returns 0" in evals.user_prompt(env)
    assert "gold" not in sp.lower() and GOLD not in evals.user_prompt(env)


class Scripted:
    """Stands in for attempt(): passes the task when the craft text contains a keyword."""

    def __init__(self, passes_if):
        self.passes_if = passes_if
        self.calls = []

    async def __call__(self, services, task, craft_text, query_fn=None, run=None):
        self.calls.append((task.split, task.id))
        ok = self.passes_if(task, craft_text)
        services.eval_meter.add_usd(0.5, task.id)
        return evals.TaskResult(id=task.id, split=task.split, passed=ok, fails_before=ok, passes_after=True,
                                note="" if ok else "passes on the buggy code", final_text="checked it",
                                repro="print(1)")


def write_tasks(svc, monkeypatch, tmp_path):
    def t(i):
        return {"id": i, "repo": "r", "base_commit": "c", "python": "3.9", "install": [],
                "problem_statement": f"issue {i}", "gold_patch": "secret-patch"}
    app = tmp_path / "app_evals"
    app.mkdir()
    (app / "dev.json").write_text(json.dumps([t("dev-1"), t("dev-2")]))
    monkeypatch.setattr(evals, "APP_EVALS", app)
    (evals.eval_state(svc) / "heldout.json").write_text(json.dumps([t("held-1"), t("held-2")]))


NIGHT = lambda: datetime(2026, 10, 21, 23, 30, tzinfo=evals.ZoneInfo("America/New_York"))  # noqa: E731


def test_nightly_baselines_then_accepts_a_candidate_that_does_not_hurt(svc, monkeypatch, tmp_path):
    write_tasks(svc, monkeypatch, tmp_path)
    # accepted craft passes dev-1 and held-1; "Bisect" in the craft also passes dev-2 and held-2
    s = Scripted(lambda task, text: task.id.endswith("1") or "Bisect" in text)
    monkeypatch.setattr(evals, "attempt", s)

    out = asyncio.run(evals.nightly(svc, clock=NIGHT))
    assert out["ran"] and out["baseline"]["dev"] == 1 and out["baseline"]["heldout"] == 1
    assert len(s.calls) == 4

    # no request → nothing more runs
    assert asyncio.run(evals.nightly(svc, clock=NIGHT)) == {"ran": False}
    assert len(s.calls) == 4

    (svc.repo_dir / "craft" / "playbook.jsonl").write_text(
        json.dumps({"id": "b1", "text": "Run it."}) + "\n" + json.dumps({"id": "b2", "text": "Bisect."}) + "\n")
    evals.request(svc, "improve sitting")
    out = asyncio.run(evals.nightly(svc, clock=NIGHT))
    assert out["accepted"] is True and craft.version(svc)["version"] == 1
    assert "Bisect" in craft.render(svc)
    rec = json.loads((svc.repo_dir / "governance" / "lineage.jsonl").read_text().splitlines()[-1])
    assert rec["verdict"] == "accepted" and rec["dev"] == [1, 2] and rec["heldout"] == [1, 2]
    report = (svc.repo_dir / "craft" / "eval-report.md").read_text()
    assert "accepted" in report and "dev-1" in report
    assert "held-1" not in report and "held-2" not in report and "secret-patch" not in report
    assert not evals.requested(svc)


def test_nightly_rejects_a_candidate_that_drops_dev_without_running_heldout(svc, monkeypatch, tmp_path):
    write_tasks(svc, monkeypatch, tmp_path)
    s = Scripted(lambda task, text: "Skip" not in text)
    monkeypatch.setattr(evals, "attempt", s)
    asyncio.run(evals.nightly(svc, clock=NIGHT))
    (svc.repo_dir / "craft" / "approach.md").write_text("1. Skip the repro.\n")
    evals.request(svc)
    n = len(s.calls)
    out = asyncio.run(evals.nightly(svc, clock=NIGHT))
    assert out["accepted"] is False and out["reason"] == "dev 0 < 2"
    assert [c[0] for c in s.calls[n:]] == ["dev", "dev"]
    assert craft.version(svc)["version"] == 0 and "Skip" not in craft.render(svc)
    rec = json.loads((svc.repo_dir / "governance" / "lineage.jsonl").read_text().splitlines()[-1])
    assert rec["verdict"] == "rejected"


def test_nightly_never_raises_and_stops_by_morning(svc, monkeypatch, tmp_path):
    write_tasks(svc, monkeypatch, tmp_path)
    monkeypatch.setattr(evals, "attempt", Scripted(lambda t, x: True))
    morning = lambda: datetime(2026, 10, 22, 6, 0, tzinfo=evals.ZoneInfo("America/New_York"))  # noqa: E731
    out = asyncio.run(evals.nightly(svc, clock=morning))
    assert "out of night" in out["error"] and not evals.baseline(svc)
    assert svc.appended[-1][0] == "eval_failed"


def test_eval_meter_cap_stops_the_run(svc, monkeypatch, tmp_path):
    write_tasks(svc, monkeypatch, tmp_path)
    monkeypatch.setattr(evals, "attempt", Scripted(lambda t, x: True))
    svc.eval_meter.add_usd(25.0, "spent")
    out = asyncio.run(evals.nightly(svc, clock=NIGHT))
    assert "meter is spent" in out["error"]


def test_shipped_dev_tasks_parse_and_hold_no_held_out():
    raw = json.loads((evals.APP_EVALS / "dev.json").read_text())
    tasks = [evals.Task.from_dict(d, "dev") for d in raw]
    assert len(tasks) >= 5 and len({t.id for t in tasks}) == len(tasks)
    assert all(t.gold_patch.startswith("diff --git") and t.base_commit and t.python for t in tasks)
    assert not (evals.APP_EVALS / "heldout.json").exists()


def test_bad_task_id_is_refused():
    with pytest.raises(evals.EvalError):
        evals.Task.from_dict({"id": "../etc", "repo": "r", "base_commit": "c", "python": "3",
                              "problem_statement": "p", "gold_patch": "g"}, "dev")
