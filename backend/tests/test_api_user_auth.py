import pytest
from fastapi.testclient import TestClient

from ajusta_core.api import create_app
from ajusta_core.auth import SQLiteAuthStore
from ajusta_core.brain import DepartmentRegistry, register_model_departments
from ajusta_core.models import ModelResponse
from ajusta_core.knowledge_store import SQLiteKnowledgeStore
from ajusta_core.service import TaskExecutionService
from ajusta_core.storage import SQLiteTaskStore


class TestGateway:
    def generate(self, request):
        department = request.prompt.splitlines()[0].split(": ", 1)[1]
        return ModelResponse(provider="test", model="deterministic", text=f"{department} output")


@pytest.fixture
def client(tmp_path):
    store = SQLiteTaskStore(tmp_path / "tasks.sqlite3")
    auth = SQLiteAuthStore(tmp_path / "auth.sqlite3")
    registry = DepartmentRegistry()
    register_model_departments(registry, TestGateway())
    service = TaskExecutionService(
        store=store,
        registry=registry,
        enabled_departments={"research", "coding", "design", "data", "business", "automation"},
    )
    knowledge = SQLiteKnowledgeStore(tmp_path / "knowledge.sqlite3")
    return TestClient(create_app(service, auth_store=auth, knowledge_store=knowledge))


def register(client, email):
    return client.post("/v1/auth/register", json={"email": email, "password": "a-very-long-password"})


def login(client, email):
    response = client.post("/v1/auth/login", json={"email": email, "password": "a-very-long-password"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_register_login_and_current_user(client):
    response = register(client, "first@example.com")
    assert response.status_code == 201
    headers = login(client, "first@example.com")
    current = client.get("/v1/auth/me", headers=headers)
    assert current.status_code == 200
    assert current.json()["email"] == "first@example.com"


def test_user_task_isolation(client):
    register(client, "first@example.com")
    register(client, "second@example.com")
    first_headers = login(client, "first@example.com")
    second_headers = login(client, "second@example.com")
    created = client.post(
        "/v1/tasks", headers=first_headers,
        json={"task_id": "private-task", "instruction": "Research clean energy"},
    )
    assert created.status_code == 201
    hidden = client.get("/v1/tasks/private-task", headers=second_headers)
    assert hidden.status_code == 404


def test_logout_revokes_session(client):
    register(client, "first@example.com")
    headers = login(client, "first@example.com")
    assert client.post("/v1/auth/logout", headers=headers).status_code == 200
    assert client.get("/v1/auth/me", headers=headers).status_code == 401


def test_invalid_login_is_rejected(client):
    register(client, "first@example.com")
    response = client.post(
        "/v1/auth/login",
        json={"email": "first@example.com", "password": "wrong-password"},
    )
    assert response.status_code == 401


def test_registration_validation(client):
    response = client.post(
        "/v1/auth/register",
        json={"email": "not-email", "password": "short"},
    )
    assert response.status_code == 422



def test_knowledge_api_persists_and_returns_provenance_for_owner(client):
    register(client, "first@example.com")
    headers = login(client, "first@example.com")
    created = client.post(
        "/v1/knowledge",
        headers=headers,
        json={
            "title": "Solar panel note",
            "content": "The cited report estimates 22 percent efficiency.",
            "source": "https://example.org/report",
            "confidence": 0.72,
        },
    )

    assert created.status_code == 201
    assert created.json()["source"] == "https://example.org/report"
    assert created.json()["confidence"] == 0.72

    listed = client.get("/v1/knowledge", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["items"][0]["source"] == "https://example.org/report"


def test_knowledge_api_rejects_out_of_range_confidence(client):
    register(client, "first@example.com")
    headers = login(client, "first@example.com")
    response = client.post(
        "/v1/knowledge",
        headers=headers,
        json={"title": "Note", "content": "Content", "confidence": 1.5},
    )

    assert response.status_code == 422
