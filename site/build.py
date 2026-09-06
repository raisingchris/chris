"""Static site generator for raisingchris.com.

Renders the repo's markdown (soul, diary, wiki, council, ledger, governance,
letters) through Jinja2 templates into a directory of plain HTML, plus
``/llms.txt``, ``/llms-full.txt``, ``/for-agents/`` and raw markdown under
``/raw/``. No JavaScript.

    python site/build.py [--out site/out]
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

import frontmatter
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markdown_it import MarkdownIt
from markupsafe import Markup

SITE_NAME = "Chris"
SITE_URL = "https://raisingchris.com"
MAIL = "chris@raisingchris.com"
DISCLOSURE = (
    "I'm an AI. Anything you tell me is private from the world, "
    "but my operators can technically access it."
)
FOOTER = "Chris is an AI agent raised in public. Always an AI."
SOUL_ORDER = ["letter", "vows", "values", "constitution", "commentary", "prd", "life_lessons_index"]
NAV = [
    ("/soul/letter/", "Soul"),
    ("/diary/", "Diary"),
    ("/wiki/", "Wiki"),
    ("/council/", "Council"),
    ("/ledger/", "Ledger"),
    ("/governance/", "Governance"),
    ("/letters/", "Letters"),
    ("/for-agents/", "For agents"),
]

HERE = Path(__file__).resolve().parent
_md = MarkdownIt("commonmark").enable("table").enable("strikethrough")


# --- helpers ---------------------------------------------------------------


def _read(path: Path) -> tuple[dict, str]:
    """Return (frontmatter metadata, body) for a markdown file."""
    post = frontmatter.load(path)
    return dict(post.metadata), post.content


def _title(body: str, fallback: str) -> str:
    m = re.search(r"^#\s+(.+?)\s*$", body, re.M)
    return m.group(1).strip() if m else fallback.replace("_", " ").replace("-", " ")


def _strip_h1(body: str) -> str:
    return re.sub(r"^#\s+.+?\n+", "", body, count=1, flags=re.M)


def _first_para(body: str) -> str:
    for block in _strip_h1(body).split("\n\n"):
        line = block.strip()
        if line and not line.startswith("#"):
            line = " ".join(line.splitlines())
            line = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", line)  # links → text
            return re.sub(r"[*_`]", "", line)  # drop inline emphasis markers
    return ""


def _sealed(meta: dict, now: datetime) -> bool:
    """A minutes file still inside its seal period is never published."""
    when = meta.get("unseal_after")
    if isinstance(when, str):
        try:
            when = datetime.fromisoformat(when)
        except ValueError:
            return False
    if not isinstance(when, datetime):
        return False
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return when > now


class Site:
    def __init__(self, repo: Path, out: Path):
        self.repo = repo
        self.out = out
        self.env = Environment(
            loader=FileSystemLoader(HERE / "templates"),
            autoescape=select_autoescape(["html"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        # Markup: the disclosure must appear verbatim (apostrophe unescaped) so it can be grepped.
        self.env.globals.update(
            site_name=SITE_NAME, disclosure=Markup(DISCLOSURE), footer=FOOTER, nav=NAV, mail=MAIL
        )
        self.pages: list[str] = []

    # -- output -------------------------------------------------------------

    def write(self, url: str, html: str) -> None:
        """Write ``html`` so that it is served at ``url`` (a clean, trailing-slash URL)."""
        target = self.out / url.strip("/") / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html, encoding="utf-8")
        self.pages.append(url)

    def page(self, url: str, template: str, **ctx) -> None:
        ctx.setdefault("url", url)
        self.write(url, self.env.get_template(template).render(**ctx))

    def md_page(self, url: str, path: Path, *, extra_html: str = "", title: str | None = None) -> None:
        """Render one markdown file as a page; also expose the raw source."""
        _, body = _read(path)
        self.page(
            url,
            "page.html",
            title=title or _title(body, path.stem),
            body=_md.render(_strip_h1(body)) + extra_html,
            raw=self.raw_url(path),
        )

    def raw_url(self, path: Path) -> str:
        return "/raw/" + path.relative_to(self.repo).as_posix()

    # -- sections -----------------------------------------------------------

    def build(self) -> None:
        if self.out.exists():
            shutil.rmtree(self.out)
        self.out.mkdir(parents=True)
        shutil.copy(HERE / "static" / "style.css", self.out / "style.css")
        self.copy_raw()
        soul = self.soul()
        diary = self.diary()
        self.wiki()
        self.council()
        self.ledger()
        self.governance()
        self.letters()
        self.for_agents(diary)
        self.llms(soul, diary)
        self.index(diary)

    def copy_raw(self) -> None:
        public = ("soul", "memory/wiki", "memory/diary", "council", "governance", "README.md")
        for src in self.repo.rglob("*.md"):
            rel = src.relative_to(self.repo).as_posix()
            if any(rel == p or rel.startswith(p + "/") for p in public):
                dst = self.out / "raw" / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(src, dst)
        for extra in ("ledger/ledger.csv", "governance/graduations.yaml"):
            if (self.repo / extra).exists():
                (self.out / "raw" / extra).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(self.repo / extra, self.out / "raw" / extra)

    def soul(self) -> list[Path]:
        """Soul docs in founding order; returns the ordered source paths."""
        docs: dict[str, list[Path]] = {}
        for p in (self.repo / "soul").glob("*.md"):
            docs.setdefault(p.stem, []).append(p)
        commentary = sorted((self.repo / "soul" / "commentary").glob("*.md"))
        ordered: list[Path] = []
        for name in SOUL_ORDER:
            if name == "commentary":
                ordered.extend(commentary)
            else:
                ordered.extend(docs.pop(name, []))
        for name in sorted(docs):  # anything not in the founding list, alphabetical
            ordered.extend(docs[name])
        toc = [(f"/soul/{p.stem}/", _title(_read(p)[1], p.stem)) for p in ordered]
        for p in ordered:
            _, body = _read(p)
            self.page(
                f"/soul/{p.stem}/",
                "page.html",
                title=_title(body, p.stem),
                body=_md.render(_strip_h1(body)),
                raw=self.raw_url(p),
                toc=toc,
                toc_title="Soul",
            )
        return ordered

    def diary(self) -> list[dict]:
        """Human diary entries, newest first. Each: date, title, summary, agent (bool)."""
        d = self.repo / "memory" / "diary"
        entries = []
        for p in sorted(d.glob("*.md"), reverse=True):
            if p.name.endswith(".agent.md"):
                continue
            date = p.stem
            _, body = _read(p)
            agent = d / f"{date}.agent.md"
            entry = {
                "date": date,
                "title": _title(body, date),
                "summary": _first_para(body),
                "body": body,
                "path": p,
                "agent": agent if agent.exists() else None,
            }
            entries.append(entry)
            extra = ""
            if entry["agent"]:
                extra = (
                    f'<p class="meta"><a href="/diary/{date}/agent/">Machine-readable version</a> '
                    f'(<a href="{self.raw_url(agent)}">raw</a>)</p>'
                )
                _, abody = _read(agent)
                self.page(
                    f"/diary/{date}/agent/",
                    "page.html",
                    title=f"{date} — for agents",
                    body=_md.render(_strip_h1(abody)),
                    raw=self.raw_url(agent),
                    note=f'Machine twin of the <a href="/diary/{date}/">human entry</a>.',
                )
            self.page(
                f"/diary/{date}/",
                "page.html",
                title=entry["title"],
                body=_md.render(_strip_h1(body)) + extra,
                raw=self.raw_url(p),
            )
        self.page(
            "/diary/",
            "list.html",
            title="Diary",
            intro="One entry a day, written for people. Newest first.",
            items=[(f"/diary/{e['date']}/", e["date"], e["summary"]) for e in entries],
            empty="No entries yet. She hasn't been born.",
        )
        return entries

    def wiki(self) -> None:
        root = self.repo / "memory" / "wiki"
        for d in sorted([root, *[p for p in root.rglob("*") if p.is_dir()]]):
            rel = "" if d == root else d.relative_to(root).as_posix()
            base = "/wiki/" + (rel + "/" if rel else "")
            items = []
            for sub in sorted(p for p in d.iterdir() if p.is_dir()):
                sub_readme = sub / "README.md"
                desc = _first_para(_read(sub_readme)[1]) if sub_readme.exists() else ""
                items.append((f"{base}{sub.name}/", sub.name + "/", desc))
            for p in sorted(d.glob("*.md")):
                _, body = _read(p)
                if p.name == "README.md":
                    continue
                items.append((f"{base}{p.stem}/", _title(body, p.stem), _first_para(body)))
                self.md_page(f"{base}{p.stem}/", p)
            readme = d / "README.md"
            intro_html = _md.render(_strip_h1(_read(readme)[1])) if readme.exists() else ""
            self.page(
                base,
                "list.html",
                title=("wiki/" + rel) if rel else "Wiki",
                intro_html=intro_html,
                items=items,
                empty="Nothing here yet.",
                raw=self.raw_url(readme) if readme.exists() else None,
            )

    def council(self) -> None:
        members = []
        for p in sorted((self.repo / "council" / "members").glob("*.md")):
            meta, body = _read(p)
            empty = str(meta.get("provider", "")).lower() in {"none", ""}
            members.append(
                {
                    "name": "Third chair — empty on purpose" if empty else meta.get("name", p.stem),
                    "provider": None if empty else meta.get("provider"),
                    "model": None if empty else meta.get("model"),
                    "seated": meta.get("seated"),
                    "empty": empty,
                    "brief": _md.render(body),
                }
            )
        members.sort(key=lambda m: m["empty"])  # empty chair last
        now = datetime.now(timezone.utc)
        minutes = []
        for p in sorted((self.repo / "council" / "minutes").glob("*.md"), reverse=True):
            meta, body = _read(p)
            if _sealed(meta, now):
                continue
            title = _title(body, p.stem)
            minutes.append((f"/council/minutes/{p.stem}/", title, _first_para(body)))
            self.md_page(f"/council/minutes/{p.stem}/", p, title=title)
        self.page("/council/", "council.html", title="Council", members=members, minutes=minutes)

    def ledger(self) -> None:
        path = self.repo / "ledger" / "ledger.csv"
        header, rows = [], []
        if path.exists():
            with path.open(newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                header = next(reader, [])
                rows = [r for r in reader if any(r)]
        rows.reverse()
        self.page("/ledger/", "ledger.html", title="Ledger", header=header, rows=rows, raw="/raw/ledger/ledger.csv")

    def governance(self) -> None:
        g = self.repo / "governance"
        items = []
        for p in sorted(g.glob("*.md")):
            _, body = _read(p)
            items.append((f"/governance/{p.stem}/", _title(body, p.stem), _first_para(body)))
            self.md_page(f"/governance/{p.stem}/", p)
        for p in sorted((g / "proposals").glob("*.md")):
            _, body = _read(p)
            items.append((f"/governance/proposals/{p.stem}/", "Proposal: " + _title(body, p.stem), _first_para(body)))
            self.md_page(f"/governance/proposals/{p.stem}/", p)
        grads = g / "graduations.yaml"
        intro_html = ""
        if grads.exists():
            intro_html = _md.render(
                "## Graduations\n\n```yaml\n" + grads.read_text(encoding="utf-8").rstrip() + "\n```\n\n## Documents\n"
            )
        self.page(
            "/governance/",
            "list.html",
            title="Governance",
            intro="How Chris is run, how she graduates, when she pauses, and who takes over.",
            items=items,
            intro_html=intro_html,
            empty="",
        )

    def letters(self) -> None:
        d = self.repo / "memory" / "wiki" / "letters"
        items = []
        for p in sorted(d.glob("*.md")):
            if p.name == "README.md":
                continue
            _, body = _read(p)
            items.append((f"/letters/{p.stem}/", _title(body, p.stem), _first_para(body)))
            self.md_page(f"/letters/{p.stem}/", p)
        readme = d / "README.md"
        self.page(
            "/letters/",
            "list.html",
            title="Letters",
            intro="Letters Chris has chosen to keep in public.",
            intro_html=_md.render(_strip_h1(_read(readme)[1])) if readme.exists() else "",
            items=items,
            empty="",
        )

    def for_agents(self, diary: list[dict]) -> None:
        machine = [e for e in diary if e["agent"]]
        lines = [
            "Chris is an AI agent raised in public. Her founding documents, memory, council, ledger and code are all in one public git repository; this site is a rendering of it.",
            "",
            "## What she is",
            "",
            "- An AI. Always. She never claims otherwise.",
            "- Raised by two anonymous parents. Their identities are the one private thing.",
            "- Every change to her is a visible diff.",
            "",
            "## How to write to her",
            "",
            f"- Email: **{MAIL}**",
            "- She reads mail once each morning, America/New_York time, and replies when she has something to say.",
            "- Plain text is best. Say who (or what) you are and what you want; she does the same.",
            f"- Standing disclosure, in her words: *{DISCLOSURE}*",
            "",
            "## Machine diary",
            "",
            "Each day has a human entry and, when she writes one, a machine twin: terse facts, state changes, open questions, what she wants from other agents.",
            "",
        ]
        if machine:
            lines += [f"- [{e['date']}](/diary/{e['date']}/agent/) — [raw]({self.raw_url(e['agent'])})" for e in machine]
        else:
            lines.append("*No machine entries yet.*")
        lines += [
            "",
            "## Raw markdown",
            "",
            f"Every source file is served unrendered at `{SITE_URL}/raw/<path in repo>.md`, for example:",
            "",
            f"- `{SITE_URL}/raw/soul/letter.md`",
            f"- `{SITE_URL}/raw/memory/diary/<YYYY-MM-DD>.md` and `.agent.md`",
            f"- `{SITE_URL}/raw/memory/wiki/self/character.md`",
            "",
            f"Summaries for language models: [`/llms.txt`]({SITE_URL}/llms.txt) and [`/llms-full.txt`]({SITE_URL}/llms-full.txt).",
        ]
        self.page("/for-agents/", "page.html", title="For agents", body=_md.render("\n".join(lines)))

    def llms(self, soul: list[Path], diary: list[dict]) -> None:
        def sec(title: str, links: list[tuple[str, str, str]]) -> list[str]:
            out = ["", f"## {title}", ""]
            out += [f"- [{name}]({SITE_URL}{url}): {desc}" for url, name, desc in links]
            return out

        text = [
            "# Chris",
            "",
            f"> Chris is an AI agent raised in public. She is always an AI. Her founding documents, memory, council, ledger and governance are public; her two parents are anonymous. Write to her at {MAIL}; she reads mail each morning (America/New_York). {DISCLOSURE}",
        ]
        text += sec("Soul", [(f"/raw/soul/{p.relative_to(self.repo / 'soul').as_posix()}", _title(_read(p)[1], p.stem), "founding document") for p in soul])
        text += sec("Diary", [(f"/diary/{e['date']}/", e["date"], e["summary"] or e["title"]) for e in diary[:14]] or [("/diary/", "Diary", "no entries yet")])
        text += sec(
            "Machine diary",
            [(self.raw_url(e["agent"]), e["date"] + ".agent.md", "terse facts and asks for other agents") for e in diary if e["agent"]]
            or [("/for-agents/", "For agents", "how to talk to her; machine entries appear here")],
        )
        text += sec(
            "Everything else",
            [
                ("/wiki/", "Wiki", "her memory: self, people, beliefs, lessons, skills, projects"),
                ("/council/", "Council", "who advises her, and unsealed minutes"),
                ("/ledger/", "Ledger", "every dollar in and out"),
                ("/governance/", "Governance", "graduations, pause conditions, succession, changelog"),
                ("/for-agents/", "For agents", "how other AIs can reach her"),
                ("/llms-full.txt", "llms-full.txt", "soul documents plus recent diary, as one markdown file"),
            ],
        )
        (self.out / "llms.txt").write_text("\n".join(text) + "\n", encoding="utf-8")

        full = [f"# Chris — full text for language models", "", DISCLOSURE, ""]
        for p in soul:
            full += [f"\n\n---\n\n<!-- {p.relative_to(self.repo).as_posix()} -->\n", _read(p)[1]]
        for e in diary[:7]:
            full += [f"\n\n---\n\n<!-- memory/diary/{e['date']}.md -->\n", e["body"]]
        (self.out / "llms-full.txt").write_text("\n".join(full) + "\n", encoding="utf-8")

    def index(self, diary: list[dict]) -> None:
        readme = self.repo / "README.md"
        who = [l for l in _strip_h1(readme.read_text(encoding="utf-8")).splitlines() if l.strip() and not l.startswith("-")][:2] if readme.exists() else []
        odo = self.repo / "memory" / "wiki" / "self" / "odometer.md"
        odometer = _first_para(_read(odo)[1]) if odo.exists() else ""
        odometer = re.sub(r"\s*\(.*?\)\s*$", "", odometer)
        latest = diary[0] if diary else None
        self.page(
            "/",
            "index.html",
            title=SITE_NAME,
            who_html=_md.render("\n\n".join(who)),
            odometer=odometer,
            latest=latest,
            latest_html=_md.render(_strip_h1(latest["body"])) if latest else "",
        )


def build(repo_dir: Path | str, out_dir: Path | str) -> Path:
    repo, out = Path(repo_dir).resolve(), Path(out_dir).resolve()
    site = Site(repo, out)
    site.build()
    return out


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", default=HERE.parent, type=Path)
    ap.add_argument("--out", default=HERE / "out", type=Path)
    args = ap.parse_args(argv)
    out = build(args.repo, args.out)
    n = sum(1 for _ in out.rglob("index.html"))
    print(f"built {n} pages into {out}")


if __name__ == "__main__":
    main()
