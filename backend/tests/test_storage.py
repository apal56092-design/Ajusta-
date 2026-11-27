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



def test_task_store_requires_file_backed_database_for_durability():
    with pytest.raises(ValueError, match="file-backed"):
        SQLiteTaskStore(":memory:")


def test_task_store_rejects_result_for_unknown_task(tmp_path):
    store = SQLiteTaskStore(tmp_path / "ajusta.sqlite3")
    result = TaskResult(task_id="unknown", status=TaskStatus.FAILED, error_code="NOT_FOUND")

    with pytest.raises(KeyError, match="does not exist"):
        store.save_result(result)


def test_task_store_lists_recent_tasks_with_owner_isolation_and_limit(tmp_path):
    store = SQLiteTaskStore(tmp_path / "ajusta.sqlite3")
    store.create_task("one-old", TaskRequest("Old request"), user_id="user-one")
    store.save_result(TaskResult("one-old", TaskStatus.SUCCEEDED, result="old result"))
    store.create_task("one-new", TaskRequest("New request"), user_id="user-one")
    store.create_task("two-private", TaskRequest("Other user's request"), user_id="user-two")

    listed = store.list_tasks(user_id="user-one", limit=1)

    assert len(listed) == 1
    assert listed[0].task_id == "one-new"
    assert listed[0].user_id == "user-one"


def test_task_store_lists_service_owned_tasks_separately(tmp_path):
    store = SQLiteTaskStore(tmp_path / "ajusta.sqlite3")
    store.create_task("service-task", TaskRequest("Service request"))
    store.create_task("user-task", TaskRequest("User request"), user_id="user-one")

    listed = store.list_tasks(limit=10)

    assert [item.task_id for item in listed] == ["service-task"]
