"""Invariant 6: character diffs must cite existing archive refs."""

from agent import character_diff as cd

KNOWN = {"archive:2026-09-07#12", "archive:2026-09-07#3"}


def archive_get(ref):
    if ref not in KNOWN:
        raise KeyError(ref)
    return {"ref": ref}


BEFORE = "# Character\n\nI like plain words.\n\n## Diffs\n- 2026-09-06 — born — evidence: archive:2026-09-07#3\n\n## Notes\nkeep\n"
GOOD = "- 2026-09-07 — I answer mail before work — evidence: archive:2026-09-07#12"
UNCITED = "- 2026-09-07 — I am now brave"
MISSING = "- 2026-09-07 — I am now brave — evidence: archive:2026-09-07#99"


def test_validate_flags_uncited_and_missing():
    page = BEFORE.replace("## Notes", f"{GOOD}\n{UNCITED}\n{MISSING}\n\n## Notes")
    problems = cd.validate(page, archive_get=archive_get)
    assert len(problems) == 2
    assert any("malformed" in p and "brave" in p for p in problems)
    assert any("#99" in p and "not in the archive" in p for p in problems)


def test_validate_today_refs():
    page = BEFORE.replace("## Notes", f"{GOOD}\n\n## Notes")
    assert cd.validate(page, today_refs=KNOWN, archive_get=archive_get) == []
    assert cd.validate(page, today_refs={"archive:2026-09-08#1"}, archive_get=archive_get) == [
        f"evidence archive:2026-09-07#3 is not from today: - 2026-09-06 — born — evidence: archive:2026-09-07#3",
        f"evidence archive:2026-09-07#12 is not from today: {GOOD}",
    ]


def test_enforce_rejects_uncited_keeps_cited_and_rest():
    after = BEFORE.replace("I like plain words.", "I like plain words, and short ones.").replace(
        "## Notes", f"{GOOD}\n{UNCITED}\n{MISSING}\n\n## Notes")
    accepted = cd.enforce(BEFORE, after, archive_get)
    assert GOOD in accepted
    assert UNCITED not in accepted and MISSING not in accepted
    assert "short ones" in accepted and "keep" in accepted and "born" in accepted
    assert accepted.endswith("\n")


def test_enforce_untouched_when_no_new_diffs():
    after = BEFORE + "\nmore prose\n"
    assert cd.enforce(BEFORE, after, archive_get) == after


def test_pre_existing_bad_lines_are_not_re_judged():
    before = BEFORE.replace("## Notes", f"{UNCITED}\n\n## Notes")
    after = before.replace("## Notes", f"{GOOD}\n\n## Notes")
    assert UNCITED in cd.enforce(before, after, archive_get)
