import pytest

from ajusta_core.durable_queue import SQLiteTaskQueue


def test_queue_claims_in_order_and_requires_matching_lease_to_complete(tmp_path):
    queue = SQLiteTaskQueue(tmp_path / "queue.sqlite3")
    queued = queue.enqueue("task-1", "user-1", {"instruction": "Research"})
    assert queued.status == "queued"

    claimed = queue.claim_next("worker-a", lease_seconds=30)
    assert claimed.task_id == "task-1"
    assert claimed.status == "running"
    assert claimed.attempts == 1
    assert queue.complete("task-1", "wrong-token", succeeded=True) is False
    assert queue.complete("task-1", claimed.lease_token, succeeded=True) is True
    assert queue.get("task-1", "user-1").status == "succeeded"


def test_queue_is_owner_scoped_and_rejects_duplicate_ids(tmp_path):
    queue = SQLiteTaskQueue(tmp_path / "queue.sqlite3")
    queue.enqueue("private-task", "owner-a", {"instruction": "private"})
    assert queue.get("private-task", "owner-b") is None
    with pytest.raises(ValueError, match="already exists"):
        queue.enqueue("private-task", "owner-b", {"instruction": "other"})


def test_expired_worker_lease_is_requeued_and_attempt_count_increments(tmp_path):
    queue = SQLiteTaskQueue(tmp_path / "queue.sqlite3", max_attempts=2)
    queue.enqueue("recover-task", "owner-a", {"instruction": "Recover"})
    first = queue.claim_next("worker-a", lease_seconds=5)
    with queue._connect() as db:
        db.execute("UPDATE task_queue SET lease_until=0 WHERE task_id='recover-task'")
    second = queue.claim_next("worker-b", lease_seconds=30)
    assert second.task_id == first.task_id
    assert second.attempts == 2
    with queue._connect() as db:
        db.execute("UPDATE task_queue SET lease_until=0 WHERE task_id='recover-task'")
    assert queue.claim_next("worker-c") is None
    assert queue.get("recover-task", "owner-a").status == "failed"


def test_only_queued_tasks_can_be_cancelled_by_their_owner(tmp_path):
    queue = SQLiteTaskQueue(tmp_path / "queue.sqlite3")
    queue.enqueue("cancel-task", "owner-a", {"instruction": "Cancel me"})
    assert queue.cancel("cancel-task", "owner-b") is False
    assert queue.cancel("cancel-task", "owner-a") is True
    assert queue.get("cancel-task", "owner-a").status == "cancelled"


def test_queue_bounds_payload_and_lease_parameters(tmp_path):
    queue = SQLiteTaskQueue(tmp_path / "queue.sqlite3")
    with pytest.raises(ValueError):
        queue.claim_next("worker", lease_seconds=1)
    with pytest.raises(ValueError):
        queue.enqueue("large", "owner", {"data": "x" * 21000})
