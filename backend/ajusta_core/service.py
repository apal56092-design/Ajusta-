"""Synchronous task execution service with persisted ownership metadata."""
from .brain import DepartmentRegistry
from .multi_agent import coordinate_agents
from .contracts import TaskRequest, TaskResult, TaskStatus
from .models import ModelAuthenticationError, ModelUnavailableError
from .orchestrator import build_execution_plan
from .policy import Action, ApprovalRequired
from .storage import SQLiteTaskStore


class TaskExecutionService:
    """Persist, plan, execute and record one bounded task."""

    def __init__(self, *, store: SQLiteTaskStore, registry: DepartmentRegistry,
                 enabled_departments: set[str] | frozenset[str]) -> None:
        if not callable(getattr(store, "create_task", None)) or not callable(getattr(store, "save_result", None)):
            raise TypeError("store must provide create_task() and save_result()")
        if not isinstance(registry, DepartmentRegistry):
            raise TypeError("registry must be a DepartmentRegistry")
        if not isinstance(enabled_departments, (set, frozenset)) or not enabled_departments:
            raise ValueError("enabled_departments must be a non-empty set")
        self._store = store
        self._registry = registry
        self._enabled_departments = frozenset(enabled_departments)

    @property
    def enabled_departments(self) -> frozenset[str]:
        """Return the immutable department allow-list used by the planner."""
        return self._enabled_departments

    def submit(self, task_id: str, request: TaskRequest, *, action: Action | None = None,
               user_id: str | None = None) -> TaskResult:
        if not isinstance(request, TaskRequest):
            raise TypeError("request must be a TaskRequest")
        if not isinstance(task_id, str) or not task_id.strip():
            raise ValueError("task_id must be a non-empty string")
        task_id = task_id.strip()
        self._store.create_task(task_id, request, user_id=user_id)
        self._store.save_result(TaskResult(task_id, TaskStatus.RUNNING))
        try:
            plan = build_execution_plan(request.instruction, enabled_departments=self._enabled_departments, action=action)
            report = coordinate_agents(plan, self._registry)
            unavailable = tuple(dict.fromkeys(report.unavailable_departments + plan.disabled_departments + tuple(item.department for item in report.outcomes if item.status != "succeeded")))
            department_results = report.successful_results
            if not department_results:
                message = ("No requested department was available: " + ", ".join(unavailable)
                           if unavailable else "No department returned a result.")
                result = TaskResult(task_id=task_id, status=TaskStatus.FAILED,
                    error_code="DEPARTMENTS_UNAVAILABLE", error_message=message,
                    evidence=tuple(f"unavailable:{name}" for name in unavailable))
            else:
                sections = [f"[{name}]\n{output}" for name, output in department_results]
                if unavailable:
                    sections.append("[Unavailable departments]\n" + ", ".join(unavailable))
                evidence = tuple([f"department:{name}" for name, _ in department_results]
                                 + [f"unavailable:{name}" for name in unavailable])
                result = TaskResult(task_id=task_id, status=TaskStatus.SUCCEEDED,
                                    result="\n\n".join(sections), evidence=evidence)
        except ApprovalRequired:
            result = TaskResult(task_id=task_id, status=TaskStatus.NEEDS_APPROVAL,
                error_code="APPROVAL_REQUIRED", error_message="Explicit user approval is required before this action.")
        except ModelAuthenticationError:
            result = TaskResult(task_id=task_id, status=TaskStatus.FAILED,
                error_code="MODEL_AUTHENTICATION_FAILED", error_message="The configured AI provider could not authenticate.")
        except ModelUnavailableError:
            result = TaskResult(task_id=task_id, status=TaskStatus.FAILED,
                error_code="MODEL_UNAVAILABLE", error_message="No configured AI provider is currently available.")
        except Exception:
            result = TaskResult(task_id=task_id, status=TaskStatus.FAILED,
                error_code="EXECUTION_FAILED", error_message="The task could not be completed. Check server diagnostics.")
        self._store.save_result(result)
        return result

    def list_tasks(self, *, user_id: str | None = None, limit: int = 20):
        """List recent persisted tasks for one authenticated owner."""
        return self._store.list_tasks(user_id=user_id, limit=limit)

    def get_task(self, task_id: str, *, user_id: str | None = None):
        if not isinstance(task_id, str) or not task_id.strip():
            raise ValueError("task_id must be a non-empty string")
        return self._store.get_task(task_id.strip(), user_id=user_id)
