import pytz
from datetime import datetime, timedelta
from config.settings import settings

_TZ = pytz.timezone(settings.PRAGUE_TZ)

def now_prague() -> datetime:
    return datetime.now(_TZ)

def midnight_snapshot(dt_prague: datetime) -> datetime:
    # Return 00:00 Prague of the given dt's date
    local = dt_prague.astimezone(_TZ)
    return _TZ.localize(local.replace(hour=0, minute=0, second=0, microsecond=0).replace(tzinfo=None))

def prague_reset_countdown(now: datetime | None = None) -> timedelta:
    n = (now or now_prague()).astimezone(_TZ)
    tomorrow_midnight = _TZ.localize(n.replace(hour=0, minute=0, second=0, microsecond=0).replace(tzinfo=None)) + timedelta(days=1)
    return tomorrow_midnight - n
