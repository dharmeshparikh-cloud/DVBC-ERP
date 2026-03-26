"""
Centralized IST Timezone utility.
GOVERNANCE RULE: All attendance, leaves, and business-hour calculations use IST.
Timestamps stored in DB remain ISO format with timezone info for auditability.
"""

from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))


def now_ist() -> datetime:
    """Get current datetime in IST"""
    return datetime.now(IST)


def today_ist() -> str:
    """Get today's date string (YYYY-MM-DD) in IST"""
    return now_ist().strftime("%Y-%m-%d")


def current_month_ist() -> str:
    """Get current month string (YYYY-MM) in IST"""
    return now_ist().strftime("%Y-%m")


def to_ist(dt: datetime) -> datetime:
    """Convert any datetime to IST. Naive datetimes are assumed IST already."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=IST)
    return dt.astimezone(IST)


def parse_to_ist(time_str: str) -> datetime:
    """Parse ISO datetime string and convert to IST"""
    dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
    return to_ist(dt)
