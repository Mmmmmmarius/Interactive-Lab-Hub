"""Wall-clock schedule for a running ornament; no OS jobs or audio side effects."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone, time
import random
from typing import Callable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class DailySchedule:
    # Scheduler jitter is fine; waking a sleeping computer must not replay a scene.
    MAX_LATENESS_SECONDS = 60

    def __init__(self, settings: dict, clock: Callable[[], datetime] | None = None,
                 rng: random.Random | None = None):
        self.zone_name = settings.get("timezone", "America/New_York")
        try:
            self.zone = ZoneInfo(self.zone_name)
        except ZoneInfoNotFoundError as error:
            raise ValueError(f"Timezone data unavailable for {self.zone_name}; "
                             "daily scheduling needs an existing IANA timezone database") from error
        self.morning = time.fromisoformat(settings.get("morning_time", "10:30"))
        self.quiet = time.fromisoformat(settings.get("quiet_time", "20:00"))
        if self.morning.tzinfo or self.quiet.tzinfo or self.morning >= self.quiet:
            raise ValueError("Daily times must be local, with morning before quiet time")
        self.minimum = settings.get("min_interval_minutes", 30)
        self.maximum = settings.get("max_interval_minutes", 90)
        if (type(self.minimum) is not int or type(self.maximum) is not int
                or not 1 <= self.minimum <= self.maximum <= 1440):
            raise ValueError("Daily intervals must be whole minutes in ascending order")
        self.enabled = settings.get("enabled", True)
        if type(self.enabled) is not bool:
            raise ValueError("Daily enabled must be true or false")
        self.paused = False
        self.busy = False
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.rng = rng or random.Random()
        self.last_now = self.now()
        # Startup never replays the current day's morning scene.
        self.morning_handled = (self.last_now.date() if self.last_now >= self._morning(self.last_now)
                                else self.last_now.date() - timedelta(days=1))
        self.next_chatter: datetime | None = None
        self._plan(self.last_now)

    def now(self) -> datetime:
        value = self.clock()
        if value.tzinfo is None:
            raise ValueError("Schedule clock must return a timezone-aware datetime")
        return value.astimezone(self.zone)

    def _morning(self, now: datetime) -> datetime:
        return datetime.combine(now.date(), self.morning, self.zone)

    def _quiet(self, now: datetime) -> datetime:
        return datetime.combine(now.date(), self.quiet, self.zone)

    def _plan(self, now: datetime) -> None:
        self.next_chatter = None
        if (self.enabled and not self.paused and not self.busy
                and self._morning(now) <= now < self._quiet(now)):
            candidate = now + timedelta(seconds=self.rng.randint(self.minimum * 60, self.maximum * 60))
            if candidate < self._quiet(now):
                self.next_chatter = candidate

    def begin(self) -> None:
        self.busy = True
        self.next_chatter = None

    def complete(self) -> None:
        self.busy = False
        self._plan(self.now())

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        self.last_now = self.now()
        self._plan(self.last_now)

    def set_paused(self, paused: bool) -> None:
        self.paused = paused
        self.last_now = self.now()
        self._plan(self.last_now)

    def poll(self, available: bool = True) -> str | None:
        now = self.now()
        previous = self.last_now
        if now < previous:  # A backward clock correction must not replay events.
            return None
        self.last_now = now
        morning = self._morning(now)
        crossed = previous < morning <= now and now.date() > self.morning_handled
        if crossed:
            self.morning_handled = now.date()
            if (self.enabled and not self.paused and not self.busy and available
                    and now < self._quiet(now)
                    and (now - morning).total_seconds() <= self.MAX_LATENESS_SECONDS):
                self.begin()
                return "morning"
            self._plan(now)  # Busy/paused/missed morning is skipped, not queued.
        elif previous.date() != now.date():
            self._plan(now)
        if not self.enabled or self.paused or self.busy:
            return None
        if not morning <= now < self._quiet(now):
            self.next_chatter = None
            return None
        if self.next_chatter is not None and now >= self.next_chatter:
            if (now - self.next_chatter).total_seconds() > self.MAX_LATENESS_SECONDS:
                self._plan(now)
            elif available:
                self.begin()
                return "chatter"
        return None

    def snapshot(self) -> dict:
        now = self.now()
        next_at, kind = self.next_chatter, "chatter"
        if not self.enabled or self.paused or self.busy:
            next_at, kind = None, None
        elif next_at is None:
            next_at, kind = self._morning(now), "morning"
            if now >= next_at or now.date() <= self.morning_handled:
                next_at += timedelta(days=1)
        return {"enabled": self.enabled, "paused": self.paused, "busy": self.busy,
                "timezone": self.zone_name, "morning_time": self.morning.isoformat(timespec="minutes"),
                "quiet_time": self.quiet.isoformat(timespec="minutes"),
                "min_interval_minutes": self.minimum, "max_interval_minutes": self.maximum,
                "next_at": next_at.isoformat() if next_at else None, "next_kind": kind}
