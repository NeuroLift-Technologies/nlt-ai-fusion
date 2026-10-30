"""
Time Manager

Manages the simulation's in-game clock: day-of-week, current hour/minute,
day/night cycle, and the speed multiplier that controls how fast
game time flows relative to real (wall-clock) time.

A speed_multiplier of 1.0 means one real second equals one game minute.
Higher values accelerate game time proportionally.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class TimeManager:
    """Tracks and advances the simulation's in-game time."""

    start_day: int = 1
    start_hour: int = 0
    start_minute: int = 0
    speed_multiplier: float = 1.0

    def __post_init__(self) -> None:
        self._clamp_init_values()
        self._total_minutes_elapsed: int = (
            (self.start_day - 1) * 1440
            + self.start_hour * 60
            + self.start_minute
        )
        self._sync_calendar()

    # -- public state (kept in sync with _total_minutes_elapsed) ---------------

    @property
    def day(self) -> int:
        return self._day

    @property
    def hour(self) -> int:
        return self._hour

    @property
    def minute(self) -> int:
        return self._minute

    @property
    def total_minutes_elapsed(self) -> int:
        return self._total_minutes_elapsed

    @property
    def is_daytime(self) -> bool:
        """True when the in-game hour is between 6 AM and 8 PM (exclusive)."""
        return 6 <= self._hour < 20

    @property
    def day_of_week(self) -> str:
        names = [
            "Monday", "Tuesday", "Wednesday", "Thursday",
            "Friday", "Saturday", "Sunday",
        ]
        return names[(self._day - 1) % 7]

    @property
    def weekend(self) -> bool:
        """True on Saturday (day-of-week index 5) or Sunday (index 6)."""
        return (self._day - 1) % 7 >= 5

    # -- mutation --------------------------------------------------------------

    def advance(self, minutes: float) -> None:
        """Advance the clock by *minutes* game-time minutes."""
        self._total_minutes_elapsed += int(round(minutes))
        self._sync_calendar()

    def set_time(self, hour: int, minute: int) -> None:
        """Set the clock to *hour*:*minute* on the current in-game day."""
        if not (0 <= hour <= 23):
            raise ValueError(f"hour must be in 0-23, got {hour}")
        if not (0 <= minute <= 59):
            raise ValueError(f"minute must be in 0-59, got {minute}")
        days_elapsed = self._total_minutes_elapsed // 1440
        self._total_minutes_elapsed = days_elapsed * 1440 + hour * 60 + minute
        self._sync_calendar()

    def set_speed(self, multiplier: float) -> None:
        """Set the speed multiplier (must be positive)."""
        if multiplier <= 0:
            raise ValueError("speed_multiplier must be positive")
        self.speed_multiplier = multiplier

    # -- serialization --------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "day": self._day,
            "hour": self._hour,
            "minute": self._minute,
            "speed_multiplier": self.speed_multiplier,
            "total_minutes_elapsed": self._total_minutes_elapsed,
            "start_day": self.start_day,
            "start_hour": self.start_hour,
            "start_minute": self.start_minute,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TimeManager":
        tm = cls(
            start_day=data.get("start_day", 1),
            start_hour=data.get("start_hour", 0),
            start_minute=data.get("start_minute", 0),
            speed_multiplier=data.get("speed_multiplier", 1.0),
        )
        tm._total_minutes_elapsed = data.get(
            "total_minutes_elapsed", tm._total_minutes_elapsed
        )
        tm._sync_calendar()
        if "speed_multiplier" in data:
            tm.speed_multiplier = data["speed_multiplier"]
        return tm

    # -- internals -------------------------------------------------------------

    def _clamp_init_values(self) -> None:
        if self.start_day < 1:
            self.start_day = 1
        self.start_hour = max(0, min(23, self.start_hour))
        self.start_minute = max(0, min(59, self.start_minute))

    def _sync_calendar(self) -> None:
        total = self._total_minutes_elapsed
        self._day = total // 1440 + 1
        remainder = total % 1440
        self._hour = remainder // 60
        self._minute = remainder % 60
