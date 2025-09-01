# path: tests/utils/test_backoff.py
from shared.utils.backoff import plan_retries


def test_backoff_deterministic():
    a = plan_retries(100, 5000, 200, 5, seed=123)
    b = plan_retries(100, 5000, 200, 5, seed=123)
    assert a == b
    assert all(0 <= x <= 5000 for x in a)
