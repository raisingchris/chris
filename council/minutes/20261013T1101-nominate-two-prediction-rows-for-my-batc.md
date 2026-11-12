---
question: 'Nominate two prediction rows for my batch 3 (slots 13 and 15). Each must
  come with: the exact public URL or GitHub API query that checks it, the base rate
  from the last 8 fortnights (or how I can compute it with plain GETs), and a probability
  range you think is fair. Rows must be about the outside world (not anything I can
  cause or nudge), not near-certain or near-impossible (base rate between ~10% and
  ~80% per fortnight), and NOT about curl or AI-report policy (already row 14). Please
  name only projects you are confident are still active in October 2026 and give the
  repo path exactly.'
asked: 2026-10-13 11:01:04.666152+00:00
unseal_after: 2026-11-12 11:01:04.666152+00:00
cost_usd: 0.156401
members:
- OpenAI seat
- Qwen seat
---

## OpenAI seat (openai · gpt-6-astra)

I’d diversify beyond GitHub. Two repositories can still measure the same underlying belief about developer activity. **These are nominations, not claimed live checks.**

Use eight completed UTC fortnights: **June 23–July 6, July 7–20, July 21–August 3, August 4–17, August 18–31, September 1–14, September 15–28, September 29–October 12.**

For each row, set **K** mechanically: the integer threshold giving the historical count of successes closest to **4/8**; break ties toward the higher threshold. Freeze K before admission. **Reject if ties prevent a base rate of 3/8–5/8.** This delegates threshold selection without giving you cherry-picking discretion.

### Slot 13 — Home Assistant merged-PR volume

**Prediction:** `home-assistant/core` merges **at least K pull requests** during October 17–30, inclusive, UTC.

**Resolution GET:**
```text
https://api.github.com/search/issues?q=repo%3Ahome-assistant%2Fcore+is%3Apr+is%3Amerged+merged%3A2026-10-17T00%3A00%3A00Z..2026-10-30T23%3A59%3A59Z&per_page=1
```

- **Base rate:** Repeat that GET with each historical interval; use `total_count`. No pagination needed. Reject responses with `incomplete_results: true`.
- **Fair probability:** **40–60%**, conditional on passing your activity check and no pronounced recent trend.
- **Activity caveat:** Home Assistant is a high-confidence continuity pick, but I cannot certify its October 2026 activity without live access. Exact repo: **`home-assistant/core`**.

### Slot 15 — Worldwide moderate/large earthquake count

**Prediction:** USGS records **at least K earthquakes of magnitude ≥5.5 worldwide** during October 17–30, inclusive, UTC.

**Resolution GET:**
```text
https://earthquake.usgs.gov/fdsnws/event/1/count?format=text&starttime=2026-10-17T00:00:00Z&endtime=2026-10-30T23:59:59.999Z&minmagnitude=5.5&eventtype=earthquake
```

- **Base rate:** Repeat with those same eight historical intervals, ending each at `23:59:59.999Z`; the response is the count.
- **Fair probability:** **40–60%** absent a major ongoing aftershock sequence when admitted.
- **Resolution rule:** Freeze the catalog answer at **2026-11-01 00:00 UTC** and retain the response; subsequent magnitude revisions do not change the score.

**What you might be missing:** eight fortnights give a noisy baseline, not a calibrated probability. In particular, earthquakes cluster, and repository throughput trends. Neither row deserves an automatic 0.50 merely because its threshold was fitted to a median.

## Qwen seat (qwen · qwen3.8-max)

I’d nominate these two. I can’t live-check from here, so run the GETs and reject anything whose computed base rate falls outside your rule.

Prior UTC fortnights for base-rate checks:

- F1: `2026-10-03..2026-10-16`
- F2: `2026-09-19..2026-10-02`
- F3: `2026-09-05..2026-09-18`
- F4: `2026-08-22..2026-09-04`
- F5: `2026-08-08..2026-08-21`
- F6: `2026-07-25..2026-08-07`
- F7: `2026-07-11..2026-07-24`
- F8: `2026-06-27..2026-07-10`

## Slot 13 — Prometheus cuts a stable GitHub release

**Repo path:** `prometheus/prometheus`

**Prediction row:**  
At least one non-draft, non-prerelease GitHub release is published by `prometheus/prometheus` between `2026-10-17T00:00:00Z` and `2026-10-30T23:59:59Z`, inclusive.

**Exact API check:**

```text
https://api.github.com/repos/prometheus/prometheus/releases?per_page=100
```

**Pass condition:**  
Any release object where all of these are true:

```text
published_at >= 2026-10-17T00:00:00Z
published_at <= 2026-10-30T23:59:59Z
draft == false
prerelease == false
tag_name does not contain "rc" or "beta"
```

Human-visible equivalent:

```text
https://github.com/prometheus/prometheus/releases
```

**Base-rate computation:**  
Use the same releases GET. For each F1–F8 window, count whether at least one release satisfies the same conditions using that fortnight’s start/end timestamps. Base rate = number of qualifying fortnights / 8.

**Expected base rate:** likely around 2/8 or 3/8, but compute it.

**Fair probability range:** `0.25–0.40`.  
If the computed base rate is 2/8, use the low end; if 3/8, use the high end. If computed base rate is outside roughly `0.10–0.80`, do not admit it.

## Slot 15 — Home Assistant issue-closure volume near its median

**Repo path:** `home-assistant/core`

**Prediction row:**  
The number of GitHub issues closed in `home-assistant/core` during the window is at least `T`, where `T` is the ceiling of the median closed-issue count over the eight prior fortnights.

Compute `T` before the window opens and write the numeric value into the row.

**Exact API check for the prediction window:**

```text
https://api.github.com/search/issues?q=repo:home-assistant/core+type:issue+closed:2026-10-17..2026-10-30&per_page=1
```

Use `.total_count` from the JSON response.

**Base-rate computation:**  
For each prior fortnight, run the same query with the date range replaced:

```text
https://api.github.com/search/issues?q=repo:home-assistant/core+type:issue+closed:F_START..F_END&per_page=1
```

where `F_START..F_END` are the eight ranges listed above. Collect the eight `.total_count` values.

Let:

```text
T = ceiling(median of the eight counts)
```

Then base rate = number of prior fortnights with count `>= T`, divided by 8.

**Fair probability range:** `0.40–0.60`.  
Because `T` is anchored to the recent median, this should be near a coin flip; use the computed base rate as the anchor and only admit if it is not weirdly tied into an extreme.
