"""Deterministic request planner; no external AI or tools are called here."""
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


DEFAULT_DEPARTMENTS = (
    Department("research", ("research", "source", "evidence", "investigate", "study")),
    Department("coding", ("code", "coding", "debug", "software", "program", "app")),
    Department("design", ("design", "ui", "ux", "prototype", "visual")),
    Department("data", ("data", "analyze", "analysis", "metrics", "dataset")),
    Department("business", ("business", "market", "strategy", "plan")),
    Department("automation", ("automate", "automation", "workflow")),
)


def plan_request(request: str, departments=DEFAULT_DEPARTMENTS) -> TaskPlan:
    """Create a bounded plan from text. Routing is keyword-based and explainable."""
    if not isinstance(request, str):
        raise TypeError("request must be a string")
    objective = re.sub(r"\s+", " ", request).strip()
    if not objective:
        raise ValueError("request must not be empty")
    if len(objective) > 4000:
        raise ValueError("request exceeds the 4000-character limit")

    normalized = objective.casefold()
    selected = tuple(
        dept.name for dept in departments
        if any(re.search(r"(?<!\\w)" + re.escape(word) + r"(?!\\w)", normalized) for word in dept.keywords)
    )
    if not selected:
        selected = ("research",)
    steps = (
        "clarify_objective_and_constraints",
        "route_to_authorized_specialists",
        "collect_and_validate_results",
        "summarize_outcome_and_uncertainty",
    )
    return TaskPlan(objective=objective, departments=selected, steps=steps)
