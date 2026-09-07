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


CANARIES = ["Alice Realname", "Example Holdings"]


@pytest.fixture
def mail(tmp_path, archive):
    return Mail(
        repo_dir=tmp_path,
        archive_append=archive,
        parents=PARENTS,
        chris_email=CHRIS,
        dry_run=True,
        canaries=CANARIES,
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
    # the event is archived with the sender already mapped to the handle — the raw address is nowhere
    kind, payload = archive.entries[0]
    assert kind == "mail_in"
    assert payload["data"]["from"] == "parent-a"
    assert_no_real_address(str(archive.entries))
    assert meta["email_id"] == "em_in_1"
    # the signature line carried a canary (the parent's display name); it is gone from the file
    assert "Alice" not in text


def test_ingest_stranger_keeps_address(mail, archive):
    mail.fetch_body = lambda _id: {"text": "hello, write me at other@else.org or ring +1 415 555 0100\n", "html": None}
    path = mail.ingest(webhook("someone@else.org", subject="Q"))
    text = path.read_text()
    assert "from: someone@else.org" in text  # the from: line is never redacted — she needs it to reply
    assert "other@else.org" not in text and "555" not in text  # the body is
    assert archive.entries[0][1]["data"]["from"] == "someone@else.org"


def test_ingest_redacts_canaries_and_parent_names_in_body_and_subject(mail, archive):
    mail.fetch_body = lambda _id: {"text": f"Alice Realname says hi; cc {PARENT_B}; Example Holdings pays.\n", "html": None}
    path = mail.ingest(webhook("s@e.org", subject=f"From Alice Realname <{PARENT_A}>"))
    text = path.read_text()
    assert_no_real_address(text)
    assert "Alice" not in text and "Example Holdings" not in text
    assert "cc parent-b" in text
    # archived subject: parent address mapped; the canary name is a redaction concern for what she reads
    assert PARENT_A not in str(archive.entries)


def test_ingest_anonymises_every_address_field_in_the_archived_event(mail, archive):
    mail.fetch_body = lambda _id: {"text": "x", "html": None}
    event = webhook(f"Bob <{PARENT_B}>")
    event["data"]["to"] = [CHRIS, PARENT_A]
    event["data"]["cc"] = [f"A <{PARENT_A}>", "friend@else.org"]
    event["data"]["reply_to"] = PARENT_B
    mail.ingest(event)
    data = archive.entries[0][1]["data"]
    assert data["from"] == "parent-b" and data["to"] == [CHRIS, "parent-a"]
    assert data["cc"] == ["parent-a", "friend@else.org"] and data["reply_to"] == "parent-b"
    assert event["data"]["from"] == f"Bob <{PARENT_B}>"  # caller's payload untouched
    assert_no_real_address(str(archive.entries))


def test_ingest_dedupes_on_email_id(mail, archive):
    fetched = []
    mail.fetch_body = lambda _id: fetched.append(_id) or {"text": "once", "html": None}
    p1 = mail.ingest(webhook("s@e.org", email_id="dup_1"))
    p2 = mail.ingest(webhook("s@e.org", email_id="dup_1"))
    assert p1 == p2 and fetched == ["dup_1"]
    assert len(list((mail.inbox_dir).glob("*.md"))) == 1
    assert [k for k, _ in archive.entries] == ["mail_in", "mail_in_duplicate"]
    assert mail.ingest(webhook("s@e.org", email_id="dup_2")) != p1


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


def test_send_does_not_double_sign(tmp_path):
    from agent.mail import Mail, SIGNATURE
    m = Mail(tmp_path, lambda k, p: "archive:2026-01-01#1", {"parent-a": "a@x.com"}, "chris@raisingchris.com", dry_run=True)
    body = "Hello.\n\nChris\n\nI'm an AI. Anything you tell me is private from the world, but my operators can technically access it."
    out = m.send("parent-a", "s", body)
    assert out["text"].count("I'm an AI.") == 1
    assert out["text"].endswith(SIGNATURE)


def test_double_chevron_reply_markers_are_kept():
    from agent.mail import _clean_body
    body = "Hey.\n\n~ her question\n>> my answer line\n>>second answer\n> quoted client line\n\nOn Mon, Chris wrote:\n> old stuff"
    out = _clean_body(body)
    assert ">> my answer line" in out and ">>second answer" in out
    assert "quoted client line" not in out and "old stuff" not in out


def test_daily_summary_lists_open_tickets_after_odometer(mail, archive):
    res = mail.daily_summary("2026-09-06", "Diary.", "Odometer: 3 loops", "Spend: $4.20", 0,
                             tickets_line="2 open ticket(s) for you: A key; A deploy")
    body = res["text"]
    assert "Odometer: 3 loops\n2 open ticket(s) for you: A key; A deploy\nSpend: $4.20" in body
    res = mail.daily_summary("2026-09-06", "Diary.", "Odometer: 3 loops", "Spend: $4.20", 0)
    assert "open ticket" not in res["text"]
