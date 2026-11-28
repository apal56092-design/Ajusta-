from fastapi.testclient import TestClient

from ajusta_core.api import create_app
from ajusta_core.auth import SQLiteAuthStore
from ajusta_core.brain import DepartmentRegistry, register_model_departments
from ajusta_core.models import ModelResponse
from ajusta_core.service import TaskExecutionService
from ajusta_core.storage import SQLiteTaskStore
from ajusta_core.training import SQLiteTrainingStore, TrainingEngine


class Gateway:
    def generate(self, request):
        department = request.prompt.splitlines()[0].split(": ", 1)[1]
        return ModelResponse(provider="test", model="test", text=f"{department} result")


def _client(tmp_path):
    auth = SQLiteAuthStore(tmp_path / "auth.sqlite3")
    registry = DepartmentRegistry()
    register_model_departments(registry, Gateway())
    service = TaskExecutionService(
        store=SQLiteTaskStore(tmp_path / "tasks.sqlite3"),
        registry=registry,
        enabled_departments={"research", "coding", "design", "data", "business", "automation"},
    )
    training = SQLiteTrainingStore(tmp_path / "training.sqlite3")
    engine = TrainingEngine(training)
    engine.register_trainer("test_trainer", lambda examples, config: {
        "examples_seen": len(examples), "loss": 0.1
    })
    client = TestClient(create_app(
        service, auth_store=auth, training_store=training, training_engine=engine
    ))
    return client


def _auth(client, email):
    client.post("/v1/auth/register", json={
        "email": email, "password": "a-very-long-password"
    })
    login = client.post("/v1/auth/login", json={
        "email": email, "password": "a-very-long-password"
    }).json()
    return {"Authorization": "Bearer " + login["access_token"]}


def test_training_api_creates_private_dataset_and_runs_only_after_approval(tmp_path):
    client = _client(tmp_path)
    headers = _auth(client, "trainer@example.com")
    created = client.post("/v1/training/datasets", headers=headers, json={
        "name": "Reviewed set", "description": "Curated supervised examples"
    })
    assert created.status_code == 201
    dataset_id = created.json()["id"]

    for question, answer in (("2+2?", "4"), ("3+3?", "6")):
        response = client.post(
            f"/v1/training/datasets/{dataset_id}/examples",
            headers=headers,
            json={"input": question, "target": answer, "source": "human-reviewed"},
        )
        assert response.status_code == 201

    blocked = client.post("/v1/training/runs", headers=headers, json={
        "dataset_id": dataset_id, "trainer_name": "test_trainer", "approved_by_user": False
    })
    assert blocked.status_code == 403

    started = client.post("/v1/training/runs", headers=headers, json={
        "dataset_id": dataset_id, "trainer_name": "test_trainer",
        "config": {"epochs": 1}, "approved_by_user": True
    })
    assert started.status_code == 201
    assert started.json()["status"] == "completed"
    assert started.json()["metrics"]["examples_seen"] == 2


def test_training_api_isolates_datasets_between_users(tmp_path):
    client = _client(tmp_path)
    first = _auth(client, "first@example.com")
    second = _auth(client, "second@example.com")
    dataset = client.post("/v1/training/datasets", headers=first, json={
        "name": "Private dataset"
    }).json()

    response = client.post(
        f"/v1/training/datasets/{dataset['id']}/examples",
        headers=second,
        json={"input": "private input", "target": "private target"},
    )
    assert response.status_code == 404
