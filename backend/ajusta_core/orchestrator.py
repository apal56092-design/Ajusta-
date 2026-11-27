"""Central orchestration boundary joining planning, departments and policy.

This layer plans work only. It does not call AI providers or execute external tools.
"""
from dataclasses import dataclass

from .planner import DEFAULT_DEPARTMENTS, plan_request
from .policy import Action, authorize_action


@dataclass(frozen=True)
class ExecutionPlan:
    """A validated plan routed only to currently enabled departments."""

    objective: str
    departments: tuple[str, ...]
    disabled_departments: tuple[str, ...]
    steps: tuple[str, ...]
    status: str = "planned"
    routing_reasons: tuple[tuple[str, tuple[str, ...]], ...] = ()
    confidence: float = 0.1
    used_fallback: bool = False


def build_execution_plan(
    request: str,
    *,
    enabled_departments: set[str] | frozenset[str],
    action: Action | None = None,
) -> ExecutionPlan:
    """Connect the planner to an enabled department registry and policy gate.

    Missing departments are reported rather than silently treated as available.
    Consequential actions are rejected unless the user has explicitly approved.
    """
    if not enabled_departments:
        raise ValueError("at least one department must be enabled")

    known = {department.name for department in DEFAULT_DEPARTMENTS}
    unknown = set(enabled_departments) - known
    if unknown:
        raise ValueError(f"unknown departments: {', '.join(sorted(unknown))}")

    if action is not None:
        authorize_action(action)

    draft = plan_request(request)
    active = tuple(name for name in draft.departments if name in enabled_departments)
    unavailable = tuple(name for name in draft.departments if name not in enabled_departments)

    return ExecutionPlan(
        objective=draft.objective,
        departments=active,
        disabled_departments=unavailable,
        steps=draft.steps,
        routing_reasons=tuple((name, words) for name, words in draft.routing_reasons if name in active),
        confidence=draft.confidence,
        used_fallback=draft.used_fallback,
    )
