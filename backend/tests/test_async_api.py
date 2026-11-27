from fastapi.testclient import TestClient

from ajusta_core.api import create_app
from ajusta_core.auth import SQLiteAuthStore
from ajusta_core.brain import DepartmentRegistry, register_model_departments
from ajusta_core.durable_queue import SQLiteTaskQueue
from ajusta_core.models import ModelResponse
from ajusta_core.service import TaskExecutionService
from ajusta_core.storage import SQLiteTaskStore
from ajusta_core.worker import DurableTaskWorker


class Gateway:
    def generate(self, request):
        name = request.prompt.splitlines()[0].split(": ", 1)[1]
        return ModelResponse(provider="test", model="fake", text=f"{name} done")


def setup(tmp_path):
    auth = SQLiteAuthStore(tmp_path / "auth.sqlite3")
    auth.register_user("async@example.com", "long-password-123")
    user = auth.authenticate("async@example.com", "long-password-123")
    token = auth.create_session(user.user_id)
    registry = DepartmentRegistry()
    register_model_departments(registry, Gateway())
    service = TaskExecutionService(
        store=SQLiteTaskStore(tmp_path / "tasks.sqlite3"),
        registry=registry, enabled_departments={"research"},
    )
    queue = SQLiteTaskQueue(tmp_path / "queue.sqlite3")
    worker = DurableTaskWorker(
        queue, lambda item: service.submit(
            item.task_id,
            __import__("ajusta_core.contracts", fromlist=["TaskRequest"]).TaskRequest(
                instruction=item.payload["instruction"],
                constraints=tuple(item.payload["constraints"]),
                output_format=item.payload["output_format"],
            ),
            user_id=item.owner_id,
        ),
    )
    client = TestClient(create_app(
        service, auth_store=auth, task_queue=queue, task_worker=worker,
    ))
    return client, worker, token, user.user_id


def test_async_task_is_queued_then_executed_and_owner_scoped(tmp_path):
    client, worker, token, owner_id = setup(tmp_path)
    headers = {"Authorization": f"Bearer {token}"}
    body = {"task_id": "async-1", "instruction": "Research solar power"}
    queued = client.post("/v1/tasks/async", headers=headers, json=body)
    assert queued.status_code == 202
    assert queued.json() == {"task_id": "async-1", "status": "queued"}

    assert client.get("/v1/tasks/async/async-1", headers=headers).json()["status"] == "queued"
    assert worker.run_once() is True
    finished = client.get("/v1/tasks/async/async-1", headers=headers)
    assert finished.status_code == 200
    assert finished.json()["status"] == "succeeded"
    assert "research done" in finished.json()["result"]


def test_async_task_requires_user_session_and_hides_other_owners(tmp_path):
    client, worker, token, owner_id = setup(tmp_path)
    body = {"task_id": "private-async", "instruction": "Research solar power"}
    assert client.post("/v1/tasks/async", json=body).status_code == 401
    headers = {"Authorization": f"Bearer {token}"}
    assert client.post("/v1/tasks/async", headers=headers, json=body).status_code == 202
    other = client.get("/v1/tasks/async/private-async", headers={
        "Authorization": f"Bearer {client.post('/v1/auth/login', json={'email':'async@example.com','password':'long-password-123'}).json()['access_token']}"
    })
    assert other.status_code == 200


def test_async_cancel_only_cancels_queued_tasks(tmp_path):
    client, worker, token, owner_id = setup(tmp_path)
    headers = {"Authorization": f"Bearer {token}"}
    body = {"task_id": "cancel-1", "instruction": "Research solar power"}
    assert client.post("/v1/tasks/async", headers=headers, json=body).status_code == 202
    cancelled = client.delete("/v1/tasks/async/cancel-1", headers=headers)
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert client.delete("/v1/tasks/async/cancel-1", headers=headers).status_code == 409
