"""Synchronous end-to-end task service joining planning, Brain, policy and storage."""
from .brain import DepartmentRegistry, execute_plan
from .contracts import TaskRequest, TaskResult, TaskStatus
from .models import ModelAuthenticationError, ModelUnavailableError
from .orchestrator import build_execution_plan
from .policy import Action, ApprovalRequired
from .storage import SQLiteTaskStore


class TaskExecutionService:
    """Persist, plan, execute and record one bounded task.

    This is a synchronous first execution path. It does not provide a job queue,
    multi-user authorization, streaming, cancellation, or background retries.
    """

    def __init__(
        self,
        *,
        store: SQLiteTaskStore,
        registry: DepartmentRegistry,
        enabled_departments: set[str] | frozenset[str],
    ) -> None:
        if not callable(getattr(store, "create_task", None)) or not callable(
            getattr(store, "save_result", None)
        ):
            raise TypeError("store must provide create_task() and save_result()")
        if not isinstance(registry, DepartmentRegistry):
            raise TypeError("registry must be a DepartmentRegistry")
        if not isinstance(enabled_departments, (set, frozenset)) or not enabled_departments:
            raise ValueError("enabled_departments must be a non-empty set")
        self._store = store
        self._registry = registry
        self._enabled_departments = frozenset(enabled_departments)

    def submit(
        self,
        task_id: str,
        request: TaskRequest,
        *,
        action: Action | None = None,
    ) -> TaskResult:
        """Run one task and persist its terminal state before returning."""
        if not isinstance(request, TaskRequest):
            raise TypeError("request must be a TaskRequest")
        if not isinstance(task_id, str) or not task_id.strip():
            raise ValueError("task_id must be a non-empty string")
        task_id = task_id.strip()
        self._store.create_task(task_id, request)
        self._store.save_result(TaskResult(task_id, TaskStatus.RUNNING))

        try:
            plan = build_execution_plan(
                request.instruction,
                enabled_departments=self._enabled_departments,
                action=action,
            )
            report = execute_plan(plan, self._registry)
            unavailable = tuple(
                dict.fromkeys(report.unavailable_departments + plan.disabled_departments)
            )
            if not report.department_results:
                message = (
                    "No requested department was available: " + ", ".join(unavailable)
                    if unavailable
                    else "No department returned a result."
                )
                result = TaskResult(
                    task_id=task_id,
                    status=TaskStatus.FAILED,
                    error_code="DEPARTMENTS_UNAVAILABLE",
                    error_message=message,
                    evidence=tuple(f"unavailable:{name}" for name in unavailable),
                )
            else:
                sections = [
                    f"[{name}]\n{output}"
                    for name, output in report.department_results
                ]
                if unavailable:
                    sections.append(
                        "[Unavailable departments]\n" + ", ".join(unavailable)
                    )
                evidence = tuple(
                    [f"department:{name}" for name, _ in report.department_results]
                    + [f"unavailable:{name}" for name in unavailable]
                )
                result = TaskResult(
                    task_id=task_id,
                    status=TaskStatus.SUCCEEDED,
                    result="\n\n".join(sections),
                    evidence=evidence,
                )
        except ApprovalRequired:
            result = TaskResult(
                task_id=task_id,
                status=TaskStatus.NEEDS_APPROVAL,
                error_code="APPROVAL_REQUIRED",
                error_message="Explicit user approval is required before this action.",
            )
        except ModelAuthenticationError:
            result = TaskResult(
                task_id=task_id,
                status=TaskStatus.FAILED,
                error_code="MODEL_AUTHENTICATION_FAILED",
                error_message="The configured AI provider could not authenticate.",
            )
        except ModelUnavailableError:
            result = TaskResult(
                task_id=task_id,
                status=TaskStatus.FAILED,
                error_code="MODEL_UNAVAILABLE",
                error_message="No configured AI provider is currently available.",
            )
        except Exception:
            # Do not expose provider details, credentials, or internal exception text
            # in a user-visible task result.
            result = TaskResult(
                task_id=task_id,
                status=TaskStatus.FAILED,
                error_code="EXECUTION_FAILED",
                error_message="The task could not be completed. Check server diagnostics.",
            )

        self._store.save_result(result)
        return result


    def get_task(self, task_id: str):
        """Return a persisted task snapshot without exposing storage internals."""
        if not isinstance(task_id, str) or not task_id.strip():
            raise ValueError("task_id must be a non-empty string")
        return self._store.get_task(task_id.strip())
