"""
Schedule & Sim Life Components

ECS components that give entities Sims-like life:

* ``FurnitureType`` / ``FurnitureComponent`` — marks an entity as furniture
  with a known type and the affordances it offers.
* ``RoomComponent`` — tags an entity with the room it lives in.
* ``NeedsComponent`` — tracks the five core Sim needs (hunger, energy,
  social, fun, hygiene) as floating-point values 0-100.
* ``ScheduleComponent`` — gives a Sim an autonomous daily routine and
  resolves the *current_activity* from the in-game hour.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from .ecs import Component


class FurnitureType(str, Enum):
    """Catalogue of furniture pieces that can appear in the house."""
    BED = "bed"
    FRIDGE = "fridge"
    STOVE = "stove"
    COUNTER = "counter"
    TABLE = "table"
    COUCH = "couch"
    COMPUTER = "computer"
    TOILET = "toilet"
    SHOWER = "shower"


# (hour -> activity) for a standard weekday schedule
_WEEKDAY_SCHEDULE: Dict[int, str] = {
    0: "sleep", 1: "sleep", 2: "sleep", 3: "sleep", 4: "sleep",
    5: "sleep",
    6: "wake_up",
    7: "breakfast", 8: "breakfast",
    9: "work", 10: "work", 11: "work", 12: "work",
    13: "lunch",
    14: "work", 15: "work",
    16: "work", 17: "work",
    18: "dinner", 19: "dinner",
    20: "relax", 21: "relax", 22: "relax", 23: "sleep",
}

# (hour -> activity) for a weekend schedule
_WEEKEND_SCHEDULE: Dict[int, str] = {
    0: "sleep", 1: "sleep", 2: "sleep", 3: "sleep", 4: "sleep",
    5: "sleep",
    6: "wake_up",
    7: "breakfast",
    8: "free_time", 9: "free_time", 10: "free_time",
    11: "breakfast", 12: "free_time",
    13: "lunch", 14: "free_time", 15: "free_time",
    16: "free_time", 17: "free_time",
    18: "dinner", 19: "dinner",
    20: "relax", 21: "relax", 22: "sleep", 23: "sleep",
}


class FurnitureComponent(Component):
    """Tags an entity as a piece of furniture."""

    def __init__(self, furniture_type: FurnitureType):
        self.furniture_type: FurnitureType = furniture_type

    def to_dict(self) -> Dict[str, Any]:
        return {"furniture_type": self.furniture_type.value}


class RoomComponent(Component):
    """Tags an entity with the room name it belongs to."""

    def __init__(self, room_name: str):
        self.room_name: str = room_name

    def to_dict(self) -> Dict[str, Any]:
        return {"room_name": self.room_name}


class NeedType(Enum):
    """The five core Sim needs."""
    HUNGER = "hunger"
    ENERGY = "energy"
    SOCIAL = "social"
    FUN = "fun"
    HYGIENE = "hygiene"


_NEED_NAMES = {e: e.value for e in NeedType}

# How much each need decays per game hour at 1x speed (0-100 range).
_NEED_DECAY_PER_HOUR: Dict[NeedType, float] = {
    NeedType.HUNGER: 0.5,
    NeedType.ENERGY: 0.8,
    NeedType.SOCIAL: 0.2,
    NeedType.FUN: 0.4,
    NeedType.HYGIENE: 0.3,
}

# How much each need recovers when the Sim engages with the matching
# furniture affordance.
_NEED_RECOVERY: Dict[str, Dict[NeedType, float]] = {
    "sleep": {NeedType.ENERGY: 8.0},
    "rest": {NeedType.ENERGY: 4.0},
    "eat": {NeedType.HUNGER: 12.0},
    "cook": {NeedType.HUNGER: 5.0},
    "use": {NeedType.FUN: 2.0},
    "work": {NeedType.FUN: 0.5},
    "sit": {NeedType.FUN: 1.0},
    "relax": {NeedType.FUN: 3.0, NeedType.ENERGY: 2.0},
    "get_food": {NeedType.HUNGER: 10.0},
    "prepare": {NeedType.HUNGER: 4.0},
    "shower": {NeedType.HYGIENE: 15.0},
}


class NeedsComponent(Component):
    """Tracks a Sim's needs as a dict keyed by ``NeedType``."""

    def __init__(self, initial_value: float = 100.0):
        self.needs: Dict[NeedType, float] = {
            need: max(0.0, min(100.0, initial_value)) for need in NeedType
        }

    def decay(self, hours_passed: float) -> None:
        """Decrease needs by *hours_passed* worth of natural decay."""
        for need, rate in _NEED_DECAY_PER_HOUR.items():
            self.needs[need] = max(0.0, self.needs[need] - rate * hours_passed)

    def recover(self, affordance: str) -> None:
        """Recover needs based on the affordance being used."""
        for need, amount in _NEED_RECOVERY.get(affordance, {}).items():
            self.needs[need] = min(100.0, self.needs[need] + amount)

    def as_dict(self) -> Dict[str, float]:
        return {need.value: val for need, val in self.needs.items()}

    def to_dict(self) -> Dict[str, Any]:
        return {"needs": self.as_dict()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NeedsComponent":
        comp = cls()
        raw = data.get("needs", {})
        for key, val in raw.items():
            try:
                need = NeedType(key)
            except ValueError:
                continue
            comp.needs[need] = max(0.0, min(100.0, float(val)))
        return comp


class ScheduleComponent(Component):
    """Gives a Sim an autonomous daily routine.

    The *current_activity* is resolved from the in-game hour and whether
    it is a weekend.  The component also tracks which furniture the Sim
    is currently interacting with (``target_entity_id``) and the progress
    of that interaction (``intent_progress``).
    """

    def __init__(self):
        self.current_activity: Optional[str] = None
        self.target_entity_id: Optional[str] = None
        self.intent_progress: float = 0.0
        self._weekend: bool = False
        self._weekday_schedule: Dict[int, str] = dict(_WEEKDAY_SCHEDULE)
        self._weekend_schedule: Dict[int, str] = dict(_WEEKEND_SCHEDULE)

    @property
    def weekend(self) -> bool:
        return self._weekend

    @weekend.setter
    def weekend(self, value: bool) -> None:
        self._weekend = value

    @property
    def weekday_schedule(self) -> Dict[int, str]:
        return dict(self._weekday_schedule)

    @property
    def weekend_schedule(self) -> Dict[int, str]:
        return dict(self._weekend_schedule)

    def resolve_activity(self, hour: int, is_weekend: bool) -> str:
        """Return the scheduled activity for *hour* on a weekday/weekend."""
        sched = self._weekend_schedule if is_weekend else self._weekday_schedule
        return sched.get(hour, "idle")

    def update_for_time(self, hour: int, is_weekend: bool) -> None:
        """Refresh *current_activity* and *weekend* flag from the clock."""
        self._weekend = is_weekend
        activity = self.resolve_activity(hour, is_weekend)
        if activity != self.current_activity:
            self.current_activity = activity
            self.target_entity_id = None
            self.intent_progress = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_activity": self.current_activity,
            "target_entity_id": self.target_entity_id,
            "intent_progress": self.intent_progress,
            "weekend": self._weekend,
            "weekday_schedule": self._weekday_schedule,
            "weekend_schedule": self._weekend_schedule,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScheduleComponent":
        comp = cls()
        comp.current_activity = data.get("current_activity")
        comp.target_entity_id = data.get("target_entity_id")
        comp.intent_progress = data.get("intent_progress", 0.0)
        comp._weekend = data.get("weekend", False)
        comp._weekday_schedule = dict(data.get("weekday_schedule", _WEEKDAY_SCHEDULE))
        comp._weekend_schedule = dict(data.get("weekend_schedule", _WEEKEND_SCHEDULE))
        return comp
