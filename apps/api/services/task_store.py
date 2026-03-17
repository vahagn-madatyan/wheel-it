"""In-memory background task store with TTL cleanup.

Tracks screening runs submitted via the API so callers can poll
for status and results without holding an HTTP connection open.
"""

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class TaskStatus(str, Enum):
    """Lifecycle states for a background screening run."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TaskEntry:
    """State for one background screening run."""

    run_id: str
    status: TaskStatus
    run_type: str  # "put_screen" or "call_screen"
    results: Optional[Any] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)


class TaskStore:
    """Thread-safe in-memory store for background task tracking.

    Uses a plain dict — safe under the GIL for single-process FastAPI.
    """

    def __init__(self) -> None:
        self._tasks: dict[str, TaskEntry] = {}

    def submit(self, run_type: str) -> str:
        """Create a new task entry in PENDING state.

        Args:
            run_type: Descriptor like "put_screen" or "call_screen".

        Returns:
            The generated run_id (UUID4 hex).
        """
        run_id = uuid.uuid4().hex
        self._tasks[run_id] = TaskEntry(
            run_id=run_id,
            status=TaskStatus.PENDING,
            run_type=run_type,
        )
        return run_id

    def update(
        self,
        run_id: str,
        status: TaskStatus,
        results: Optional[Any] = None,
        error: Optional[str] = None,
    ) -> None:
        """Update an existing task entry.

        Args:
            run_id: The task to update.
            status: New status.
            results: Screening results (on completion).
            error: Error message (on failure).
        """
        entry = self._tasks.get(run_id)
        if entry is None:
            return
        entry.status = status
        if results is not None:
            entry.results = results
        if error is not None:
            entry.error = error

    def get(self, run_id: str) -> Optional[TaskEntry]:
        """Retrieve a task entry by run_id, or None if not found."""
        return self._tasks.get(run_id)

    def cleanup(self, max_age_seconds: float = 3600) -> int:
        """Remove entries older than max_age_seconds.

        Returns:
            Number of entries removed.
        """
        now = time.time()
        expired = [
            rid
            for rid, entry in self._tasks.items()
            if (now - entry.created_at) > max_age_seconds
        ]
        for rid in expired:
            del self._tasks[rid]
        return len(expired)


async def periodic_cleanup(store: TaskStore, interval: float = 300) -> None:
    """Background coroutine that sweeps expired tasks periodically.

    Args:
        store: The TaskStore to clean.
        interval: Seconds between sweeps (default 5 minutes).
    """
    while True:
        await asyncio.sleep(interval)
        store.cleanup()
