"""Deterministic, explainable request planner; no external AI or tools are called."""
from dataclasses import dataclass
import re


@dataclass(frozen=True)
class Department:
    name: str
    keywords: tuple[str, ...]


@dataclass(frozen=True)
class TaskPlan:
    objective: str
    departments: tuple[str, ...]
    steps: tuple[str, ...]
    status: str = "planned"
    routing_reasons: tuple[tuple[str, tuple[str, ...]], ...] = ()
    confidence: float = 0.1
    used_fallback: bool = False


DEFAULT_DEPARTMENTS = (
    Department("research", ("research", "source", "evidence", "investigate", "study")),
    Department("coding", ("code", "coding", "debug", "software", "program", "app")),
    Department("design", ("design", "ui", "ux", "prototype", "visual")),
    Department("data", ("data", "analyze", "analysis", "metrics", "dataset")),
    Department("business", ("business", "market", "strategy", "plan")),
    Department("automation", ("automate", "automation", "workflow")),
)


def plan_request(request: str, departments=DEFAULT_DEPARTMENTS) -> TaskPlan:
    """Route using exact keyword boundaries and explain every selected specialist.

    Confidence is a transparent routing heuristic, not a calibrated probability
    that the plan is correct. Unknown requests fall back to research explicitly.
    """
    if not isinstance(request, str):
        raise TypeError("request must be a string")
    objective = " ".join(request.split())
    if not objective:
        raise ValueError("request must not be empty")
    if len(objective) > 4000:
        raise ValueError("request exceeds the 4000-character limit")

    normalized = objective.casefold()
    reasons = []
    for dept in departments:
        matches = tuple(
            word for word in dept.keywords
            if re.search(r"(?<![a-z0-9_])" + re.escape(word) + r"s?(?![a-z0-9_])", normalized)
        )
        if matches:
            reasons.append((dept.name, matches))

    used_fallback = not reasons
    if used_fallback:
        reasons = [("research", ())]
    selected = tuple(name for name, _ in reasons)
    matched_count = sum(len(words) for _, words in reasons)
    confidence = 0.1 if used_fallback else min(0.95, 0.55 + 0.1 * matched_count)
    steps = (
        "clarify_objective_and_constraints",
        "route_to_authorized_specialists",
        "collect_and_validate_results",
        "summarize_outcome_and_uncertainty",
    )
    return TaskPlan(
        objective=objective,
        departments=selected,
        steps=steps,
        routing_reasons=tuple(reasons),
        confidence=round(confidence, 2),
        used_fallback=used_fallback,
    )
