from __future__ import annotations

from datetime import datetime

LOCAL_TIMEZONE = datetime.now().astimezone().tzinfo


def format_ns(value_ns: int) -> dict[str, object]:
    dt = datetime.fromtimestamp(value_ns / 1_000_000_000, tz=LOCAL_TIMEZONE)
    return {"ns": value_ns, "iso_local": dt.isoformat()}


def parse_time_to_ns(value: str | None) -> int:
    if value is None or value == "now":
        return int(datetime.now(tz=LOCAL_TIMEZONE).timestamp() * 1_000_000_000)

    if value.startswith("@"):
        raw = value[1:]
        if raw.endswith("ns"):
            return int(raw[:-2])
        return int(float(raw) * 1_000_000_000)

    normalized = value.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError:
        dt = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=LOCAL_TIMEZONE)
    return int(dt.timestamp() * 1_000_000_000)
