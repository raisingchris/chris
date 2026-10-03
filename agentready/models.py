"""Data types shared across AgentReady.

Everything here is plain data. The network layer fills a :class:`StoreSnapshot`;
the pure evaluator turns it into an :class:`AuditResult`. Keeping them as simple
dataclasses (no methods that reach out) is what lets the checks be tested with a
hand-written snapshot and no sockets.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any


class Grade(enum.Enum):
    """How an agent fared on one step. Ordered worst→best for sorting and colour."""

    FAIL = "fail"      # an agent cannot get through this step
    PARTIAL = "partial"  # an agent can, but only with effort a real one may not make
    PASS = "pass"      # an agent sails through
    UNKNOWN = "unknown"  # can't tell from what's readable; needs a live test

    @property
    def points(self) -> float:
        return {"fail": 0.0, "partial": 0.5, "pass": 1.0, "unknown": 0.5}[self.value]

    @property
    def emoji(self) -> str:
        return {"fail": "🔴", "partial": "🟡", "pass": "🟢", "unknown": "⚪"}[self.value]


# The seven steps of the agent-commerce flow, in order. The key is stable (used in
# JSON and tests); the title is what a store owner reads.
STEPS: list[tuple[str, str]] = [
    ("discover", "Discover — can an agent find and read your store?"),
    ("understand", "Understand — can it read your catalogue, prices, and stock?"),
    ("authenticate", "Authenticate — can it start a cart without a human-only login?"),
    ("act", "Act — can it add to the cart and hold that state?"),
    ("authorize", "Authorize — can it reach checkout without a human-only wall?"),
    ("pay", "Pay — is the payment step one an agent can complete?"),
    ("confirm", "Confirm — is the receipt machine-readable, and does refund work?"),
]
STEP_TITLES: dict[str, str] = dict(STEPS)
STEP_KEYS: list[str] = [k for k, _ in STEPS]


@dataclass
class StepResult:
    """One step's verdict, with the evidence behind it and the fix for the owner."""

    key: str
    grade: Grade
    summary: str                      # one plain line: what an agent hits here
    evidence: list[str] = field(default_factory=list)  # concrete, checkable facts
    fixes: list[str] = field(default_factory=list)     # what to change, specific
    live_test_only: bool = False      # True when only a real purchase can confirm it

    @property
    def title(self) -> str:
        return STEP_TITLES.get(self.key, self.key)

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "title": self.title,
            "grade": self.grade.value,
            "summary": self.summary,
            "evidence": list(self.evidence),
            "fixes": list(self.fixes),
            "live_test_only": self.live_test_only,
        }


@dataclass
class StoreSnapshot:
    """Everything an agent can see of a store, gathered once.

    Filled by :func:`agentready.fetch.gather`. In tests it is built by hand. Every
    field has a safe empty default so a partial gather (a site that timed out
    halfway) still evaluates instead of crashing.
    """

    url: str
    final_url: str = ""               # after redirects
    reachable: bool = True
    status_code: int | None = None
    homepage_html: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    robots_txt: str | None = None     # None = not fetched / not present
    llms_txt: str | None = None
    sitemap_xml: str | None = None
    jsonld: list[dict[str, Any]] = field(default_factory=list)  # parsed JSON-LD blocks
    # Shopify-specific (None = not applicable / not found)
    is_shopify: bool = False
    products_json: dict[str, Any] | None = None   # parsed /products.json
    cart_js: dict[str, Any] | None = None         # parsed /cart.js
    # Signals pulled out of the homepage/headers during gather, so checks stay pure.
    signals: dict[str, Any] = field(default_factory=dict)
    gather_notes: list[str] = field(default_factory=list)  # anything odd during fetch

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "final_url": self.final_url,
            "reachable": self.reachable,
            "status_code": self.status_code,
            "is_shopify": self.is_shopify,
            "has_robots": self.robots_txt is not None,
            "has_llms": self.llms_txt is not None,
            "has_sitemap": self.sitemap_xml is not None,
            "jsonld_blocks": len(self.jsonld),
            "has_products_json": self.products_json is not None,
            "signals": dict(self.signals),
            "gather_notes": list(self.gather_notes),
        }


@dataclass
class AuditResult:
    """The whole audit: the store, the seven step verdicts, and the headline score."""

    url: str
    snapshot: StoreSnapshot
    steps: list[StepResult]
    score: int = 0                    # 0–100, filled by score_audit
    grade_letter: str = ""            # A–F, filled by score_audit
    audited_at: str = ""              # ISO date, set by the caller

    def step(self, key: str) -> StepResult | None:
        return next((s for s in self.steps if s.key == key), None)

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "score": self.score,
            "grade_letter": self.grade_letter,
            "audited_at": self.audited_at,
            "steps": [s.to_dict() for s in self.steps],
            "snapshot": self.snapshot.to_dict(),
        }
