# path: tests/events/test_event_schema.py
from shared.events.schema import is_allowed


def test_reason_codes_known():
    assert is_allowed("CORR_BLOCK")
    assert is_allowed("PARTIAL_FILL")
    assert not is_allowed("MADE_UP_CODE")
