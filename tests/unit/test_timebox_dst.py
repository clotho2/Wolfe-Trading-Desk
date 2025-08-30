from datetime import datetime
import pytz
from engine.timebox import now_prague, midnight_snapshot, prague_reset_countdown

def test_dst_transitions():
    tz = pytz.timezone("Europe/Prague")
    # Approx DST start last Sunday in March
    spring = tz.localize(datetime(2024, 3, 31, 1, 30, 0))
    snap = midnight_snapshot(spring)
    assert snap.hour == 0 and snap.minute == 0

    # Approx DST end last Sunday in October
    fall = tz.localize(datetime(2024, 10, 27, 1, 30, 0))
    snap2 = midnight_snapshot(fall)
    assert snap2.hour == 0

def test_reset_countdown_positive():
    tz = pytz.timezone("Europe/Prague")
    n = tz.localize(datetime(2024, 5, 1, 12, 0, 0))
    cd = prague_reset_countdown(n)
    assert cd.total_seconds() > 0
