import calendar
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from croniter import croniter

SCHEDULE_TYPES = {"once", "daily", "weekly", "monthly", "cron"}
SNOOZE_UNITS = {"minutes", "hours", "days"}


def validate_schedule(schedule_type: str, value: dict) -> None:
    if schedule_type not in SCHEDULE_TYPES:
        raise ValueError(f"Unknown schedule_type: {schedule_type}")

    if schedule_type == "once":
        datetime.fromisoformat(value["datetime"])
    elif schedule_type == "daily":
        _parse_time(value["time"])
    elif schedule_type == "weekly":
        _parse_time(value["time"])
        if not (0 <= int(value["weekday"]) <= 6):
            raise ValueError("weekday must be 0 (Monday) through 6 (Sunday)")
    elif schedule_type == "monthly":
        _parse_time(value["time"])
        if not (1 <= int(value["day"]) <= 31):
            raise ValueError("day must be between 1 and 31")
    elif schedule_type == "cron":
        if not croniter.is_valid(value["expr"]):
            raise ValueError("invalid cron expression")


def _parse_time(value: str) -> tuple[int, int]:
    h, m = value.split(":")
    h, m = int(h), int(m)
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise ValueError("time must be HH:MM")
    return h, m


def _clamp_month_day(year: int, month: int, day: int) -> int:
    last_day = calendar.monthrange(year, month)[1]
    return min(day, last_day)


def compute_next_run(
    schedule_type: str, value: dict, tz_name: str, after: datetime | None = None
) -> datetime | None:
    tz = ZoneInfo(tz_name)
    now_utc = after or datetime.utcnow()
    now_local = now_utc.replace(tzinfo=ZoneInfo("UTC")).astimezone(tz)

    if schedule_type == "once":
        dt_local = datetime.fromisoformat(value["datetime"]).replace(tzinfo=tz)
        if dt_local <= now_local:
            return None
        return dt_local.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)

    if schedule_type == "daily":
        h, m = _parse_time(value["time"])
        candidate = now_local.replace(hour=h, minute=m, second=0, microsecond=0)
        if candidate <= now_local:
            candidate += timedelta(days=1)
        return candidate.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)

    if schedule_type == "weekly":
        h, m = _parse_time(value["time"])
        target_wd = int(value["weekday"])
        candidate = now_local.replace(hour=h, minute=m, second=0, microsecond=0)
        days_ahead = (target_wd - candidate.weekday()) % 7
        candidate += timedelta(days=days_ahead)
        if candidate <= now_local:
            candidate += timedelta(days=7)
        return candidate.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)

    if schedule_type == "monthly":
        h, m = _parse_time(value["time"])
        day = int(value["day"])
        y, mo = now_local.year, now_local.month
        candidate = now_local.replace(
            day=_clamp_month_day(y, mo, day), hour=h, minute=m, second=0, microsecond=0
        )
        if candidate <= now_local:
            mo += 1
            if mo > 12:
                mo = 1
                y += 1
            candidate = now_local.replace(
                year=y, month=mo, day=_clamp_month_day(y, mo, day),
                hour=h, minute=m, second=0, microsecond=0,
            )
        return candidate.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)

    if schedule_type == "cron":
        cron = croniter(value["expr"], now_local)
        nxt = cron.get_next(datetime)
        if nxt.tzinfo is None:
            nxt = nxt.replace(tzinfo=tz)
        return nxt.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)

    raise ValueError(f"Unknown schedule_type: {schedule_type}")


def snooze_target(amount: int, unit: str, tz_name: str) -> tuple[dict, datetime]:
    """Returns (schedule_value for a 'once' reminder, next_run_at in UTC)."""
    if unit not in SNOOZE_UNITS:
        raise ValueError(f"unit must be one of {sorted(SNOOZE_UNITS)}")
    if amount <= 0:
        raise ValueError("amount must be positive")

    next_run_utc = datetime.utcnow() + timedelta(**{unit: amount})
    local_dt = next_run_utc.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo(tz_name))
    schedule_value = {"datetime": local_dt.strftime("%Y-%m-%dT%H:%M")}
    return schedule_value, next_run_utc
