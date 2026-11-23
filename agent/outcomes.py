"""Outcomes: one weekly number for what reached anyone outside, scored by the brain.

Chris cannot write this number. Once a day the brain counts the last seven days and
appends a row to ``<state_dir>/outcomes.jsonl``:

- ``readers``: GA4 active users on the site (people; agents that don't run scripts
  are invisible to GA4, so they show up only through the next two lines)
- ``agents_readers``: of those, users of ``/agents*`` (shown, not added twice)
- ``search_clicks``: Search Console clicks on queries that are not her own name
- ``correspondents``: distinct outside senders who mailed her (humans or agents;
  parents, robots and bulk senders left out)
- ``merged_prs``: her pull requests merged upstream

``score = readers + search_clicks + 3 * correspondents + 5 * merged_prs``.
A user is a user, human or machine. A source that fails is ``None`` and left out
of the score, and the row says ``partial``.

The same file decides craft trials: a craft version accepted by the eval is kept
only if the score did not fall while it was in use (see :func:`judge_trials`).
"""

from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

import httpx

log = logging.getLogger("chris.outcomes")

FILE = "outcomes.jsonl"
WINDOW_DAYS = 7
WEIGHTS = {"readers": 1, "search_clicks": 1, "correspondents": 3, "merged_prs": 5}
BRAND_RE = re.compile(r"chris|raising", re.I)
ROBOT_RE = re.compile(r"no-?reply|do-?not-?reply|dmarc|mailer-daemon|postmaster|notifications?@|bounce|"
                      r"@github\.com|@.*google\.com|@stripe\.com|@resend\.|newsletter|digest|support@", re.I)
GITHUB_SEARCH = "https://api.github.com/search/issues"
# Her own repos don't count: she could open and merge pull requests there herself.
OWN_GITHUB = ("raisingchris",)
PER_DOMAIN = 2       # at most this many correspondents counted from one mail domain
AUTOREPLY_S = 300    # a sender whose every mail came within 5 minutes of her mail to them is an autoresponder
RECOMPUTE_DAYS = 3   # GA4 and Search Console fill in late; the last few rows are recomputed each morning


# Trials: a newly accepted craft is in use for TRIAL_DAYS. The 7-day score lags, so only days
# from WINDOW_DAYS after acceptance count as "during"; the BEFORE_DAYS before acceptance are "before".
TRIAL_DAYS = 21
BEFORE_DAYS = 14
MIN_BEFORE = 5.0     # below this the signal is too small to judge; the version is kept
FALL_RATIO = 0.8     # during < 80% of before → revert
MIN_DAYS = 5         # fewer measured days on either side → kept, "not enough data"


def _path(services) -> Path:
    return Path(services.cfg.state_dir) / FILE


def _sender(addr: Any) -> str:
    if not isinstance(addr, str):
        return ""
    m = re.search(r"<([^>]+)>", addr)
    return (m.group(1) if m else addr).strip().lower()


def _ts(rec: dict) -> datetime | None:
    try:
        return datetime.fromisoformat(str(rec.get("ts")))
    except ValueError:
        return None


def correspondents(services, start: date, end: date) -> int:
    """Distinct outside senders in the archive between start and end (inclusive).

    Parents, her own address and robot-looking senders are left out; so is a sender whose every
    mail arrived within AUTOREPLY_S of her mail to them (an autoresponder), and no domain counts
    more than PER_DOMAIN senders.
    """
    handles = {h.lower() for h in services.cfg.parent_handles}
    own = str(getattr(services.cfg, "chris_email", "") or "").lower()
    sent: dict[str, list[datetime]] = {}
    got: dict[str, list[datetime | None]] = {}
    d = start - timedelta(days=1)
    while d <= end:
        for rec in services.archive.read_day(d.isoformat()):
            kind, payload = rec.get("kind"), rec.get("payload") or {}
            if kind == "mail_out":
                to = payload.get("to") or []
                for addr in (to if isinstance(to, list) else [to]):
                    t = _ts(rec)
                    if t is not None:
                        sent.setdefault(_sender(addr), []).append(t)
            elif kind == "mail_in" and d >= start:
                data = payload.get("data", payload) if isinstance(payload, dict) else {}
                s = _sender((data or {}).get("from"))
                if not s or s in handles or (own and s == own) or ROBOT_RE.search(s):
                    continue
                got.setdefault(s, []).append(_ts(rec))
        d += timedelta(days=1)

    def autoreply(s: str) -> bool:
        outs = sent.get(s) or []
        ins = got[s]
        return bool(outs) and all(t is not None and any(0 <= (t - o).total_seconds() <= AUTOREPLY_S for o in outs)
                                  for t in ins)

    per_domain: dict[str, int] = {}
    n = 0
    for s in sorted(got):
        if autoreply(s):
            continue
        dom = s.rsplit("@", 1)[-1]
        if per_domain.get(dom, 0) >= PER_DOMAIN:
            continue
        per_domain[dom] = per_domain.get(dom, 0) + 1
        n += 1
    return n


