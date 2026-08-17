from unittest.mock import MagicMock
from services.queue import enqueue_task


def sample_worker_function(arg1: str, keyword: str = ""):
    return f"{arg1}:{keyword}"


def test_enqueue_task_fallback_to_background_tasks(monkeypatch):
    import services.queue as queue_mod

    # Force redis availability to False to simulate local dev without Redis
    monkeypatch.setattr(queue_mod, "_redis_available", False)

    mock_bg_tasks = MagicMock()

    dispatched = enqueue_task(
        sample_worker_function,
        "arg1",
        keyword="val1",
        background_tasks=mock_bg_tasks,
    )

    assert dispatched is True
    mock_bg_tasks.add_task.assert_called_once_with(
        sample_worker_function, "arg1", keyword="val1"
    )


def test_enqueue_task_direct_run_without_bg():
    called = False

    def target_action():
        nonlocal called
        called = True

    dispatched = enqueue_task(target_action)
    assert dispatched is True
    assert called is True