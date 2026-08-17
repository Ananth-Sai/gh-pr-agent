import pytest
from services.retry import retry_with_backoff


def test_retry_eventual_success():
    calls = 0

    @retry_with_backoff(max_retries=3, base_delay=0.01, jitter=False)
    def flaky_task():
        nonlocal calls
        calls += 1
        if calls < 3:
            raise ConnectionError("Temporary connection drop")
        return "success"

    result = flaky_task()
    assert result == "success"
    assert calls == 3


def test_retry_exceeds_max_retries():
    calls = 0

    @retry_with_backoff(max_retries=3, base_delay=0.01, jitter=False)
    def failing_task():
        nonlocal calls
        calls += 1
        raise ValueError("Permanent invalid argument")

    with pytest.raises(ValueError, match="Permanent invalid argument"):
        failing_task()

    assert calls == 3