"""Central AJUSTA brain: dispatch plans to explicitly registered departments.

Handlers are trusted application components. This module does not execute skill code,
load plugins dynamically, or connect external AI providers.
"""
from dataclasses import dataclass
from typing import Protocol

from .orchestrator import ExecutionPlan


class DepartmentHandler(Protocol):
    """Contract implemented by a reviewed department adapter."""

    name: str

    def execute(self, objective: str, steps: tuple[str, ...]) -> str:
        """Perform the department's bounded task and return a textual result."""


@dataclass(frozen=True)
class BrainExecutionReport:
    status: str
    department_results: tuple[tuple[str, str], ...]
    unavailable_departments: tuple[str, ...]


class DepartmentRegistry:
    """Explicit allow-list of department handlers; no implicit discovery."""

    def __init__(self) -> None:
        self._handlers: dict[str, DepartmentHandler] = {}

    def register(self, handler: DepartmentHandler) -> None:
        name = getattr(handler, "name", None)
        if not isinstance(name, str) or not name.strip():
            raise ValueError("department handler must have a non-empty name")
        normalized = name.strip().casefold()
        if normalized in self._handlers:
            raise ValueError(f"department {normalized!r} is already registered")
        if not callable(getattr(handler, "execute", None)):
            raise ValueError("department handler must provide execute()")
        self._handlers[normalized] = handler

    def get(self, name: str) -> DepartmentHandler | None:
        return self._handlers.get(name.casefold())


def execute_plan(
    plan: ExecutionPlan,
    registry: DepartmentRegistry,
) -> BrainExecutionReport:
    """Execute a planned task through registered handlers only.

    Missing handlers are reported. Handler exceptions intentionally propagate to the
    caller so the API/task boundary can record a failure without masking it.
    """
    results: list[tuple[str, str]] = []
    unavailable: list[str] = []

    for name in plan.departments:
        handler = registry.get(name)
        if handler is None:
            unavailable.append(name)
            continue
        output = handler.execute(plan.objective, plan.steps)
        if not isinstance(output, str) or not output.strip():
            raise ValueError(f"department {name!r} must return a non-empty string")
        results.append((name, output.strip()))

    status = "completed" if not unavailable else "partial"
    if not results and unavailable:
        status = "unavailable"
    return BrainExecutionReport(
        status=status,
        department_results=tuple(results),
        unavailable_departments=tuple(unavailable),
    )
