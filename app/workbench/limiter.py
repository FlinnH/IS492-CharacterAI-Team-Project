"""Call spacing and the daily cap. Pure: the caller passes in the clock and the time.

Calls start at least 60/N seconds apart, where N is WORKBENCH_CALLS_PER_MINUTE,
across every model and role, so a run stays under the free per-minute limit.
The daily count follows the provider's quota day, which for Gemini ends at
midnight Pacific time (quota_timezone in the models file).
"""

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo


class Limiter:
    def __init__(self, calls_per_minute: int, daily_cap: int, quota_timezone: str) -> None:
        self.calls_per_minute = calls_per_minute
        self.daily_cap = daily_cap
        self.interval = 60.0 / calls_per_minute
        self.zone = ZoneInfo(quota_timezone)
        # The clock reading when the next call may start, or None before the first call.
        self.next_free: float | None = None

    def quota_day(self, when: datetime) -> str:
        """The quota day that a moment falls on, like 2026-10-11."""
        return when.astimezone(self.zone).date().isoformat()

    def hours_left(self, when: datetime) -> int:
        """Whole hours, at least 1, until the quota day ends."""
        local = when.astimezone(self.zone)
        midnight = datetime.combine(local.date() + timedelta(days=1), time(0), tzinfo=self.zone)
        return max(1, round((midnight - local).total_seconds() / 3600))

    def cap_message(self, used: int, when: datetime) -> str | None:
        """None while calls are left today, otherwise what to tell the creator."""
        if used < self.daily_cap:
            return None
        hours = self.hours_left(when)
        return (
            f"Today's {self.daily_cap} model calls are used up. Google's free quota resets at "
            f"midnight Pacific time, in about {hours} {'hour' if hours == 1 else 'hours'}. "
            "To allow more, raise WORKBENCH_DAILY_CALL_CAP in app/.env."
        )

    def reserve(self, now: float) -> float:
        """Books the next start slot and returns the seconds to wait for it.

        now is a monotonic clock reading. A slot booked by a call that is then
        stopped stays booked, which only makes the spacing safer.
        """
        start = now if self.next_free is None else max(now, self.next_free)
        self.next_free = start + self.interval
        return start - now
