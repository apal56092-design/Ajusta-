import pytest

from ajusta_core.brain import DepartmentRegistry, register_model_departments
from ajusta_core.contracts import TaskRequest, TaskStatus
from ajusta_core.models import ModelResponse
from ajusta_core.policy import Action
from ajusta_core.service import TaskExecutionService
from ajusta_core.storage import SQLiteTaskStore


class DeterministicGateway:
    def generate(self, request):
        department = request.prompt.splitlines()[0].split(": ", 1)[1]
        return ModelResponse(
            provider="test",
            model="deterministic",
            text=f"{department} output for requested work",
        )


def test_task_service_executes_model_departments_and_persists_result(tmp_path):
    store = SQLiteTaskStore(tmp_path / "tasks.sqlite3")
    registry = DepartmentRegistry()
    register_model_departments(registry, DeterministicGateway())
    service = TaskExecutionService(
        store=store,
        registry=registry,
        enabled_departments={"research", "coding", "design", "data", "business", "automation"},
    )

    result = service.submit(
        "task-success",
        TaskRequest("Build an app and analyze data"),
    )

    assert result.status is TaskStatus.SUCCEEDED
    assert "coding output" in result.result
    assert "data output" in result.result
    assert result.evidence == ("department:coding", "department:data")
    saved = store.get_task("task-success")
    assert saved is not None
    assert saved.status is TaskStatus.SUCCEEDED
    assert saved.result == result.result


def test_task_service_persists_approval_required_without_running_departments(tmp_path):
    store = SQLiteTaskStore(tmp_path / "tasks.sqlite3")
    registry = DepartmentRegistry()
    register_model_departments(registry, DeterministicGateway())
    service = TaskExecutionService(
        store=store,
        registry=registry,
        enabled_departments={"research", "coding", "design", "data", "business", "automation"},
    )

    result = service.submit(
        "task-approval",
        TaskRequest("Publish this content"),
        action=Action("publish_content", consequential=True),
    )

    assert result.status is TaskStatus.NEEDS_APPROVAL
    assert result.error_code == "APPROVAL_REQUIRED"
    assert store.get_task("task-approval").status is TaskStatus.NEEDS_APPROVAL


def test_task_service_marks_disabled_department_as_failed(tmp_path):
    store = SQLiteTaskStore(tmp_path / "tasks.sqlite3")
    registry = DepartmentRegistry()
    service = TaskExecutionService(
        store=store,
        registry=registry,
        enabled_departments={"research"},
    )

    result = service.submit("task-disabled", TaskRequest("Build an app"))

    assert result.status is TaskStatus.FAILED
    assert result.error_code == "DEPARTMENTS_UNAVAILABLE"
    assert "coding" in result.error_message
    assert store.get_task("task-disabled").status is TaskStatus.FAILED


def test_task_service_records_provider_authentication_failure_safely(tmp_path):
    from ajusta_core.models import ModelAuthenticationError

    class BrokenGateway:
        def generate(self, request):
            raise ModelAuthenticationError("sensitive provider detail")

    store = SQLiteTaskStore(tmp_path / "tasks.sqlite3")
    registry = DepartmentRegistry()
    register_model_departments(registry, BrokenGateway())
    service = TaskExecutionService(
        store=store,
        registry=registry,
        enabled_departments={"research", "coding", "design", "data", "business", "automation"},
    )

    result = service.submit("task-auth", TaskRequest("Investigate clean energy"))

    assert result.status is TaskStatus.FAILED
    assert result.error_code == "MODEL_AUTHENTICATION_FAILED"
    assert "sensitive" not in result.error_message


def test_task_service_normalizes_task_id_before_persisting(tmp_path):
    store = SQLiteTaskStore(tmp_path / "tasks.sqlite3")
    registry = DepartmentRegistry()
    register_model_departments(registry, DeterministicGateway())
    service = TaskExecutionService(
        store=store,
        registry=registry,
        enabled_departments={"research", "coding", "design", "data", "business", "automation"},
    )

    result = service.submit("  task-trimmed  ", TaskRequest("Investigate clean energy"))

    assert result.task_id == "task-trimmed"
    assert store.get_task("task-trimmed").status is TaskStatus.SUCCEEDED
