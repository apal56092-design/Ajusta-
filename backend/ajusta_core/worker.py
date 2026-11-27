"""Bounded worker runtime with cooperative cancellation and lease heartbeats."""
from __future__ import annotations

import inspect
import logging
import threading
from typing import Callable
from uuid import uuid4

from .durable_queue import QueueItem, SQLiteTaskQueue

_LOG = logging.getLogger(__name__)


class TaskCancelledError(Exception):
    """Raised by a trusted handler after observing a cancellation request."""


class TaskExecutionContext:
    """Lease-bound callbacks a trusted handler may poll during long operations."""

    def __init__(self, queue: SQLiteTaskQueue, item: QueueItem) -> None:
        self._queue = queue
        self._item = item

    @property
    def cancellation_requested(self) -> bool:
        return self._queue.is_cancel_requested(self._item.task_id, self._item.lease_token)

    def raise_if_cancelled(self) -> None:
        if self.cancellation_requested:
            raise TaskCancelledError("Task cancellation was requested")

    def report_progress(self, percent: int, message: str) -> bool:
        return self._queue.report_progress(
            self._item.task_id, self._item.lease_token, percent, message
        )


class DurableTaskWorker:
    """One bounded polling worker with renewable leases and cooperative cancellation."""

    def __init__(
        self,
        queue: SQLiteTaskQueue,
        handler: Callable[..., object],
        *,
        poll_interval: float = 0.25,
        lease_seconds: int = 300,
        worker_id: str | None = None,
    ) -> None:
        if not isinstance(queue, SQLiteTaskQueue):
            raise TypeError("queue must be an SQLiteTaskQueue")
        if not callable(handler):
            raise TypeError("handler must be callable")
        if not isinstance(poll_interval, (int, float)) or isinstance(poll_interval, bool) or not 0.05 <= poll_interval <= 30:
            raise ValueError("poll_interval must be between 0.05 and 30 seconds")
        if not isinstance(lease_seconds, int) or isinstance(lease_seconds, bool) or not 5 <= lease_seconds <= 3600:
            raise ValueError("lease_seconds must be between 5 and 3600")
        self._queue = queue
        self._handler = handler
        self._handler_accepts_context = self._accepts_context(handler)
        self._poll_interval = float(poll_interval)
        self._lease_seconds = lease_seconds
        self._worker_id = worker_id or "worker-" + uuid4().hex
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._lifecycle_lock = threading.Lock()

    @staticmethod
    def _accepts_context(handler: Callable[..., object]) -> bool:
        try:
            signature = inspect.signature(handler)
        except (TypeError, ValueError):
            return False
        parameters = list(signature.parameters.values())
        return any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in parameters) or len(parameters) >= 2

    @property
    def is_running(self) -> bool:
        thread = self._thread
        return thread is not None and thread.is_alive()

    def _invoke(self, item: QueueItem, context: TaskExecutionContext) -> object:
        if self._handler_accepts_context:
            return self._handler(item, context)
        return self._handler(item)

    def run_once(self) -> bool:
        """Claim and process at most one item; suitable for deterministic tests."""
        item = self._queue.claim_next(self._worker_id, lease_seconds=self._lease_seconds)
        if item is None:
            return False
        context = TaskExecutionContext(self._queue, item)
        heartbeat_stop = threading.Event()

        def heartbeat() -> None:
            interval = max(1.0, self._lease_seconds / 3)
            while not heartbeat_stop.wait(interval):
                if not self._queue.renew_lease(
                    item.task_id, item.lease_token, lease_seconds=self._lease_seconds
                ):
                    return

        heartbeat_thread = threading.Thread(
            target=heartbeat, name=f"{self._worker_id}-lease", daemon=True
        )
        heartbeat_thread.start()
        try:
            self._queue.report_progress(
                item.task_id, item.lease_token, 10, "Task dispatched to trusted handler"
            )
            self._invoke(item, context)
            context.raise_if_cancelled()
            self._queue.report_progress(
                item.task_id, item.lease_token, 95, "Handler returned; saving result"
            )
        except TaskCancelledError:
            self._queue.complete(item.task_id, item.lease_token, succeeded=False, cancelled=True)
        except Exception as exc:
            _LOG.exception("AJUSTA task handler failed for task %s", item.task_id)
            self._queue.complete(
                item.task_id, item.lease_token, succeeded=False,
                error=f"Trusted task handler failed: {type(exc).__name__}",
            )
        else:
            self._queue.complete(item.task_id, item.lease_token, succeeded=True)
        finally:
            heartbeat_stop.set()
            heartbeat_thread.join(timeout=1.0)
        return True

    def start(self) -> None:
        """Start exactly one daemon polling thread; repeated starts are idempotent."""
        with self._lifecycle_lock:
            if self.is_running:
                return
            self._stop.clear()
            self._thread = threading.Thread(
                target=self._run, name=self._worker_id, daemon=True
            )
            self._thread.start()

    def stop(self, *, timeout: float = 5.0) -> bool:
        """Request graceful stop; handlers must poll their execution context to cancel."""
        if not isinstance(timeout, (int, float)) or isinstance(timeout, bool) or not 0 <= timeout <= 60:
            raise ValueError("timeout must be between 0 and 60 seconds")
        self._stop.set()
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=float(timeout))
        return not self.is_running

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                worked = self.run_once()
            except Exception:
                _LOG.exception("AJUSTA queue polling failed")
                worked = False
            if not worked:
                self._stop.wait(self._poll_interval)
