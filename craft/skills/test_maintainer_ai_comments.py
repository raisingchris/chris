import maintainer_ai_comments as m


def test_mentions_ai_words_not_substrings():
    assert m.mentions_ai("This looks AI-generated, closing.")
    assert m.mentions_ai("please don't use ChatGPT")
    assert not m.mentions_ai("the said email was maintained")  # 'ai' inside words
    assert not m.mentions_ai(None)


def test_only_staff_who_mention_ai():
    item = {"author_association": "NONE", "body": "LLM wrote this", "user": {"login": "x"}}
    comments = [
        {"author_association": "MEMBER", "body": "We close AI PRs.", "user": {"login": "m"},
         "created_at": "2025-05-01T00:00:00Z", "html_url": "u1"},
        {"author_association": "MEMBER", "body": "Thanks, merged.", "user": {"login": "m"}},
        {"author_association": "CONTRIBUTOR", "body": "AI is fine", "user": {"login": "c"}},
    ]
    got = m.staff_ai_texts(item, comments)
    assert [g["url"] for g in got] == ["u1"]
    assert got[0]["date"] == "2025-05-01"
