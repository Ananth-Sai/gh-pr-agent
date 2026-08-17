import logging
import os
from typing import Any, Callable
from dotenv import load_dotenv
from fastapi import BackgroundTasks

load_dotenv()
logger = logging.getLogger("gh-pr-agent.queue")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
QUEUE_NAME = "pr-bot-jobs"

_redis_conn = None
_task_queue = None
_redis_available = False

try:
    import redis
    from rq import Queue

    conn = redis.from_url(
        REDIS_URL,
        socket_connect_timeout=1,
        socket_timeout=1,
    )
    conn.ping()
    _redis_conn = conn
    _task_queue = Queue(QUEUE_NAME, connection=_redis_conn)
    _redis_available = True
    logger.info(
        f"✅ Redis persistent queue active on {REDIS_URL} (Queue: '{QUEUE_NAME}')"
    )
except Exception:
    logger.info(
        "ℹ️ Redis not detected. Falling back to FastAPI BackgroundTasks (in-memory mode)."
    )
    _redis_available = False


def is_redis_active() -> bool:
    """Returns True if connected to a live Redis instance."""
    return _redis_available


def enqueue_task(
    func: Callable,
    *args: Any,
    background_tasks: BackgroundTasks | None = None,
    **kwargs: Any,
) -> bool:
    """Dual-mode task dispatcher:

    1. If Redis is alive -> Enqueues durable job into RQ.
    2. If Redis is offline -> Falls back safely to FastAPI in-memory
    BackgroundTasks.
    """
    func_name = getattr(func, "__name__", str(func))

    if _redis_available and _task_queue:
        try:
            job = _task_queue.enqueue(func, *args, **kwargs)
            logger.info(
                f"📦 Task '{func_name}' enqueued to Redis (Job ID: {job.id})"
            )
            return True
        except Exception as e:
            logger.warning(
                f"⚠️ Redis enqueue failed ({e}). Falling back to BackgroundTasks..."
            )

    if background_tasks is not None:
        background_tasks.add_task(func, *args, **kwargs)
        logger.info(
            f"⚡ Task '{func_name}' enqueued in-memory via BackgroundTasks."
        )
        return True

    # Direct execution fallback
    func(*args, **kwargs)
    return True