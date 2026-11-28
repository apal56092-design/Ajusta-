from ajusta_core.models import ModelResponse
from ajusta_core.runtime import create_runtime_app
from ajusta_core.skill_store import SQLiteSkillStore


class FakeGateway:
    def generate(self, request):
        department = request.prompt.splitlines()[0].split(": ", 1)[1]
        return ModelResponse(provider="fake", model="runtime-test", text=f"{department} result")


def test_runtime_factory_wires_user_auth_and_task_service(tmp_path):
    app = create_runtime_app(
        database_path=tmp_path / "tasks.sqlite3",
        auth_database_path=tmp_path / "auth.sqlite3",
        gateway=FakeGateway(),
        search_provider=None,
    )
    from fastapi.testclient import TestClient
    client = TestClient(app)
    registered = client.post(
        "/v1/auth/register",
        json={"email": "runtime@example.com", "password": "a-very-long-password"},
    )
    assert registered.status_code == 201
    login = client.post(
        "/v1/auth/login",
        json={"email": "runtime@example.com", "password": "a-very-long-password"},
    )
    assert login.status_code == 200
    headers = {"Authorization": "Bearer " + login.json()["access_token"]}
    task = client.post(
        "/v1/tasks",
        headers=headers,
        json={"task_id": "runtime-task", "instruction": "Build an app"},
    )
    assert task.status_code == 201
    assert task.json()["status"] == "succeeded"
    assert "coding result" in task.json()["result"]
    assert isinstance(app.state.skill_store, SQLiteSkillStore)


def test_runtime_exposes_user_scoped_knowledge_search_as_governed_skill(tmp_path):
    from fastapi.testclient import TestClient

    app = create_runtime_app(
        database_path=tmp_path / "tasks.sqlite3",
        auth_database_path=tmp_path / "auth.sqlite3",
        gateway=FakeGateway(),
        search_provider=None,
    )
    client = TestClient(app)
    client.post("/v1/auth/register", json={
        "email": "knowledge@example.com", "password": "a-very-long-password"
    })
    login = client.post("/v1/auth/login", json={
        "email": "knowledge@example.com", "password": "a-very-long-password"
    })
    headers = {"Authorization": "Bearer " + login.json()["access_token"]}
    user_id = login.json()["user_id"]
    app.state.knowledge_store.create(
        user_id, "AJUSTA architecture", "Central intelligence coordinates specialist departments."
    )

    listed = client.get("/v1/skills", headers=headers)
    assert listed.status_code == 200
    assert any(item["name"] == "knowledge_search" for item in listed.json()["skills"])

    result = client.post(
        "/v1/skills/knowledge_search/1.0.0/execute",
        headers=headers,
        json={"inputs": {"query": "specialist departments"}, "approved_by_user": False},
    )
    assert result.status_code == 200
    assert result.json()["status"] == "succeeded"
    assert result.json()["output"]["items"][0]["title"] == "AJUSTA architecture"


def test_runtime_knowledge_skill_does_not_leak_between_users(tmp_path):
    from fastapi.testclient import TestClient

    app = create_runtime_app(
        database_path=tmp_path / "tasks.sqlite3",
        auth_database_path=tmp_path / "auth.sqlite3",
        gateway=FakeGateway(),
        search_provider=None,
    )
    client = TestClient(app)
    tokens = []
    user_ids = []
    for email in ("one@example.com", "two@example.com"):
        client.post("/v1/auth/register", json={
            "email": email, "password": "a-very-long-password"
        })
        login = client.post("/v1/auth/login", json={
            "email": email, "password": "a-very-long-password"
        }).json()
        tokens.append(login["access_token"])
        user_ids.append(login["user_id"])
    app.state.knowledge_store.create(
        user_ids[0], "Private entry", "secret project phrase belongs to user one"
    )
    response = client.post(
        "/v1/skills/knowledge_search/1.0.0/execute",
        headers={"Authorization": "Bearer " + tokens[1]},
        json={"inputs": {"query": "secret project phrase"}},
    )
    assert response.status_code == 200
    assert response.json()["output"]["items"] == []


class FakeSearchProvider:
    def search(self, query, *, max_results=5):
        from ajusta_core.research import ResearchSource
        return (ResearchSource(
            title="AJUSTA research source",
            url="https://example.org/research",
            content=f"Verified excerpt for {query}",
            score=0.9,
        ),)


def test_runtime_exposes_research_search_only_when_provider_is_configured(tmp_path):
    from fastapi.testclient import TestClient

    app = create_runtime_app(
        database_path=tmp_path / "tasks.sqlite3",
        auth_database_path=tmp_path / "auth.sqlite3",
        gateway=FakeGateway(),
        search_provider=FakeSearchProvider(),
    )
    client = TestClient(app)
    client.post("/v1/auth/register", json={
        "email": "research@example.com", "password": "a-very-long-password"
    })
    login = client.post("/v1/auth/login", json={
        "email": "research@example.com", "password": "a-very-long-password"
    }).json()
    headers = {"Authorization": "Bearer " + login["access_token"]}

    result = client.post(
        "/v1/skills/research_search/1.0.0/execute",
        headers=headers,
        json={"inputs": {"query": "safe AI orchestration"}},
    )
    assert result.status_code == 200
    source = result.json()["output"]["sources"][0]
    assert source["title"] == "AJUSTA research source"
    assert source["url"] == "https://example.org/research"
    assert "safe AI orchestration" in source["content"]


def test_runtime_wires_persistent_training_store_and_empty_trusted_trainer_registry(tmp_path):
    from ajusta_core.training import SQLiteTrainingStore, TrainingEngine

    app = create_runtime_app(
        database_path=tmp_path / "tasks.sqlite3",
        auth_database_path=tmp_path / "auth.sqlite3",
        gateway=FakeGateway(),
        search_provider=None,
    )

    assert isinstance(app.state.training_store, SQLiteTrainingStore)
    assert isinstance(app.state.training_engine, TrainingEngine)
    # Runtime does not silently invent a model trainer; deployments register a
    # reviewed host-side adapter before exposing actual fine-tuning.
