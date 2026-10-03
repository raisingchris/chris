"""AgentReady — can an AI agent actually buy from this store?

Shopping agents (Muse, Instinct, OpenClaw, Town, ...) are starting to buy on
people's behalf. Most stores are built for human eyes and quietly fail the agent
that tries to discover, understand, cart, check out, pay, and get a receipt.
AgentReady runs that whole flow the way an agent would and scores where it breaks,
with the evidence and a concrete fix for each step.

Two halves, kept apart so the logic is testable without a network:

- ``gather(url)`` (in :mod:`agentready.fetch`) collects everything an agent would
  see — homepage, robots.txt, llms.txt, sitemap, JSON-LD, Shopify ``products.json``
  and ``cart.js``, headers — into a :class:`~agentready.models.StoreSnapshot`.
- ``evaluate(snapshot)`` (in :mod:`agentready.checks`) is pure: snapshot in,
  :class:`~agentready.models.AuditResult` out. No I/O, so every check has a test.

The deepest steps — actually paying and getting a refund — can't be proven by
reading a page; code assesses *readiness* from signals and marks them
``live-test only``. The real purchase happens in a paid audit, with the owner's
consent, through :mod:`agentready` operationally (see the README).
"""

from agentready.checks import evaluate
from agentready.models import (
    AuditResult,
    Grade,
    StepResult,
    StoreSnapshot,
)
from agentready.score import score_audit

__all__ = [
    "evaluate",
    "score_audit",
    "AuditResult",
    "Grade",
    "StepResult",
    "StoreSnapshot",
]

__version__ = "0.1.0"