def _ga4_users(analytics, start: str, end: str, prefix: str | None = None) -> int | None:
    filters = None
    if prefix:
        filters = {"filter": {"fieldName": "pagePath",
                              "stringFilter": {"matchType": "BEGINS_WITH", "value": prefix}}}
    r = analytics.ga4_report([], ["activeUsers"], start, end, limit=1, filters=filters)
    if "error" in r:
        return None
    rows = r.get("rows") or []
    return int(rows[0].get("activeUsers") or 0) if rows else 0


def _search_clicks(analytics, start: str, end: str) -> int | None:
    r = analytics.gsc_query(start, end, ["query"], row_limit=1000)
    if "error" in r:
        return None
    return sum(int(row.get("clicks") or 0) for row in r.get("rows") or []
               if not BRAND_RE.search(str(row.get("query") or "")))


def _merged_prs(user: str, start: str, end: str, http: httpx.Client | None = None) -> int | None:
    if not user:
        return None
    try:
        client = http or httpx.Client(timeout=30)
        own = " ".join(f"-user:{o}" for o in (user, *OWN_GITHUB))
        r = client.get(GITHUB_SEARCH, params={"q": f"is:pr author:{user} is:merged merged:{start}..{end} {own}",
                                              "per_page": 1},
                       headers={"Accept": "application/vnd.github+json"})
        if r.status_code != 200:
            return None
        return int(r.json().get("total_count") or 0)
    except Exception as exc:  # noqa: BLE001
        log.warning("github search failed: %s", exc)
        return None


def score(row: dict) -> int:
    return sum(int(row.get(k) or 0) * w for k, w in WEIGHTS.items())


def compute(services, end: date, http: httpx.Client | None = None) -> dict:
    """The row for the seven days ending on ``end`` (inclusive). Never raises."""
    start = end - timedelta(days=WINDOW_DAYS - 1)
    s, e = start.isoformat(), end.isoformat()
    row: dict[str, Any] = {"date": e, "from": s}
    an = getattr(services, "analytics", None)
    for key, fn in (("readers", lambda: _ga4_users(an, s, e)),
                    ("agents_readers", lambda: _ga4_users(an, s, e, "/agents")),
                    ("search_clicks", lambda: _search_clicks(an, s, e))):
        try:
            row[key] = fn() if an is not None else None
        except Exception as exc:  # noqa: BLE001
            log.warning("outcomes %s failed: %s", key, exc)
            row[key] = None
    try:
        row["correspondents"] = correspondents(services, start, end)
    except Exception as exc:  # noqa: BLE001
        log.warning("outcomes correspondents failed: %s", exc)
        row["correspondents"] = None
    row["merged_prs"] = _merged_prs(str(getattr(services.cfg, "github_user", "") or ""), s, e, http)
    row["partial"] = any(row.get(k) is None for k in WEIGHTS)
    row["score"] = score(row)
    return row


def history(services) -> list[dict]:
    try:
        lines = _path(services).read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    out = []
    for ln in lines:
        try:
            out.append(json.loads(ln))
        except json.JSONDecodeError:
            continue
    return out


def _write_history(services, rows: list[dict]) -> None:
    p = _path(services)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    tmp.replace(p)


def record_daily(services, today: date | None = None, http: httpx.Client | None = None) -> dict:
    """Write yesterday's 7-day row, and recompute the last few rows (late data) and any partial ones
    from the last trial span (a source that failed one morning). Returns yesterday's row."""
    today = today or datetime.now(ZoneInfo(services.cfg.tz)).date()
    rows = {str(r.get("date")): r for r in history(services) if isinstance(r, dict) and r.get("date")}
    oldest = today - timedelta(days=TRIAL_DAYS + BEFORE_DAYS)
    redo = [today - timedelta(days=i) for i in range(1, RECOMPUTE_DAYS + 1)]
    redo += [date.fromisoformat(k) for k, r in rows.items()
             if r.get("partial") and k >= oldest.isoformat() and date.fromisoformat(k) not in redo]
    for end in redo:
        row = compute(services, end, http)
        old = rows.get(end.isoformat())
        if old is not None and not old.get("partial") and row.get("partial"):
            continue  # never replace a full row with a worse one
        rows[end.isoformat()] = row
    _write_history(services, [rows[k] for k in sorted(rows)])
    row = rows[(today - timedelta(days=1)).isoformat()]
    services.archive.append("outcomes", {"kind": "outcomes", **row})
    return row


