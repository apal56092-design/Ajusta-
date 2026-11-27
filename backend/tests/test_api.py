import pytest
from fastapi.testclient import TestClient

from ajusta_core.api import create_app
from ajusta_core.brain import DepartmentRegistry, register_model_departments
from ajusta_core.models import ModelResponse
from ajusta_core.service import TaskExecutionService
from ajusta_core.storage import SQLiteTaskStore


class DeterministicGateway:
    def generate(self, request):
        department = request.prompt.splitlines()[0].split(": ", 1)[1]
        return ModelResponse(
            provider="test",
            model="deterministic",
            text=f"{department} output",
        )


@pytest.fixture
def client(tmp_path):
    store = SQLiteTaskStore(tmp_path / "api.sqlite3")
    registry = DepartmentRegistry()
    register_model_departments(registry, DeterministicGateway())
    service = TaskExecutionService(
        store=store,
        registry=registry,
        enabled_departments={"research", "coding", "design", "data", "business", "automation"},
    )
    return TestClient(create_app(service, api_token="test-server-token"))


def test_health_endpoint_requires_authentication(client):
    response = client.get("/v1/health")
    assert response.status_code == 401


def test_health_endpoint_accepts_valid_bearer_token(client):
    response = client.get(
        "/v1/health",
        headers={"Authorization": "Bearer test-server-token"},
    )
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "ajusta"}


def test_task_endpoint_executes_and_returns_persisted_result(client):
    headers = {"Authorization": "Bearer test-server-token"}
    response = client.post(
        "/v1/tasks",
        headers=headers,
        json={"task_id": "api-task-1", "instruction": "Build an app"},
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["task_id"] == "api-task-1"
    assert payload["status"] == "succeeded"
    assert "coding output" in payload["result"]


def test_task_endpoint_rejects_invalid_instruction(client):
    response = client.post(
        "/v1/tasks",
        headers={"Authorization": "Bearer test-server-token"},
        json={"task_id": "bad-task", "instruction": "   "},
    )
    assert response.status_code == 422


def test_task_endpoint_rejects_duplicate_task_id(client):
    headers = {"Authorization": "Bearer test-server-token"}
    body = {"task_id": "duplicate", "instruction": "Research clean energy"}
    assert client.post("/v1/tasks", headers=headers, json=body).status_code == 201
    response = client.post("/v1/tasks", headers=headers, json=body)
    assert response.status_code == 409


def test_task_lookup_returns_404_for_unknown_task(client):
    response = client.get(
        "/v1/tasks/not-found",
        headers={"Authorization": "Bearer test-server-token"},
    )
    assert response.status_code == 404


def test_task_lookup_returns_saved_task(client):
    headers = {"Authorization": "Bearer test-server-token"}
    client.post(
        "/v1/tasks",
        headers=headers,
        json={"task_id": "lookup-task", "instruction": "Research clean energy"},
    )
    response = client.get("/v1/tasks/lookup-task", headers=headers)
    assert response.status_code == 200
    assert response.json()["task_id"] == "lookup-task"
    assert response.json()["status"] == "succeeded"


def test_app_refuses_empty_server_token(tmp_path):
    store = SQLiteTaskStore(tmp_path / "empty-token.sqlite3")
    registry = DepartmentRegistry()
    register_model_departments(registry, DeterministicGateway())
    service = TaskExecutionService(
        store=store,
        registry=registry,
        enabled_departments={"research"},
    )
    with pytest.raises(ValueError, match="token"):
        create_app(service, api_token=" ")
