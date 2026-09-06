"""Chris's council: judgment, not action.

Members live in ``council/members/*.md`` (frontmatter: name, provider, model;
body = the system prompt Chris authors). ``deliberate`` asks every seated
member the same question in parallel, meters the cost against a weekly cap,
writes private minutes, and returns the raw answers. Chris writes her own
synthesis in the sitting — nothing here decides anything for her.

Minutes are private for 30 days; ``unseal_due`` copies the ones past their
date into ``<repo>/council/minutes/`` so the site can publish them.
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

import frontmatter
import yaml

MEMBERS_SUBDIR = Path("council") / "members"
PUBLIC_MINUTES_SUBDIR = Path("council") / "minutes"
UNSEAL_AFTER = timedelta(days=30)

# USD per 1M tokens: (input, output). Estimates only — the meter is a guard, not an invoice.
PRICE_PER_M: dict[str, tuple[float, float]] = {
    "gpt-5": (1.25, 10.0),
}
QWEN_FREE_UNTIL = datetime(2026, 9, 30, 23, 59, 59, tzinfo=timezone.utc)
QWEN_PRICE_PER_M = (1.6, 6.4)
UNKNOWN_PRICE_PER_M = (5.0, 15.0)


class CouncilBudgetExceeded(RuntimeError):
    """Raised before any provider is called when the weekly council cap is spent."""


@dataclass(frozen=True)
class Member:
    name: str
    provider: str  # openai | qwen | none
    model: str
    system_prompt: str
    empty: bool = False
    source: Path | None = None


@dataclass
class Deliberation:
    answers: dict[str, str]
    cost_usd: float
    minutes_path: Path


def load_members(repo_dir: Path) -> list[Member]:
    """Every chair, in filename order. Chairs with ``provider: none`` are flagged empty."""
    members: list[Member] = []
    for path in sorted((repo_dir / MEMBERS_SUBDIR).glob("*.md")):
        post = frontmatter.load(path)
        provider = str(post.get("provider", "none")).strip().lower()
        members.append(
            Member(
                name=str(post.get("name", path.stem)),
                provider=provider,
                model=str(post.get("model", "")),
                system_prompt=post.content.strip(),
                empty=provider == "none",
                source=path,
            )
        )
    return members


def estimate_cost_usd(provider: str, model: str, prompt_tokens: int, completion_tokens: int, at: datetime) -> float:
    if provider == "qwen":
        price = (0.0, 0.0) if at <= QWEN_FREE_UNTIL else QWEN_PRICE_PER_M
    else:
        price = PRICE_PER_M.get(model, UNKNOWN_PRICE_PER_M)
    return (prompt_tokens * price[0] + completion_tokens * price[1]) / 1_000_000


def _slug(text: str, limit: int = 40) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:limit].rstrip("-") or "question"


@dataclass
class Council:
    repo_dir: Path
    minutes_dir: Path
    archive_append: Callable[[str, dict], str]
    meter: Any  # budget.Meter: add_usd(amount, note), spent(), exceeded(cap)
    weekly_cap_usd: float
    openai_api_key: str = ""
    qwen_api_key: str = ""
    qwen_base_url: str = ""
    now: Callable[[], datetime] = field(default=lambda: datetime.now(timezone.utc))
    client_factory: Callable[[str], Any] | None = None

    def __post_init__(self) -> None:
        if self.client_factory is None:
            self.client_factory = self._default_client_factory

    # --- providers -------------------------------------------------------

    def _default_client_factory(self, provider: str):
        from openai import AsyncOpenAI

        if provider == "openai":
            return AsyncOpenAI(api_key=self.openai_api_key)
        if provider == "qwen":
            return AsyncOpenAI(api_key=self.qwen_api_key, base_url=self.qwen_base_url)
        raise ValueError(f"unknown council provider: {provider!r}")

    def members(self) -> list[Member]:
        return load_members(self.repo_dir)

    def seated(self) -> list[Member]:
        return [m for m in self.members() if not m.empty]

    # --- deliberation ----------------------------------------------------

    async def _ask(self, member: Member, user_text: str, at: datetime) -> tuple[str, float]:
        client = self.client_factory(member.provider)  # type: ignore[misc]
        response = await client.chat.completions.create(
            model=member.model,
            messages=[
                {"role": "system", "content": member.system_prompt},
                {"role": "user", "content": user_text},
            ],
        )
        answer = (response.choices[0].message.content or "").strip()
        usage = getattr(response, "usage", None)
        cost = estimate_cost_usd(
            member.provider,
            member.model,
            int(getattr(usage, "prompt_tokens", 0) or 0),
            int(getattr(usage, "completion_tokens", 0) or 0),
            at,
        )
        return answer, cost

    async def deliberate(self, question: str, context: str = "") -> Deliberation:
        if self.meter.exceeded(self.weekly_cap_usd):
            raise CouncilBudgetExceeded(
                f"The council has already spent ${self.meter.spent():.2f} this week; "
                f"the weekly cap is ${self.weekly_cap_usd:.2f}. It sits again next week."
            )
        asked = self.now()
        seated = self.seated()
        user_text = f"{context.strip()}\n\n{question.strip()}" if context.strip() else question.strip()

        results = await asyncio.gather(*(self._ask(m, user_text, asked) for m in seated))
        answers = {m.name: answer for m, (answer, _) in zip(seated, results)}
        cost = round(sum(c for _, c in results), 6)
        self.meter.add_usd(cost, f"council: {question[:60]}")

        minutes_path = self._write_minutes(question, asked, cost, seated, answers)
        self.archive_append(
            "council",
            {"kind": "council", "question": question, "minutes": minutes_path.name, "cost_usd": cost},
        )
        return Deliberation(answers=answers, cost_usd=cost, minutes_path=minutes_path)

    def _write_minutes(
        self, question: str, asked: datetime, cost: float, members: list[Member], answers: dict[str, str]
    ) -> Path:
        self.minutes_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{asked.strftime('%Y%m%dT%H%M')}-{_slug(question)}.md"
        path = self.minutes_dir / filename
        meta = {
            "question": question,
            "asked": asked,
            "unseal_after": asked + UNSEAL_AFTER,
            "cost_usd": cost,
            "members": [m.name for m in members],
        }
        body = "\n\n".join(f"## {m.name} ({m.provider} · {m.model})\n\n{answers[m.name]}" for m in members)
        path.write_text(f"---\n{yaml.safe_dump(meta, sort_keys=False)}---\n\n{body}\n")
        return path

    # --- unsealing -------------------------------------------------------

    def unseal_due(self) -> list[Path]:
        """Copy every minutes file whose ``unseal_after`` has passed into the public repo."""
        now = self.now()
        public = self.repo_dir / PUBLIC_MINUTES_SUBDIR
        copied: list[Path] = []
        for src in sorted(self.minutes_dir.glob("*.md")):
            dst = public / src.name
            if dst.exists():
                continue
            unseal_after = frontmatter.load(src).get("unseal_after")
            if not isinstance(unseal_after, datetime):
                continue
            if unseal_after.tzinfo is None:
                unseal_after = unseal_after.replace(tzinfo=timezone.utc)
            if unseal_after > now:
                continue
            public.mkdir(parents=True, exist_ok=True)
            dst.write_text(src.read_text())
            copied.append(dst)
        return copied

    # --- site ------------------------------------------------------------

    def roster_markdown(self) -> str:
        lines = ["# The council", ""]
        for m in self.members():
            if m.empty:
                lines.append(f"- **{m.name}: empty on purpose.** {m.system_prompt}")
            else:
                lines.append(f"- **{m.name}** — {m.provider} · `{m.model}`")
        lines.append("")
        lines.append("The council deliberates; Chris decides. Minutes unseal after thirty days.")
        return "\n".join(lines) + "\n"
