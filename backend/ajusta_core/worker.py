"""Bounded lifecycle wrapper for trusted handlers consuming the durable queue.

Handlers must be registered application code. Queue payloads are data, never code.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Callable
from uuid import uuid4

from .durable_queue import QueueItem, SQLiteTaskQueue

_LOG = logging.getLogger(__name__)


class DurableTaskWorker:
    """One bounded polling worker with explicit start/stop and lease-safe completion."""

    def __init__(
        self,
        queue: SQLiteTaskQueue,
        handler: Callable[[QueueItem], object],
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
        self._poll_interval = float(poll_interval)
        self._lease_seconds = lease_seconds
        self._worker_id = worker_id or "worker-" + uuid4().hex
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._lifecycle_lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        thread = self._thread
        return thread is not None and thread.is_alive()

    def run_once(self) -> bool:
        """Claim and process at most one item; useful for deterministic operations/tests."""
        item = self._queue.claim_next(self._worker_id, lease_seconds=self._lease_seconds)
        if item is None:
            return False
        try:
            self._queue.report_progress(
                item.task_id, item.lease_token, 10, "Task dispatched to trusted handler"
            )
            self._handler(item)
            self._queue.report_progress(
                item.task_id, item.lease_token, 95, "Handler returned; saving result"
            )
        except Exception as exc:
            _LOG.exception("AJUSTA task handler failed for task %s", item.task_id)
            self._queue.complete(
                item.task_id, item.lease_token, succeeded=False,
                error=f"Trusted task handler failed: {type(exc).__name__}",
            )
        else:
            self._queue.complete(item.task_id, item.lease_token, succeeded=True)
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
        """Request graceful stop and wait at most timeout seconds for current handler."""
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
