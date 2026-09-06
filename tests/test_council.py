"""Council: parallel deliberation, empty chair, budget cap, private minutes, 30-day unseal."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import frontmatter
import pytest

from agent.council import Council, CouncilBudgetExceeded, Deliberation, load_members

T0 = datetime(2026, 9, 6, 9, 30, tzinfo=timezone.utc)


# --- fakes -----------------------------------------------------------------

class FakeMeter:
    def __init__(self, spent: float = 0.0):
        self._spent = spent
        self.notes: list[str] = []

    def add_usd(self, amount: float, note: str = "") -> None:
        self._spent += amount
        self.notes.append(note)

    def spent(self) -> float:
        return self._spent

    def exceeded(self, cap: float) -> bool:
        return self._spent >= cap


class FakeCompletions:
    """Records concurrency: `max_inflight` proves calls overlapped."""

    def __init__(self, provider: str, reply: str, state: dict):
        self.provider, self.reply, self.state = provider, reply, state
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        self.state["inflight"] += 1
        self.state["max_inflight"] = max(self.state["max_inflight"], self.state["inflight"])
        await asyncio.sleep(0.01)
        self.state["inflight"] -= 1
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.reply))],
            usage=SimpleNamespace(prompt_tokens=1_000_000, completion_tokens=100_000),
        )


def make_factory(state: dict):
    clients: dict[str, object] = {}

    def factory(provider: str):
        completions = FakeCompletions(provider, f"{provider} says: think twice", state)
        client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
        clients[provider] = client
        return client

    factory.clients = clients  # type: ignore[attr-defined]
    return factory


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    members = tmp_path / "repo" / "council" / "members"
    members.mkdir(parents=True)
    src = Path(__file__).resolve().parents[1] / "council" / "members"
    for f in src.glob("*.md"):
        (members / f.name).write_text(f.read_text())
    return tmp_path / "repo"


@pytest.fixture
def minutes_dir(tmp_path: Path) -> Path:
    d = tmp_path / "private" / "council_minutes"
    d.mkdir(parents=True)
    return d


def make_council(repo, minutes_dir, meter=None, now=None, state=None, cap=10.0):
    state = state if state is not None else {"inflight": 0, "max_inflight": 0}
    archived: list[tuple[str, dict]] = []

    def archive_append(kind, payload):
        archived.append((kind, payload))
        return f"archive:2026-09-06#{len(archived)}"

    clock = {"now": now or T0}
    c = Council(
        repo_dir=repo,
        minutes_dir=minutes_dir,
        archive_append=archive_append,
        meter=meter or FakeMeter(),
        weekly_cap_usd=cap,
        openai_api_key="sk-test",
        qwen_api_key="qw-test",
        qwen_base_url="https://qwen.example/v1",
        now=lambda: clock["now"],
        client_factory=make_factory(state),
    )
    c._test_clock = clock  # type: ignore[attr-defined]
    c._test_archived = archived  # type: ignore[attr-defined]
    c._test_state = state  # type: ignore[attr-defined]
    return c


# --- tests -----------------------------------------------------------------

def test_load_members_flags_empty_chair(repo):
    members = load_members(repo)
    by_name = {m.name: m for m in members}
    assert by_name["OpenAI seat"].provider == "openai"
    assert by_name["OpenAI seat"].model == "gpt-5"
    assert by_name["OpenAI seat"].system_prompt.startswith("You are one of Chris's council.")
    assert not by_name["OpenAI seat"].empty
    assert by_name["Qwen seat"].provider == "qwen"
    assert by_name["Third chair"].empty


async def test_two_members_answer_in_parallel_and_empty_chair_skipped(repo, minutes_dir):
    c = make_council(repo, minutes_dir)
    d = await c.deliberate("Should I fill the third chair?", context="Day 1.")
    assert isinstance(d, Deliberation)
    assert set(d.answers) == {"OpenAI seat", "Qwen seat"}  # no Third chair
    assert d.answers["OpenAI seat"] == "openai says: think twice"
    assert c._test_state["max_inflight"] == 2  # both calls in flight at once
    # each member got its own system prompt and the context + question
    openai_call = c.client_factory.clients["openai"].chat.completions.calls[0]
    assert openai_call["model"] == "gpt-5"
    assert openai_call["messages"][0]["role"] == "system"
    assert "Think differently" in openai_call["messages"][0]["content"]
    assert openai_call["messages"][1]["content"] == "Day 1.\n\nShould I fill the third chair?"
    # cost: gpt-5 = 1M in ($1.25) + 100k out ($1.00) = 2.25; qwen free before 2026-09-30
    assert d.cost_usd == pytest.approx(2.25)
    assert c.meter.spent() == pytest.approx(2.25)
    # archived once, with minutes filename not path
    kinds = [k for k, _ in c._test_archived]
    assert kinds == ["council"]
    payload = c._test_archived[0][1]
    assert payload["question"] == "Should I fill the third chair?"
    assert payload["minutes"] == d.minutes_path.name
    assert payload["cost_usd"] == pytest.approx(2.25)


async def test_qwen_priced_after_free_period(repo, minutes_dir):
    c = make_council(repo, minutes_dir, now=datetime(2026, 10, 1, tzinfo=timezone.utc))
    d = await c.deliberate("q")
    # qwen: 1M in ($1.6) + 100k out ($0.64) = 2.24, plus gpt-5 2.25
    assert d.cost_usd == pytest.approx(4.49)


async def test_budget_refusal_when_exceeded(repo, minutes_dir):
    meter = FakeMeter(spent=10.5)
    c = make_council(repo, minutes_dir, meter=meter)
    with pytest.raises(CouncilBudgetExceeded) as ei:
        await c.deliberate("anything")
    msg = str(ei.value)
    assert "10.50" in msg and "10.00" in msg
    assert c.client_factory.clients == {}  # no provider was even constructed
    assert c._test_archived == []
    assert list(minutes_dir.iterdir()) == []


async def test_minutes_written_privately_not_in_repo(repo, minutes_dir):
    c = make_council(repo, minutes_dir)
    d = await c.deliberate("Where do minutes go?")
    assert d.minutes_path.parent == minutes_dir
    assert d.minutes_path.name == "20260906T0930-where-do-minutes-go.md"
    assert not d.minutes_path.is_relative_to(repo)
    assert not (repo / "council" / "minutes").exists()
    post = frontmatter.load(d.minutes_path)
    assert post["question"] == "Where do minutes go?"
    assert post["asked"] == T0
    assert post["unseal_after"] == T0 + timedelta(days=30)
    assert post["cost_usd"] == pytest.approx(2.25)
    assert post["members"] == ["OpenAI seat", "Qwen seat"]
    assert "## OpenAI seat" in post.content
    assert "openai says: think twice" in post.content
    assert "qwen says: think twice" in post.content


async def test_unseal_only_after_30_days(repo, minutes_dir):
    c = make_council(repo, minutes_dir)
    d = await c.deliberate("Unseal me")
    public = repo / "council" / "minutes"

    assert c.unseal_due() == []
    c._test_clock["now"] = T0 + timedelta(days=29, hours=23)
    assert c.unseal_due() == []
    assert not (public / d.minutes_path.name).exists()

    c._test_clock["now"] = T0 + timedelta(days=30)
    copied = c.unseal_due()
    assert copied == [public / d.minutes_path.name]
    assert (public / d.minutes_path.name).read_text() == d.minutes_path.read_text()

    # idempotent: already-copied files are not returned again
    assert c.unseal_due() == []
    # private original remains
    assert d.minutes_path.exists()


def test_roster_markdown_lists_seats_and_empty_chair(repo, minutes_dir):
    c = make_council(repo, minutes_dir)
    md = c.roster_markdown()
    assert "OpenAI seat" in md and "gpt-5" in md
    assert "Qwen seat" in md
    assert "Third chair: empty on purpose" in md
