"""Post to X (Twitter) through Typefully, an X partner.

Chris never holds an X login. The Typefully API key identifies her parents'
account, so it lives only in this process — it never reaches her shell, the tool
result, or any archive record. The archive gets
``{kind, n_posts, published, url, draft_id}`` and nothing else, never the key.

Posting is metered against a weekly cap the same way the council is: the meter
counts *posted* tweets (a thread of k posts counts k); drafts are free. X is a
megaphone, not a conversation, so the cap is deliberately small.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Iterable

import httpx

BASE_URL = "https://api.typefully.com/v2/"
MAX_CHARS = 280
TIMEOUT_S = 30
POLL_TIMEOUT_S = 30  # give up waiting for "finished" after roughly this long
POLL_INTERVAL_S = 2
PUBLISHING_MSG = "publishing, check X"


class XError(ValueError):
    """A post that cannot be sent as given — empty, or a single post over 280 chars."""


def scrub(text: str, api_key: str) -> str:
    """Never let the API key leak into an error string."""
    text = str(text)
    if api_key:
        text = text.replace(api_key, "<redacted>")
    return text


class XClient:
    def __init__(self, api_key: str, social_set: str, archive_append: Callable[[str, dict], Any],
                 meter, weekly_cap: int = 7, http: httpx.Client | None = None):
        self._api_key = api_key
        self._social_set = str(social_set)
        self._archive = archive_append
        self.meter = meter
        self.weekly_cap = int(weekly_cap)
        self._http = http or httpx.Client(base_url=BASE_URL, timeout=TIMEOUT_S)
        # Poll pacing is instance state so tests can drive it to zero (poll once, don't sleep).
        self.poll_timeout = POLL_TIMEOUT_S
        self.poll_interval = POLL_INTERVAL_S
        self._sleep = time.sleep
        self._monotonic = time.monotonic

    # -- public API --------------------------------------------------------
    def post(self, text_or_list: str | Iterable[str], publish: bool = True) -> dict:
        return self._create(text_or_list, publish=publish)

    def draft(self, text_or_list: str | Iterable[str]) -> dict:
        return self._create(text_or_list, publish=False)

    # -- internals ---------------------------------------------------------
    def _posts(self, text_or_list: str | Iterable[str]) -> list[str]:
        posts = [text_or_list] if isinstance(text_or_list, str) else [str(p) for p in text_or_list]
        posts = [str(p) for p in posts]
        if not posts or not any(p.strip() for p in posts):
            raise XError("there is nothing to post.")
        for p in posts:
            if len(p) > MAX_CHARS:
                raise XError(f"a post is {len(p)} characters; X allows {MAX_CHARS}. Split it into a thread or trim it.")
        return posts

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}

    def _create(self, text_or_list: str | Iterable[str], publish: bool) -> dict:
        posts = self._posts(text_or_list)  # raises XError before any request
        n = len(posts)
        if publish and self.meter.exceeded(self.weekly_cap):
            return {"refused": (f"You've already posted {int(self.meter.spent())} to X this week; "
                                f"the cap is {self.weekly_cap} posts a week. It resets Monday. "
                                "X is a megaphone — save it for something worth saying."),
                    "published": False, "n_posts": n}
        title = (posts[0][:60] or "Chris").strip()
        body: dict[str, Any] = {
            "platforms": {"x": {"enabled": True, "posts": [{"text": p} for p in posts]}},
            "draft_title": title,
        }
        if publish:
            body["publish_at"] = "now"
        url = f"{BASE_URL}social-sets/{self._social_set}/drafts"
        try:
            r = self._http.post(url, json=body, headers=self._headers())
        except httpx.HTTPError as exc:
            return {"error": scrub(f"{type(exc).__name__}: {exc}", self._api_key), "status_code": None,
                    "published": False, "n_posts": n}
        rbody = self._json(r)
        if not 200 <= r.status_code < 300:
            msg = rbody.get("detail") or rbody.get("message") or rbody.get("error") or r.text[:500]
            self._record(n, published=False, url=None, draft_id=rbody.get("id"))
            return {"error": scrub(msg or f"Typefully returned HTTP {r.status_code}", self._api_key),
                    "status_code": r.status_code, "published": False, "n_posts": n}

        draft_id = rbody.get("id")
        if not publish:
            self._record(n, published=False, url=None, draft_id=draft_id)
            return {"status": "draft", "published": False, "draft_id": draft_id, "n_posts": n}

        # The tweets were accepted for publishing: count them now so a slow or
        # silent free-tier publish can't be retried into an over-cap flood.
        self.meter.add_usd(n, "x_post")
        published, pub_url, state = self._poll(draft_id)
        self._record(n, published=published, url=pub_url, draft_id=draft_id)
        if published:
            return {"status": "finished", "published": True, "url": pub_url, "draft_id": draft_id, "n_posts": n}
        # 201 but never confirmed finished (free tier is slow, or it errored/nulled out).
        return {"status": state or "pending", "published": False, "draft_id": draft_id, "n_posts": n,
                "message": PUBLISHING_MSG if state not in ("errored", "error") else
                           f"Typefully reports publish_state={state!r} — it did not go out; {PUBLISHING_MSG}."}

    def _poll(self, draft_id: Any) -> tuple[bool, str | None, str | None]:
        """Poll the draft until publish_state=='finished'; give up after ~poll_timeout.

        Returns ``(published, url, last_state)``.
        """
        if draft_id in (None, ""):
            return False, None, None
        url = f"{BASE_URL}social-sets/{self._social_set}/drafts/{draft_id}"
        deadline = self._monotonic() + self.poll_timeout
        state: str | None = None
        while True:
            try:
                r = self._http.get(url, headers={"Authorization": f"Bearer {self._api_key}"})
            except httpx.HTTPError:
                return False, None, state
            b = self._json(r)
            state = b.get("publish_state")
            if state == "finished":
                return True, self._extract_url(b), state
            if state in ("errored", "error"):
                return False, None, state
            if self._monotonic() >= deadline:
                return False, None, state
            self._sleep(self.poll_interval)

    @staticmethod
    def _json(r: httpx.Response) -> dict:
        try:
            b = r.json()
        except ValueError:
            return {}
        return b if isinstance(b, dict) else {"result": b}

    @staticmethod
    def _extract_url(body: dict) -> str | None:
        """Pull a published URL out of the drafts response, defensively."""
        platforms = body.get("platforms")
        if isinstance(platforms, dict):
            x = platforms.get("x")
            if isinstance(x, dict):
                for p in x.get("posts") or []:
                    if isinstance(p, dict):
                        u = p.get("url") or p.get("tweet_url") or p.get("permalink")
                        if u:
                            return str(u)
        for key in ("share_url", "url", "permalink"):
            if body.get(key):
                return str(body[key])
        return None

    def _record(self, n: int, published: bool, url: str | None, draft_id: Any) -> None:
        self._archive("x_post", {"kind": "x_post", "n_posts": n, "published": bool(published),
                                 "url": url, "draft_id": draft_id})
