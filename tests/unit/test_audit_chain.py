from ops.audit.immutable_audit import append_event, validate_day
from datetime import datetime, timezone

def test_append_and_validate():
    append_event({"evt": "TEST_EVENT", "payload": {"k": 1}})
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    assert validate_day(day) is True
