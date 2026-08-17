import functools
import logging
import random
import time
from typing import Any, Callable, Tuple, Type

logger = logging.getLogger("gh-pr-agent.retry")


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
) -> Callable:
    """
    Decorator for retrying functions with exponential backoff and optional jitter.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            attempts = 0
            delay = base_delay

            while attempts < max_retries:
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as err:
                    attempts += 1
                    if attempts >= max_retries:
                        logger.error(
                            f"❌ [{func.__name__}] Failed after {attempts}/{max_retries} attempts. Error: {err}"
                        )
                        raise

                    actual_delay = delay
                    if jitter:
                        actual_delay += random.uniform(0, actual_delay * 0.1)

                    logger.warning(
                        f"⚠️ [{func.__name__}] Attempt {attempts}/{max_retries} failed: {err}. Retrying in {actual_delay:.2f}s..."
                    )
                    time.sleep(actual_delay)
                    delay *= backoff_factor

        return wrapper
    return decorator