def line(services) -> str:
    """One line for the meters: this week's score and last week's, with the parts."""
    rows = [r for r in history(services) if isinstance(r, dict) and r.get("date")]
    if not rows:
        return "Outcomes (scored by the brain): no count yet."
    cur = rows[-1]
    prev_date = (date.fromisoformat(cur["date"]) - timedelta(days=WINDOW_DAYS)).isoformat()
    prev = next((r for r in reversed(rows) if r.get("date") == prev_date), None)

    def v(k):
        return "?" if cur.get(k) is None else cur.get(k)

    out = (f"Outcomes, 7 days to {cur['date']} (scored by the brain; users can be people or agents): "
           f"score {cur.get('score')} = {v('readers')} readers ({v('agents_readers')} on /agents) "
           f"+ {v('search_clicks')} non-name search clicks + 3×{v('correspondents')} outside correspondents "
           f"+ 5×{v('merged_prs')} merged PRs")
    if cur.get("partial"):
        out += " (partial: a source failed)"
    if prev is not None:
        out += f"; the week before: {prev.get('score')}"
    return out + "."


def mean_between(rows: list[dict], start: date, end: date) -> tuple[float | None, int]:
    vals = [float(r.get("score") or 0) for r in rows
            if isinstance(r, dict) and not r.get("partial") and start.isoformat() <= str(r.get("date")) <= end.isoformat()]
    return (sum(vals) / len(vals) if vals else None), len(vals)


def trial_verdict(rows: list[dict], accepted_on: date) -> tuple[str, dict]:
    """("keep" | "revert", detail) for a craft accepted on ``accepted_on`` whose trial is over."""
    before, nb = mean_between(rows, accepted_on - timedelta(days=BEFORE_DAYS), accepted_on - timedelta(days=1))
    during, nd = mean_between(rows, accepted_on + timedelta(days=WINDOW_DAYS),
                              accepted_on + timedelta(days=TRIAL_DAYS))
    detail = {"before": before, "before_days": nb, "during": during, "during_days": nd}
    if nb < MIN_DAYS or nd < MIN_DAYS or before is None or during is None:
        return "keep", {**detail, "why": "not enough measured days to judge"}
    if before < MIN_BEFORE:
        return "keep", {**detail, "why": f"before-score {before:.1f} too small to judge"}
    if during < FALL_RATIO * before:
        return "revert", {**detail, "why": f"score fell from {before:.1f} to {during:.1f}"}
    return "keep", {**detail, "why": f"score {before:.1f} → {during:.1f}"}


def open_trial(services) -> dict | None:
    """The accepted craft version still on trial, or None (a malformed trial file counts as none)."""
    from agent import craft

    t = craft.trial(services)
    if not t or t.get("verdict"):
        return None
    try:
        date.fromisoformat(str(t["accepted_on"]))
        int(t["previous"])
    except (KeyError, TypeError, ValueError):
        return None
    return t


def judge_trials(services, today: date | None = None) -> dict | None:
    """End a trial that has run its course: keep the version or revert to the one before it.

    Always closes the trial once it is over, even when the revert fails, so a candidate never waits forever.
    """
    from agent import craft

    t = open_trial(services)
    if not t:
        return None
    today = today or datetime.now(ZoneInfo(services.cfg.tz)).date()
    accepted_on = date.fromisoformat(t["accepted_on"])
    if today <= accepted_on + timedelta(days=TRIAL_DAYS):
        return None
    verdict, detail = trial_verdict(history(services), accepted_on)
    if verdict == "revert":
        try:
            craft.revert(services, int(t["previous"]), f"outcomes: {detail['why']}")
        except Exception as exc:  # noqa: BLE001
            verdict, detail = "keep", {**detail, "why": f"revert failed ({type(exc).__name__}: {exc}); kept"}
    craft.end_trial(services, verdict, detail)
    services.archive.append("craft_trial", {"kind": "craft_trial", "version": t.get("version"),
                                            "verdict": verdict, **detail})
    return {"verdict": verdict, **detail}
