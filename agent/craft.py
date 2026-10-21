"""Her craft: how she works (approach), what she has learned works (playbook), and scripts she keeps (skills).

There are two copies. The *working* copy is ``craft/`` in her repo, and she edits it whenever she likes.
The *accepted* copy lives in the brain's state dir, where she cannot write, and it is what every sitting
reads. A working-copy change reaches the accepted copy only through an eval run that does not get worse
(``agent/evals.py``). That gate is the point: a self-improvement loop that grades itself drifts into
notes about itself (2026-10-21 review), so the grade comes from outside.

Playbook bullets carry helpful/harmful counters. Counters are feedback, not content, so she may bump
them in any sitting through the ``craft`` tool; a bullet marked harmful more than helpful drops out of
the prompt. New or reworded bullets are content and go through the eval like everything else.

Skills (``craft/skills/``) are scripts she runs from her own shell, so gating them would be theatre;
they are listed from the working copy.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

CRAFT = Path("craft")
APPROACH = "approach.md"
PLAYBOOK = "playbook.jsonl"
SKILLS = "skills"
LINEAGE = Path("governance") / "lineage.jsonl"

MAX_APPROACH_CHARS = 4000
MAX_BULLETS = 60
MAX_BULLET_CHARS = 300
PROMPT_BULLETS = 40
DROP_MARGIN = 2  # harmful - helpful above this hides a bullet from the prompt


class CraftError(ValueError):
    pass


def working_dir(services) -> Path:
    return Path(services.repo_dir) / CRAFT


def accepted_dir(services) -> Path:
    return Path(services.state_dir) / "craft" / "accepted"


def _version_path(services) -> Path:
    return Path(services.state_dir) / "craft" / "version.json"


def version(services) -> dict:
    try:
        return json.loads(_version_path(services).read_text()) or {}
    except (OSError, json.JSONDecodeError):
        return {}


def load_playbook(path: Path) -> list[dict]:
    """Parse playbook.jsonl; a bad line is skipped, never fatal (the sitting must still start)."""
    out = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return out
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            b = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(b, dict) and str(b.get("id", "")).strip() and str(b.get("text", "")).strip():
            b["id"] = str(b["id"]).strip()
            b["text"] = str(b["text"]).strip()
            b["helpful"] = int(b.get("helpful", 0) or 0)
            b["harmful"] = int(b.get("harmful", 0) or 0)
            out.append(b)
    return out


def _write_playbook(path: Path, bullets: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(b, ensure_ascii=False) + "\n" for b in bullets), encoding="utf-8")


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def snapshot(root: Path) -> dict:
    """The gated content of one copy: approach text and bullet texts by id (counters excluded)."""
    return {"approach": _read(root / APPROACH).strip(),
            "bullets": {b["id"]: b["text"] for b in load_playbook(root / PLAYBOOK)}}


def bootstrap(services) -> bool:
    """Seed the accepted copy from the working copy the first time; True if it did."""
    acc = accepted_dir(services)
    if (acc / APPROACH).exists() or (acc / PLAYBOOK).exists():
        return False
    src = working_dir(services)
    acc.mkdir(parents=True, exist_ok=True)
    for name in (APPROACH, PLAYBOOK):
        if (src / name).exists():
            shutil.copyfile(src / name, acc / name)
    _write_version(services, 0, "seeded from the working copy")
    return True


def _write_version(services, n: int, note: str) -> None:
    p = _version_path(services)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"version": n, "at": datetime.now().astimezone().isoformat(timespec="seconds"),
                             "note": note}))


def diff(services) -> dict:
    """What the working copy would change: {approach_changed, added, removed, changed} (ids)."""
    w, a = snapshot(working_dir(services)), snapshot(accepted_dir(services))
    wb, ab = w["bullets"], a["bullets"]
    return {
        "approach_changed": w["approach"] != a["approach"],
        "added": sorted(set(wb) - set(ab)),
        "removed": sorted(set(ab) - set(wb)),
        "changed": sorted(i for i in set(wb) & set(ab) if wb[i] != ab[i]),
    }


def has_candidate(services) -> bool:
    d = diff(services)
    return bool(d["approach_changed"] or d["added"] or d["removed"] or d["changed"])


def check_limits(root: Path) -> None:
    """Small, delta-sized craft only: long rewrites collapse into mush (ACE, 2025). Raises CraftError."""
    approach = _read(root / APPROACH)
    if len(approach) > MAX_APPROACH_CHARS:
        raise CraftError(f"approach.md is {len(approach)} chars; the limit is {MAX_APPROACH_CHARS}.")
    bullets = load_playbook(root / PLAYBOOK)
    if len(bullets) > MAX_BULLETS:
        raise CraftError(f"playbook has {len(bullets)} bullets; the limit is {MAX_BULLETS}. Merge or drop some.")
    long = [b["id"] for b in bullets if len(b["text"]) > MAX_BULLET_CHARS]
    if long:
        raise CraftError(f"bullets over {MAX_BULLET_CHARS} chars: {', '.join(long)}.")
    ids = [b["id"] for b in bullets]
    if len(ids) != len(set(ids)):
        raise CraftError("playbook has duplicate bullet ids.")


def render_text(approach: str, bullets: list[dict], limit: int = PROMPT_BULLETS) -> str:
    """The craft block a prompt carries: approach, then live bullets best-first."""
    live = [b for b in bullets if b["harmful"] - b["helpful"] <= DROP_MARGIN]
    live.sort(key=lambda b: (b["helpful"] - b["harmful"]), reverse=True)
    parts = []
    if approach.strip():
        parts.append(approach.strip())
    if live:
        parts.append("Playbook (id, helpful/harmful):\n" + "\n".join(
            f"- [{b['id']} +{b['helpful']}/-{b['harmful']}] {b['text']}" for b in live[:limit]))
    return "\n\n".join(parts)


def render(services) -> str:
    """The accepted craft plus the skills on disk, for a sitting's prompt. Empty when there's none."""
    acc = accepted_dir(services)
    body = render_text(_read(acc / APPROACH), load_playbook(acc / PLAYBOOK))
    skills = list_skills(services)
    if skills:
        body = (body + "\n\n" if body else "") + "Skills (craft/skills/):\n" + "\n".join(f"- {s}" for s in skills)
    if not body:
        return ""
    v = version(services).get("version")
    return f"## Your craft (accepted v{v})\n" + body if v is not None else "## Your craft\n" + body


def list_skills(services) -> list[str]:
    root = working_dir(services) / SKILLS
    if not root.is_dir():
        return []
    out = []
    for p in sorted(root.iterdir()):
        if p.name.startswith((".", "_")) or p.name.startswith("test_") or p.name == "README.md":
            continue
        first = ""
        for line in _read(p if p.is_file() else p / "README.md").splitlines():
            line = line.strip().lstrip("#").strip().strip('"').strip()
            if line and not line.startswith("!"):
                first = line[:120]
                break
        out.append(f"{p.name}: {first}" if first else p.name)
    return out[:30]


def feedback(services, bullet_id: str, verdict: str) -> str:
    """Bump a counter on an accepted bullet (mirrored in the working copy so the two stay comparable)."""
    verdict = verdict.strip().lower()
    if verdict not in ("helpful", "harmful"):
        raise CraftError("verdict must be helpful or harmful.")
    bullet_id = bullet_id.strip()
    acc = accepted_dir(services) / PLAYBOOK
    bullets = load_playbook(acc)
    hit = next((b for b in bullets if b["id"] == bullet_id), None)
    if hit is None:
        raise CraftError(f"no accepted bullet {bullet_id!r}.")
    hit[verdict] += 1
    _write_playbook(acc, bullets)
    work = working_dir(services) / PLAYBOOK
    wb = load_playbook(work)
    for b in wb:
        if b["id"] == bullet_id:
            b["helpful"], b["harmful"] = hit["helpful"], hit["harmful"]
    if wb:
        _write_playbook(work, wb)
    return f"{bullet_id}: +{hit['helpful']}/-{hit['harmful']}"


def accept(services, record: dict) -> int:
    """Promote the working copy to accepted (counters kept for unchanged bullets); returns the new version."""
    src, acc = working_dir(services), accepted_dir(services)
    check_limits(src)
    old = {b["id"]: b for b in load_playbook(acc / PLAYBOOK)}
    new = load_playbook(src / PLAYBOOK)
    for b in new:
        prev = old.get(b["id"])
        same = prev is not None and prev["text"] == b["text"]
        b["helpful"], b["harmful"] = (prev["helpful"], prev["harmful"]) if same else (0, 0)
    acc.mkdir(parents=True, exist_ok=True)
    (acc / APPROACH).write_text(_read(src / APPROACH), encoding="utf-8")
    _write_playbook(acc / PLAYBOOK, new)
    n = int(version(services).get("version", 0) or 0) + 1
    _write_version(services, n, "accepted by eval")
    log_lineage(services, {**record, "verdict": "accepted", "version": n})
    return n


def log_lineage(services, record: dict) -> None:
    """Append to the brain's lineage log and mirror it to the public repo (the brain's copy is authoritative)."""
    line = json.dumps({"at": datetime.now().astimezone().isoformat(timespec="seconds"), **record},
                      ensure_ascii=False) + "\n"
    for path in (Path(services.state_dir) / "craft" / "lineage.jsonl", Path(services.repo_dir) / LINEAGE):
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write(line)
        except OSError:
            pass
