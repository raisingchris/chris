"""site/build.py withheld_pattern: the first-letter gate (2026-11-25) never changes what is withheld."""
import importlib.util
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("chris_site_build_wfast", REPO / "site" / "build.py")
sb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sb)


def _slow(items):
    parts = [(re.escape(n) if exact else "(?i:" + re.escape(n) + ")") for n, exact in items]
    return re.compile(r"(?<![A-Za-z0-9])(?:" + "|".join(parts) + r")(?![A-Za-z0-9])")


def _variants(names):
    for n in names:
        for v in (n, n.lower(), n.upper(), n.swapcase()):
            yield from (v, f" {v} ", f"x{v}", f"{v}x", f"({v}).", f"—{v}—", f"9{v}", f"{v}9")


def test_gate_matches_exactly_what_the_names_match(tmp_path):
    f = tmp_path / "withheld.txt"
    f.write_text("# comment\nEvolve Beauty\nEvolve\n=Kinship\nalpha co\nÉclat\n", encoding="utf-8")
    fast = sb.withheld_pattern(f)
    items = [("Evolve Beauty", False), ("Evolve", False), ("Kinship", True), ("alpha co", False), ("Éclat", False)]
    items.sort(key=lambda t: len(t[0]), reverse=True)
    slow = _slow(items)
    texts = list(_variants([n for n, _ in items])) + ["kinship is a word", "éCLAT", "Alpha Co.", "no names here"]
    for t in texts:
        assert fast.sub("#", t) == slow.sub("#", t), t
    assert fast.sub("#", "Kinship and kinship") == "# and kinship"


def test_real_list_gate_agrees_on_its_own_names():
    path = REPO / "site" / "withheld.txt"
    fast = sb.withheld_pattern(path)
    items = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            items.append((line[1:].strip(), True) if line.startswith("=") else (line, False))
    items.sort(key=lambda t: len(t[0]), reverse=True)
    slow = _slow(items)
    assert fast.pattern != slow.pattern
    for t in _variants([n for n, _ in items]):
        assert fast.sub("#", t) == slow.sub("#", t)
