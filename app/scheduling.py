from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class ScheduleParseError(Exception):
    pass


def _parse_field(field: str, min_value: int, max_value: int) -> set[int]:
    text = field.strip()
    if text == "*":
        return set(range(min_value, max_value + 1))

    values: set[int] = set()
    for chunk in text.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if not chunk.isdigit():
            raise ScheduleParseError(f"Unsupported cron token: {chunk}")
        value = int(chunk)
        if value < min_value or value > max_value:
            raise ScheduleParseError(f"Out-of-range cron value: {value}")
        values.add(value)

    if not values:
        raise ScheduleParseError("Empty cron field")
    return values


def parse_simple_weekly_cron(schedule_cron: str) -> tuple[set[int], set[int], set[int]]:
    parts = schedule_cron.split()
    if len(parts) != 5:
        raise ScheduleParseError("Cron must have 5 fields")

    minute = _parse_field(parts[0], 0, 59)
    hour = _parse_field(parts[1], 0, 23)
    if parts[2] != "*" or parts[3] != "*":
        raise ScheduleParseError("Only daily/monthly wildcards are supported")
    dow = _parse_field(parts[4], 0, 6)
    return minute, hour, dow


def _python_weekday_to_cron(python_weekday: int) -> int:
    # Python weekday: Monday=0...Sunday=6
    # Cron mapping expected by this project: Sunday=0...Saturday=6
    return (python_weekday + 1) % 7


def next_run_times(schedule_cron: str, timezone_name: str, count: int = 5) -> list[str]:
    minute_set, hour_set, dow_set = parse_simple_weekly_cron(schedule_cron)
    try:
        tz = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as error:
        raise ScheduleParseError(f"Invalid timezone: {timezone_name}") from error

    now = datetime.now(tz).replace(second=0, microsecond=0)
    cursor = now + timedelta(minutes=1)
    horizon = cursor + timedelta(days=30)

    results: list[str] = []
    while cursor <= horizon and len(results) < count:
        cron_dow = _python_weekday_to_cron(cursor.weekday())
        if cursor.minute in minute_set and cursor.hour in hour_set and cron_dow in dow_set:
            results.append(cursor.isoformat())
        cursor += timedelta(minutes=1)

    return results


def episodes_per_week_hint(schedule_cron: str) -> int | None:
    _, _, dow_set = parse_simple_weekly_cron(schedule_cron)
    return len(dow_set)
