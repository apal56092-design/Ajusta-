import pytest

from ajusta_core.contracts import TaskRequest, TaskResult, TaskStatus
from ajusta_core.storage import SQLiteTaskStore


def test_task_store_persists_task_across_store_instances(tmp_path):
    database = tmp_path / "ajusta.sqlite3"
    first = SQLiteTaskStore(database)
    first.create_task("task-1", TaskRequest("Research clean energy"))

    second = SQLiteTaskStore(database)
    saved = second.get_task("task-1")

    assert saved is not None
    assert saved.task_id == "task-1"
    assert saved.instruction == "Research clean energy"
    assert saved.status == TaskStatus.QUEUED


def test_task_store_updates_result_and_status(tmp_path):
    store = SQLiteTaskStore(tmp_path / "ajusta.sqlite3")
    store.create_task("task-2", TaskRequest("Summarize this topic"))

    store.save_result(TaskResult(
        task_id="task-2",
        status=TaskStatus.SUCCEEDED,
        result="A concise summary",
        evidence=("source-a",),
    ))

    saved = store.get_task("task-2")
    assert saved is not None
    assert saved.status == TaskStatus.SUCCEEDED
    assert saved.result == "A concise summary"
    assert saved.evidence == ("source-a",)


def test_task_store_rejects_duplicate_task_ids(tmp_path):
    store = SQLiteTaskStore(tmp_path / "ajusta.sqlite3")
    store.create_task("task-3", TaskRequest("First request"))

    with pytest.raises(ValueError, match="already exists"):
        store.create_task("task-3", TaskRequest("Second request"))


def test_task_store_returns_none_for_unknown_task(tmp_path):
    store = SQLiteTaskStore(tmp_path / "ajusta.sqlite3")

    assert store.get_task("missing") is None
