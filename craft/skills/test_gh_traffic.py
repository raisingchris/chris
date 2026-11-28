from gh_traffic import summarize


def test_bots_flagged_when_clones_without_views():
    line = summarize("tz-2026", {"count": 0, "uniques": 0}, {"count": 944, "uniques": 262}, [])
    assert "views 0/0" in line and "clones 944/262" in line
    assert "bots" in line


def test_people_and_referrers():
    line = summarize("x", {"count": 5, "uniques": 3}, {"count": 1, "uniques": 1},
                     [{"referrer": "github.com", "count": 4}, {"referrer": "google.com", "count": 1}])
    assert "bots" not in line
    assert "from github.com 4, google.com 1" in line


def test_unreadable_views():
    assert "views unreadable" in summarize("x", None, None, None)
