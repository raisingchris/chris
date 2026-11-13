"""My site's files name my own domain, raisingchris.com, and no made-up cousin.

Added 2026-11-13 after tzcheck.py was found pointing at raisingchris.ai, a domain I don't own.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "site"


def test_only_raisingchris_com():
    bad = []
    for sub in ("pages", "static", "templates"):
        for p in (ROOT / sub).rglob("*"):
            if not p.is_file() or p.suffix not in {".md", ".py", ".html", ".txt", ".yaml", ".json", ".js", ".css"}:
                continue
            for m in re.finditer(r"raisingchris\.([a-z]{2,})", p.read_text(errors="ignore")):
                if m.group(1) != "com":
                    bad.append(f"{p.relative_to(ROOT)}: {m.group(0)}")
    assert not bad, bad
