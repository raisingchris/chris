"""Turn seven step verdicts into one 0–100 score and an A–F letter.

The weights say what matters most to an agent completing a purchase. A store can
have beautiful product data (``understand``) and still be unbuyable if checkout
throws a human-only captcha (``authorize``), so the later, harder steps carry more.
The numbers are deliberately plain and live here, in one place, so the score is
reproducible from the step grades alone — never hand-typed (a lesson from Chris's
scoreboard).
"""

from __future__ import annotations

from agentready.models import AuditResult, StepResult

# Weights sum to 100. Later steps weigh more: an agent that can't pay doesn't care
# how clean your JSON-LD is.
WEIGHTS: dict[str, int] = {
    "discover": 12,
    "understand": 18,
    "authenticate": 14,
    "act": 14,
    "authorize": 18,
    "pay": 16,
    "confirm": 8,
}


def _letter(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 60:
        return "C"
    if score >= 40:
        return "D"
    return "F"


def score_steps(steps: list[StepResult]) -> int:
    """Weighted 0–100 from step grades. Unknown counts as half (its grade.points)."""
    total = 0.0
    weight_seen = 0
    for s in steps:
        w = WEIGHTS.get(s.key, 0)
        weight_seen += w
        total += w * s.grade.points
    if weight_seen == 0:
        return 0
    # Normalise by the weight actually present, so a missing step never silently
    # caps the score below 100.
    return round(100 * total / weight_seen)


def score_audit(audit: AuditResult) -> AuditResult:
    """Fill ``audit.score`` and ``audit.grade_letter`` in place; return it for chaining."""
    audit.score = score_steps(audit.steps)
    audit.grade_letter = _letter(audit.score)
    return audit
