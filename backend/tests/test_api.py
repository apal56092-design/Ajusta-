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


def test_skill_catalog_requires_authentication(client):
    response = client.get("/v1/skills")
    assert response.status_code == 401


def test_skill_catalog_returns_only_active_skill_metadata(client, tmp_path):
    from ajusta_core.skills import SkillManifest
    from ajusta_core.skill_store import SQLiteSkillStore

    skill_store = SQLiteSkillStore(tmp_path / "catalog.sqlite3")
    skill_store.register(SkillManifest(
        name="research_digest", version="1.0.0",
        description="Summarize approved sources",
        input_schema={"type": "object"}, output_schema={"type": "object"},
        permissions=("knowledge.read",),
    ))
    skill_store.register(SkillManifest(
        name="draft_tool", version="1.0.0",
        description="A draft skill", input_schema={"type": "object"},
        output_schema={"type": "object"},
    ))
    skill_store.approve("research_digest")
    skill_store.activate("research_digest")

    store = SQLiteTaskStore(tmp_path / "catalog-api.sqlite3")
    registry = DepartmentRegistry()
    register_model_departments(registry, DeterministicGateway())
    service = TaskExecutionService(store=store, registry=registry, enabled_departments={"research"})
    app = create_app(service, api_token="test-server-token", skill_store=skill_store)
    response = TestClient(app).get(
        "/v1/skills", headers={"Authorization": "Bearer test-server-token"}
    )

    assert response.status_code == 200
    assert response.json() == {"skills": [{
        "name": "research_digest", "version": "1.0.0",
        "description": "Summarize approved sources", "permissions": ["knowledge.read"],
    }]}


def test_knowledge_api_requires_user_session(client):
    response = client.get("/v1/knowledge")
    assert response.status_code == 401


def test_knowledge_records_are_private_to_the_authenticated_user(tmp_path):
    from ajusta_core.auth import SQLiteAuthStore
    from ajusta_core.knowledge_store import SQLiteKnowledgeStore

    auth = SQLiteAuthStore(tmp_path / "auth.sqlite3")
    auth.register_user("one@example.com", "long-password-one")
    auth.register_user("two@example.com", "long-password-two")
    token_one = auth.create_session(auth.authenticate("one@example.com", "long-password-one").user_id)
    token_two = auth.create_session(auth.authenticate("two@example.com", "long-password-two").user_id)

    registry = DepartmentRegistry()
    register_model_departments(registry, DeterministicGateway())
    service = TaskExecutionService(
        store=SQLiteTaskStore(tmp_path / "tasks.sqlite3"),
        registry=registry, enabled_departments={"research"},
    )
    app = create_app(service, auth_store=auth, knowledge_store=SQLiteKnowledgeStore(tmp_path / "knowledge.sqlite3"))
    client = TestClient(app)
    one = {"Authorization": f"Bearer {token_one}"}
    two = {"Authorization": f"Bearer {token_two}"}

    created = client.post("/v1/knowledge", headers=one, json={
        "title": "Research notes", "content": "Evidence from reviewed sources"
    })
    assert created.status_code == 201
    record_id = created.json()["id"]
    assert client.get("/v1/knowledge", headers=one).json()["items"][0]["id"] == record_id
    assert client.get("/v1/knowledge", headers=two).json() == {"items": []}
    assert client.delete(f"/v1/knowledge/{record_id}", headers=two).status_code == 404
    assert client.delete(f"/v1/knowledge/{record_id}", headers=one).status_code == 204
    assert client.get("/v1/knowledge", headers=one).json() == {"items": []}


def test_plan_endpoint_returns_explainable_dry_run(client):
    response = client.post(
        "/v1/plan",
        headers={"Authorization": "Bearer test-server-token"},
        json={"instruction": "Research sources and build an Android app"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["departments"] == ["research", "coding"]
    assert payload["routing_reasons"] == [
        {"department": "research", "matched_keywords": ["research", "source"]},
        {"department": "coding", "matched_keywords": ["app"]},
    ]
    assert payload["status"] == "planned"
    assert payload["execution_started"] is False


def test_plan_endpoint_requires_authentication(client):
    response = client.post("/v1/plan", json={"instruction": "Build an app"})
    assert response.status_code == 401


def test_knowledge_search_api_is_authenticated_and_user_scoped(tmp_path):
    from ajusta_core.auth import SQLiteAuthStore
    from ajusta_core.knowledge_store import SQLiteKnowledgeStore

    auth = SQLiteAuthStore(tmp_path / "auth.sqlite3")
    auth.register_user("searcher@example.com", "long-password-one")
    auth.register_user("other@example.com", "long-password-two")
    one = auth.create_session(auth.authenticate("searcher@example.com", "long-password-one").user_id)
    two = auth.create_session(auth.authenticate("other@example.com", "long-password-two").user_id)
    knowledge = SQLiteKnowledgeStore(tmp_path / "knowledge.sqlite3")
    knowledge.create(auth.authenticate("searcher@example.com", "long-password-one").user_id,
                     "Solar energy", "Photovoltaic panels convert sunlight into electricity.")
    knowledge.create(auth.authenticate("other@example.com", "long-password-two").user_id,
                     "Solar notes", "Photovoltaic cells are used in solar panels.")
    registry = DepartmentRegistry()
    register_model_departments(registry, DeterministicGateway())
    service = TaskExecutionService(store=SQLiteTaskStore(tmp_path / "tasks.sqlite3"),
                                   registry=registry, enabled_departments={"research"})
    client = TestClient(create_app(service, auth_store=auth, knowledge_store=knowledge))

    assert client.get("/v1/knowledge/search?q=photovoltaic").status_code == 401
    own = client.get("/v1/knowledge/search?q=photovoltaic",
                     headers={"Authorization": f"Bearer {one}"})
    other = client.get("/v1/knowledge/search?q=photovoltaic",
                       headers={"Authorization": f"Bearer {two}"})
    assert own.status_code == 200 and len(own.json()["items"]) == 1
    assert other.status_code == 200 and len(other.json()["items"]) == 1
