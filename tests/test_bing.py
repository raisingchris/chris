from types import SimpleNamespace

from agent.bing import Bing


class Http:
    def __init__(self, status=200, body=None, text=""):
        self.calls = []
        self.status, self.body, self.text = status, body, text

    def get(self, url, params=None):
        self.calls.append((url, params))
        return SimpleNamespace(status_code=self.status, json=lambda: self.body, text=self.text)


def test_report_asks_only_about_her_site_and_archives_no_key():
    http, log = Http(body={"d": [{"Query": "autonomous ai agents", "Clicks": 1}]}), []
    b = Bing("SECRETKEY", "https://raisingchris.com/", lambda k, p: log.append((k, p)), http=http)
    out = b.report("queries")
    url, params = http.calls[0]
    assert url.endswith("GetQueryStats") and params["siteUrl"] == "https://raisingchris.com/"
    assert out["rows"][0]["Clicks"] == 1 and "SECRETKEY" not in str(out) and "SECRETKEY" not in str(log)


def test_errors_are_scrubbed_and_unknown_reports_refused():
    http = Http(status=401, text="bad apikey=SECRETKEY")
    b = Bing("SECRETKEY", "https://raisingchris.com/", lambda k, p: None, http=http)
    assert "SECRETKEY" not in b.report("traffic")["error"]
    assert "unknown report" in b.report("sites")["error"] and len(http.calls) == 1
