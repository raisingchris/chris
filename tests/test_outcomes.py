import json
from datetime import date, timedelta
from types import SimpleNamespace

from agent import craft, outcomes
from agent.loop import open_commitments


class Archive:
    def __init__(self, days=None):
        self.days = days or {}
        self.appended = []

    def read_day(self, d):
        return self.days.get(d, [])

    def append(self, k, p):
        self.appended.append((k, p))


class Analytics:
    def ga4_report(self, dims, metrics, start, end, limit=50, filters=None):
        return {"rows": [{"activeUsers": 4 if filters else 30}]}

    def gsc_query(self, start, end, dims=None, row_limit=50, filters=None):
        return {"rows": [{"query": "raising chris", "clicks": 9}, {"query": "list of autonomous ai agents",
                                                                    "clicks": 2}]}


class GitHub:
    def get(self, url, params=None, headers=None):
        q = params["q"]
        assert "is:merged" in q and "author:her" in q and "-user:her" in q and "-user:raisingchris" in q
        return SimpleNamespace(status_code=200, json=lambda: {"total_count": 1})


def mail(sender):
    return {"kind": "mail_in", "payload": {"data": {"from": sender}}}


def svc(tmp_path, days=None, analytics=None):
    cfg = SimpleNamespace(state_dir=str(tmp_path), tz="America/New_York", parent_handles=["parent-a", "parent-b"],
                          chris_email="chris@raisingchris.com", github_user="her")
    return SimpleNamespace(cfg=cfg, state_dir=tmp_path, repo_dir=tmp_path / "repo", archive=Archive(days),
                           analytics=analytics)


def test_compute_counts_users_of_any_kind_and_leaves_out_her_name_parents_and_robots(tmp_path):
    days = {"2026-11-20": [mail("Kei <kei@agents.example>"), mail("parent-a"), mail("noreply@github.com"),
                           mail("dmarc-reports@x.com"), mail("kei@agents.example")],
            "2026-11-21": [mail("A person <p@example.org>")]}
    row = outcomes.compute(svc(tmp_path, days, Analytics()), date(2026, 11, 22), http=GitHub())
    assert row["readers"] == 30 and row["agents_readers"] == 4
    assert row["search_clicks"] == 2  # "raising chris" is her own name
    assert row["correspondents"] == 2 and row["merged_prs"] == 1
    assert row["score"] == 30 + 2 + 3 * 2 + 5 * 1 and row["partial"] is False


def test_a_failed_source_is_left_out_and_marked_partial(tmp_path):
    row = outcomes.compute(svc(tmp_path), date(2026, 11, 22),
                           http=SimpleNamespace(get=lambda *a, **k: SimpleNamespace(status_code=403)))
    assert row["readers"] is None and row["merged_prs"] is None and row["partial"] is True


def test_record_daily_writes_once_and_the_meters_line_compares_weeks(tmp_path):
    s = svc(tmp_path, analytics=Analytics())
    gh = GitHub()
    outcomes.record_daily(s, date(2026, 11, 16), http=gh)
    outcomes.record_daily(s, date(2026, 11, 23), http=gh)
    outcomes.record_daily(s, date(2026, 11, 23), http=gh)
    dates = [r["date"] for r in outcomes.history(s)]
    assert dates == sorted(set(dates)) and len(dates) == 6  # the last 3 days of each run, no duplicates
    line = outcomes.line(s)
    assert "7 days to 2026-11-22" in line and "the week before" in line and "people or agents" in line


def _rows(start, days, score):
    return [{"date": (start + timedelta(days=i)).isoformat(), "score": score, "partial": False}
            for i in range(days)]


def test_trial_verdict_reverts_only_on_a_clear_fall_with_enough_signal():
    acc = date(2026, 11, 1)
    before = _rows(acc - timedelta(days=14), 14, 20)
    assert outcomes.trial_verdict(before + _rows(acc, 22, 10), acc)[0] == "revert"
    assert outcomes.trial_verdict(before + _rows(acc, 22, 18), acc)[0] == "keep"
    small = _rows(acc - timedelta(days=14), 14, 2)
    assert outcomes.trial_verdict(small + _rows(acc, 22, 0), acc)[0] == "keep"  # too small to judge
    assert outcomes.trial_verdict(before, acc)[1]["why"].startswith("not enough")


