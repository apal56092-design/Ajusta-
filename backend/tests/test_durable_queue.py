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


def test_progress_events_are_owner_scoped_monotonic_and_lease_protected(tmp_path):
    queue = SQLiteTaskQueue(tmp_path / "progress.sqlite3")
    queue.enqueue("progress-1", "owner-a", {"instruction": "Do work"})
    claimed = queue.claim_next("worker-a", lease_seconds=30)

    assert queue.report_progress("progress-1", "wrong-lease", 20, "forged") is False
    assert queue.report_progress("progress-1", claimed.lease_token, 40, "Researching") is True
    assert queue.report_progress("progress-1", claimed.lease_token, 30, "Going backwards") is False
    assert queue.get("progress-1", "owner-a").progress_percent == 40
    assert queue.get("progress-1", "owner-b") is None
    assert queue.list_events("progress-1", "owner-b") == []
    events = queue.list_events("progress-1", "owner-a")
    assert [event["progress_percent"] for event in events] == [0, 5, 40]
    assert events[-1]["message"] == "Researching"


def test_successful_completion_records_one_hundred_percent(tmp_path):
    queue = SQLiteTaskQueue(tmp_path / "complete.sqlite3")
    queue.enqueue("done-1", "owner-a", {"instruction": "Do work"})
    claimed = queue.claim_next("worker-a", lease_seconds=30)
    assert queue.complete("done-1", claimed.lease_token, succeeded=True) is True
    item = queue.get("done-1", "owner-a")
    assert item.status == "succeeded"
    assert item.progress_percent == 100
    assert queue.list_events("done-1", "owner-a")[-1]["message"] == "Task completed"


def test_running_task_cancellation_is_a_request_and_owner_scoped(tmp_path):
    queue = SQLiteTaskQueue(tmp_path / "running-cancel.sqlite3")
    queue.enqueue("running-1", "owner-a", {"instruction": "Work"})
    claimed = queue.claim_next("worker", lease_seconds=30)

    assert queue.request_cancel("running-1", "owner-b") == "not_found"
    assert queue.request_cancel("running-1", "owner-a") == "requested"
    assert queue.is_cancel_requested("running-1", claimed.lease_token) is True
    assert queue.get("running-1", "owner-a").status == "running"


def test_lease_can_be_renewed_only_by_current_worker_token(tmp_path):
    queue = SQLiteTaskQueue(tmp_path / "renew.sqlite3")
    queue.enqueue("renew-1", "owner-a", {"instruction": "Work"})
    claimed = queue.claim_next("worker", lease_seconds=5)

    assert queue.renew_lease("renew-1", "wrong-token", lease_seconds=30) is False
    assert queue.renew_lease("renew-1", claimed.lease_token, lease_seconds=30) is True
    renewed = queue.get("renew-1", "owner-a")
    assert renewed.lease_until > claimed.lease_until
