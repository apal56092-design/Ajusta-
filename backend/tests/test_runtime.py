from ajusta_core.models import ModelResponse
from ajusta_core.runtime import create_runtime_app


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
