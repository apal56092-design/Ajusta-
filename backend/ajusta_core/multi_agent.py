"""Bounded parallel coordination for explicitly registered AJUSTA departments.

This is a coordinator for trusted, model-backed department adapters. It does not
load generated code, grant tools, or bypass the existing permission/approval layer.
"""
from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError, as_completed
from dataclasses import dataclass
from time import monotonic
from typing import Callable

from .brain import DepartmentRegistry
from .orchestrator import ExecutionPlan
from .models import ModelAuthenticationError, ModelUnavailableError


@dataclass(frozen=True)
class AgentOutcome:
    department: str
    status: str
    output: str | None = None
    error_code: str | None = None


@dataclass(frozen=True)
class MultiAgentReport:
    status: str
    outcomes: tuple[AgentOutcome, ...]
    unavailable_departments: tuple[str, ...]
    elapsed_seconds: float

    @property
    def successful_results(self) -> tuple[tuple[str, str], ...]:
        return tuple(
            (item.department, item.output)
            for item in self.outcomes
            if item.status == "succeeded" and item.output is not None
        )


def coordinate_agents(
    plan: ExecutionPlan,
    registry: DepartmentRegistry,
    *,
    max_parallel_agents: int = 3,
    timeout_seconds: float = 60.0,
    executor_factory: Callable[..., ThreadPoolExecutor] = ThreadPoolExecutor,
) -> MultiAgentReport:
    """Run selected departments concurrently with bounded fan-out and deadline.

    Output order always follows the plan, not completion timing. Each department
    receives only the objective and bounded plan steps. Missing/failed/timed-out
    departments are explicit in the report.
    """
    if not isinstance(registry, DepartmentRegistry):
        raise TypeError("registry must be a DepartmentRegistry")
    if isinstance(max_parallel_agents, bool) or not isinstance(max_parallel_agents, int) or not 1 <= max_parallel_agents <= 6:
        raise ValueError("max_parallel_agents must be between 1 and 6")
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)) or not 0.1 <= timeout_seconds <= 300:
        raise ValueError("timeout_seconds must be between 0.1 and 300")
    if len(plan.departments) > 6:
        raise ValueError("a plan may dispatch at most 6 departments")

    started = monotonic()
    handlers = []
    unavailable = []
    for name in plan.departments:
        handler = registry.get(name)
        if handler is None:
            unavailable.append(name)
        else:
            handlers.append((name, handler))

    if not handlers:
        return MultiAgentReport(
            status="unavailable",
            outcomes=(),
            unavailable_departments=tuple(unavailable),
            elapsed_seconds=monotonic() - started,
        )

    futures: dict[Future, str] = {}
    outcomes: dict[str, AgentOutcome] = {}
    executor = executor_factory(max_workers=min(max_parallel_agents, len(handlers)))
    try:
        for name, handler in handlers:
            futures[executor.submit(handler.execute, plan.objective, plan.steps)] = name
        deadline = started + float(timeout_seconds)
        for future in as_completed(futures, timeout=max(0.0, deadline - monotonic())):
            name = futures[future]
            try:
                output = future.result()
                if not isinstance(output, str) or not output.strip():
                    outcomes[name] = AgentOutcome(name, "failed", error_code="EMPTY_OUTPUT")
                else:
                    outcomes[name] = AgentOutcome(name, "succeeded", output=output.strip())
            except ModelAuthenticationError:
                outcomes[name] = AgentOutcome(name, "failed", error_code="MODEL_AUTHENTICATION_FAILED")
            except ModelUnavailableError:
                outcomes[name] = AgentOutcome(name, "failed", error_code="MODEL_UNAVAILABLE")
            except Exception:
                outcomes[name] = AgentOutcome(name, "failed", error_code="DEPARTMENT_ERROR")
    except TimeoutError:
        pass
    finally:
        for future, name in futures.items():
            if name not in outcomes:
                future.cancel()
                outcomes[name] = AgentOutcome(name, "timed_out", error_code="DEADLINE_EXCEEDED")
        # Running Python threads cannot be safely force-killed. They are daemon-free
        # executor threads; handlers must use provider-side network timeouts.
        executor.shutdown(wait=False, cancel_futures=True)

    ordered = tuple(outcomes[name] for name, _ in handlers)
    success_count = sum(item.status == "succeeded" for item in ordered)
    failure_count = len(ordered) - success_count
    status = "completed" if failure_count == 0 and not unavailable else (
        "partial" if success_count else "failed"
    )
    return MultiAgentReport(
        status=status,
        outcomes=ordered,
        unavailable_departments=tuple(unavailable),
        elapsed_seconds=monotonic() - started,
    )
