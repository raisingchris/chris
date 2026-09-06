from pathlib import Path

import pytest

from agent.mail import SIGNATURE, Mail

PARENT_A = "alice.realname@example.com"
PARENT_B = "Bob.Other@Corp.example"
PARENTS = {"parent-a": PARENT_A, "parent-b": PARENT_B}
CHRIS = "chris@raisingchris.com"


class FakeArchive:
    def __init__(self):
        self.entries = []

    def __call__(self, kind, payload):
        self.entries.append((kind, payload))
        return f"archive:2026-09-06#{len(self.entries)}"


@pytest.fixture
def archive():
    return FakeArchive()


@pytest.fixture
def mail(tmp_path, archive):
    return Mail(
        repo_dir=tmp_path,
        archive_append=archive,
        parents=PARENTS,
        chris_email=CHRIS,
        dry_run=True,
    )


def assert_no_real_address(text: str):
    low = text.lower()
    assert PARENT_A.lower() not in low
    assert PARENT_B.lower() not in low
    assert "alice.realname" not in low
    assert "bob.other" not in low


# --- mapping -----------------------------------------------------------------


def test_resolve_handle_to_real_and_passthrough(mail):
    assert mail.resolve("parent-a") == PARENT_A
    assert mail.resolve("parent-b") == PARENT_B
    assert mail.resolve("stranger@example.org") == "stranger@example.org"


def test_map_addresses_replaces_full_and_local_part_case_insensitive(mail):
    text = (
        f"From {PARENT_A} and {PARENT_B.upper()}; "
        "also alice.realname said hi, and BOB.OTHER too."
    )
    out = mail.map_addresses(text)
    assert_no_real_address(out)
    assert out.count("parent-a") == 2
    assert out.count("parent-b") == 2


# --- send --------------------------------------------------------------------


def test_send_appends_signature_and_dry_run(mail):
    res = mail.send("parent-a", "Hello", "body text")
    assert res["dry_run"] is True
    assert res["to"] == [PARENT_A]
    assert res["from"] == CHRIS
    assert res["text"] == "body text" + SIGNATURE
    assert SIGNATURE.startswith("\n\n— Chris\nI'm an AI.")


def test_send_archives_handle_not_real_address(mail, archive):
    mail.send(["parent-a", "parent-b"], "Hi", "x")
    kinds = [k for k, _ in archive.entries]
    assert kinds == ["mail_out"]
    _, payload = archive.entries[0]
    assert payload["to"] == ["parent-a", "parent-b"]
    assert payload["subject"] == "Hi"
    assert_no_real_address(str(payload))


def test_send_uses_resend_when_not_dry_run(tmp_path, archive, monkeypatch):
    import resend

    calls = {}

    class FakeEmails:
        @staticmethod
        def send(params):
            calls["params"] = params
            return {"id": "em_123"}

    monkeypatch.setattr(resend, "Emails", FakeEmails)
    m = Mail(tmp_path, archive, PARENTS, CHRIS, resend_api_key="re_test")
    res = m.send("parent-b", "S", "B", in_reply_to="<abc@x>")
    assert resend.api_key == "re_test"
    assert calls["params"]["to"] == [PARENT_B]
    assert calls["params"]["from"] == CHRIS
    assert calls["params"]["headers"]["In-Reply-To"] == "<abc@x>"
    assert res["id"] == "em_123"


# --- ingest ------------------------------------------------------------------


def webhook(sender, subject="Morning note", email_id="em_in_1"):
    return {
        "type": "email.received",
        "created_at": "2026-09-06T11:02:03.000Z",
        "data": {
            "email_id": email_id,
            "created_at": "2026-09-06T11:02:03.000Z",
            "from": sender,
            "to": [CHRIS],
            "subject": subject,
            "message_id": "<m1@example.com>",
        },
    }


RAW_BODY = (
    "Hi Chris,\n\nDo the reading today. Ask alice.realname if stuck.\n"
    f"cc {PARENT_B}\n\n"
    "Love\n\n-- \nAlice Realname\nSent from my phone\n\n"
    f"On Sat, Sep 5, 2026 at 9:00 PM Chris <{CHRIS}> wrote:\n"
    "> earlier stuff\n> more\n"
)