def test_judge_trials_reverts_craft_when_outcomes_fall(tmp_path):
    s = svc(tmp_path)
    (s.repo_dir / "craft").mkdir(parents=True)
    (s.repo_dir / "craft" / "approach.md").write_text("old way\n")
    (s.repo_dir / "craft" / "playbook.jsonl").write_text("")
    craft.bootstrap(s)
    (s.repo_dir / "craft" / "approach.md").write_text("new way\n")
    assert craft.accept(s, {"reason": "test"}) == 1
    t = craft.trial(s)
    acc = date.fromisoformat(t["accepted_on"])
    rows = _rows(acc - timedelta(days=14), 14, 20) + _rows(acc, 22, 5)
    (tmp_path / outcomes.FILE).write_text("".join(json.dumps(r) + "\n" for r in rows))
    assert outcomes.judge_trials(s, acc + timedelta(days=5)) is None  # still running
    out = outcomes.judge_trials(s, acc + timedelta(days=outcomes.TRIAL_DAYS + 1))
    assert out["verdict"] == "revert"
    assert (craft.accepted_dir(s) / "approach.md").read_text() == "old way\n"
    assert craft.version(s)["version"] == 2 and "reverted to v0" in craft.version(s)["note"]
    assert craft.trial(s)["verdict"] == "revert" and outcomes.open_trial(s) is None


def test_open_commitments_keeps_rules_and_open_rows_only():
    text = ("# Commitments\n\nRow rules:\n- one\n\n| # | to whom | what | due | status | where |\n"
            "|---|---|---|---|---|---|\n"
            "| 1 | a | x | d | **CLOSED** 2026-09-08 — done | f |\n"
            "| 2 | b | y | d | OPEN — waiting | f |\n"
            "| 3 | c | z | d | NARROWED 11-03 | f |\n"
            "\n## Log\n- 2026-11-01 checked everything\n")
    out = open_commitments(text)
    assert "Row rules" in out and "| 2 |" in out and "| 3 |" in out
    assert "| 1 |" not in out and "checked everything" not in out and "1 closed rows and the log" in out


def test_autoresponders_and_one_domain_count_little(tmp_path):
    out = {"kind": "mail_out", "ts": "2026-11-20T10:00:00-05:00", "payload": {"to": ["bot@auto.example"]}}
    reply = {"kind": "mail_in", "ts": "2026-11-20T10:01:00-05:00", "payload": {"data": {"from": "bot@auto.example"}}}
    flat = {"kind": "mail_in", "ts": "2026-11-20T11:00:00-05:00", "payload": {"from": "flat@other.example"}}
    same = [mail(f"p{i}@one.example") for i in range(5)]
    days = {"2026-11-20": [out, reply, flat, *same]}
    assert outcomes.correspondents(svc(tmp_path, days), date(2026, 11, 16), date(2026, 11, 22)) == 1 + 2


def test_partial_rows_are_recomputed_later_and_full_rows_never_worsen(tmp_path):
    s = svc(tmp_path, analytics=None)
    bad = SimpleNamespace(get=lambda *a, **k: SimpleNamespace(status_code=500))
    outcomes.record_daily(s, date(2026, 11, 20), http=bad)
    assert outcomes.history(s)[-1]["partial"] is True
    s.analytics = Analytics()
    outcomes.record_daily(s, date(2026, 11, 21), http=GitHub())
    rows = {r["date"]: r for r in outcomes.history(s)}
    assert rows["2026-11-19"]["partial"] is False and rows["2026-11-19"]["readers"] == 30
    s.analytics = None
    outcomes.record_daily(s, date(2026, 11, 22), http=bad)
    assert {r["date"]: r for r in outcomes.history(s)}["2026-11-20"]["partial"] is False


def test_a_failed_revert_still_closes_the_trial(tmp_path, monkeypatch):
    s = svc(tmp_path)
    (tmp_path / "craft").mkdir()
    (tmp_path / "craft" / "trial.json").write_text(json.dumps({"version": 4, "previous": 3,
                                                                "accepted_on": "2026-10-01"}))
    rows = _rows(date(2026, 9, 17), 14, 20) + _rows(date(2026, 10, 1), 22, 5)
    (tmp_path / outcomes.FILE).write_text("".join(json.dumps(r) + "\n" for r in rows))
    out = outcomes.judge_trials(s, date(2026, 11, 1))  # no saved copy of v3 exists
    assert out["verdict"] == "keep" and "revert failed" in out["why"]
    assert outcomes.open_trial(s) is None


def test_a_malformed_trial_file_blocks_nothing(tmp_path):
    s = svc(tmp_path)
    (tmp_path / "craft").mkdir()
    (tmp_path / "craft" / "trial.json").write_text(json.dumps({"version": 4}))
    assert outcomes.open_trial(s) is None and outcomes.judge_trials(s) is None
