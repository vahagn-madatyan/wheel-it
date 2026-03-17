"""Tests for TaskStore submit/update/get/cleanup."""

import time

from apps.api.services.task_store import TaskEntry, TaskStatus, TaskStore


def test_submit_returns_run_id():
    store = TaskStore()
    run_id = store.submit("put_screen")
    assert isinstance(run_id, str)
    assert len(run_id) == 32  # uuid4 hex


def test_submit_creates_pending_entry():
    store = TaskStore()
    run_id = store.submit("put_screen")
    entry = store.get(run_id)
    assert entry is not None
    assert entry.status == TaskStatus.PENDING
    assert entry.run_type == "put_screen"
    assert entry.results is None
    assert entry.error is None


def test_get_unknown_returns_none():
    store = TaskStore()
    assert store.get("nonexistent") is None


def test_update_status_and_results():
    store = TaskStore()
    run_id = store.submit("call_screen")
    store.update(run_id, TaskStatus.RUNNING)
    assert store.get(run_id).status == TaskStatus.RUNNING

    results = [{"symbol": "AAPL250418P00200000"}]
    store.update(run_id, TaskStatus.COMPLETED, results=results)
    entry = store.get(run_id)
    assert entry.status == TaskStatus.COMPLETED
    assert entry.results == results


def test_update_with_error():
    store = TaskStore()
    run_id = store.submit("put_screen")
    store.update(run_id, TaskStatus.FAILED, error="API timeout")
    entry = store.get(run_id)
    assert entry.status == TaskStatus.FAILED
    assert entry.error == "API timeout"


def test_update_unknown_run_id_is_noop():
    store = TaskStore()
    store.update("ghost", TaskStatus.FAILED, error="boom")
    assert store.get("ghost") is None


def test_cleanup_removes_old_entries():
    store = TaskStore()
    run_id = store.submit("put_screen")
    # Backdate the entry
    store._tasks[run_id].created_at = time.time() - 7200  # 2 hours ago
    removed = store.cleanup(max_age_seconds=3600)
    assert removed == 1
    assert store.get(run_id) is None


def test_cleanup_preserves_recent_entries():
    store = TaskStore()
    run_id = store.submit("put_screen")
    removed = store.cleanup(max_age_seconds=3600)
    assert removed == 0
    assert store.get(run_id) is not None


def test_multiple_tasks_independent():
    store = TaskStore()
    id1 = store.submit("put_screen")
    id2 = store.submit("call_screen")
    store.update(id1, TaskStatus.COMPLETED, results=[])
    store.update(id2, TaskStatus.FAILED, error="bad")
    assert store.get(id1).status == TaskStatus.COMPLETED
    assert store.get(id2).status == TaskStatus.FAILED