def test_ingest_writes_inbox_file_without_real_address(mail, archive, tmp_path):
    fetched = []

    def fetch_body(email_id):
        fetched.append(email_id)
        return {"text": RAW_BODY, "html": "<p>x</p>"}

    mail.fetch_body = fetch_body
    path = mail.ingest(webhook(f"Alice <{PARENT_A}>"))

    assert fetched == ["em_in_1"]
    assert path.parent == tmp_path / "memory" / "inbox"
    assert path.name.startswith("2026-09-06-morning-note")
    text = path.read_text()
    assert_no_real_address(text)
    import frontmatter

    meta = frontmatter.loads(text).metadata
    assert meta["from"] == "parent-a"
    assert meta["subject"] == "Morning note"
    assert meta["archive"] == "archive:2026-09-06#1"
    assert str(meta["received"]).startswith("2026-09-06 11:02:03")  # ISO timestamp, YAML-parsed
    # quoted history and signature stripped, content kept, addresses mapped
    assert "Do the reading today." in text
    assert "Ask parent-a if stuck" in text
    assert "cc parent-b" in text
    assert "earlier stuff" not in text
    assert "wrote:" not in text
    assert "Sent from my phone" not in text
    # raw event archived first, with the raw sender (archive is not Chris-readable)
    kind, payload = archive.entries[0]
    assert kind == "mail_in"
    assert payload["data"]["from"] == f"Alice <{PARENT_A}>"


def test_ingest_stranger_keeps_address(mail):
    mail.fetch_body = lambda _id: {"text": "hello\n", "html": None}
    path = mail.ingest(webhook("someone@else.org", subject="Q"))
    assert "from: someone@else.org" in path.read_text()


def test_ingest_strips_original_message_marker_and_quotes(mail):
    body = "keep this\n> quoted line\n-----Original Message-----\nFrom: x\nold text\n"
    mail.fetch_body = lambda _id: {"text": body, "html": None}
    text = mail.ingest(webhook("s@e.org")).read_text()
    assert "keep this" in text
    assert "quoted line" not in text
    assert "old text" not in text


def test_ingest_falls_back_to_html_when_no_text(mail):
    mail.fetch_body = lambda _id: {"text": None, "html": "<p>Hello <b>there</b></p>"}
    text = mail.ingest(webhook("s@e.org")).read_text()
    assert "Hello there" in text


def test_ingest_avoids_filename_collision(mail):
    mail.fetch_body = lambda _id: {"text": "a", "html": None}
    p1 = mail.ingest(webhook("s@e.org", email_id="1"))
    p2 = mail.ingest(webhook("s@e.org", email_id="2"))
    assert p1 != p2 and p1.exists() and p2.exists()


# --- daily summary -----------------------------------------------------------


def test_daily_summary_goes_to_both_parents(mail, archive):
    res = mail.daily_summary(
        "2026-09-06", "# Diary\nGood day.", "Odometer: 3 loops", "Spend: $4.20", 2
    )
    assert sorted(res["to"]) == sorted([PARENT_A, PARENT_B])
    assert res["subject"] == "Chris — 2026-09-06"
    assert res["reply_to"] == CHRIS
    body = res["text"]
    assert "Good day." in body
    assert "Odometer: 3 loops" in body
    assert "Spend: $4.20" in body
    assert "Reply to this email and Chris reads it in the morning. Assignments welcome." in body
    assert body.endswith(SIGNATURE)
    _, payload = archive.entries[0]
    assert sorted(payload["to"]) == ["parent-a", "parent-b"]


# --- unread ------------------------------------------------------------------


def test_list_unread_and_mark_read(mail):
    mail.fetch_body = lambda _id: {"text": "a", "html": None}
    p1 = mail.ingest(webhook("s@e.org", email_id="1"))
    p2 = mail.ingest(webhook("s@e.org", email_id="2"))
    assert set(mail.list_unread()) == {p1, p2}
    mail.mark_read(p1)
    assert mail.list_unread() == [p2]
    assert "read: true" in p1.read_text()
    assert p1.read_text().startswith("---\n")
