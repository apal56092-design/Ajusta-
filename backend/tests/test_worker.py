import time

import pytest

from ajusta_core.durable_queue import SQLiteTaskQueue
from ajusta_core.worker import DurableTaskWorker


def test_worker_processes_one_claimed_task_and_completes_lease(tmp_path):
    queue = SQLiteTaskQueue(tmp_path / "queue.sqlite3")
    queue.enqueue("task-1", "user-1", {"instruction": "safe data"})
    handled = []
    worker = DurableTaskWorker(queue, lambda item: handled.append(item.payload))

    assert worker.run_once() is True
    assert handled == [{"instruction": "safe data"}]
    assert queue.get("task-1", "user-1").status == "succeeded"
    assert worker.run_once() is False


def test_worker_records_handler_failure_without_leaking_exception_text(tmp_path):
    queue = SQLiteTaskQueue(tmp_path / "queue.sqlite3")
    queue.enqueue("task-2", "user-1", {"instruction": "safe data"})

    def fail(_item):
        raise RuntimeError("private token must not be stored")

    worker = DurableTaskWorker(queue, fail)
    assert worker.run_once() is True
    item = queue.get("task-2", "user-1")
    assert item.status == "failed"
    assert "private token" not in str(item)


def test_worker_validates_bounds_and_handler(tmp_path):
    queue = SQLiteTaskQueue(tmp_path / "queue.sqlite3")
    with pytest.raises(ValueError):
        DurableTaskWorker(queue, lambda item: None, poll_interval=0)
    with pytest.raises(ValueError):
        DurableTaskWorker(queue, lambda item: None, lease_seconds=4)
    with pytest.raises(TypeError):
        DurableTaskWorker(queue, None)


def test_worker_start_is_idempotent_and_stop_is_graceful(tmp_path):
    queue = SQLiteTaskQueue(tmp_path / "queue.sqlite3")
    worker = DurableTaskWorker(queue, lambda item: None, poll_interval=0.05)
    worker.start()
    worker.start()
    assert worker.is_running
    assert worker.stop(timeout=2) is True
    assert worker.is_running is False


def test_handler_can_observe_and_cooperatively_stop_after_cancel_request(tmp_path):
    queue = SQLiteTaskQueue(tmp_path / "cooperative.sqlite3")
    queue.enqueue("cooperative-1", "owner-a", {"instruction": "Work"})

    def handler(item, context):
        assert context.cancellation_requested is False
        assert queue.request_cancel(item.task_id, item.owner_id) == "requested"
        context.raise_if_cancelled()

    worker = DurableTaskWorker(queue, handler)
    assert worker.run_once() is True
    item = queue.get("cooperative-1", "owner-a")
    assert item.status == "cancelled"
    assert item.cancel_requested is False
    assert item.progress_message == "Task cancelled cooperatively"
