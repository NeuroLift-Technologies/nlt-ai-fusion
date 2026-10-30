"""
Pydantic schemas for the World-state router.

Request models for time control, save/load, and response models for
serializing WorldEngine entities, Sims, rooms, and full world snapshots.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Time speed
# ---------------------------------------------------------------------------


class TimeSpeed(str, Enum):
    """Preset speed multipliers for the simulation."""

    REALTIME = "realtime"
    FAST = "fast"
    ULTRA = "ultra"
    HYPER = "hyper"


TIME_SPEED_MULTIPLIERS: Dict[str, float] = {
    "realtime": 1.0,
    "fast": 5.0,
    "ultra": 20.0,
    "hyper": 100.0,
}


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class TimeAdvanceRequest(BaseModel):
    """Body for POST /world/time/advance."""

    minutes: int = Field(..., ge=0, description="Number of minutes to advance")


class TimeSetRequest(BaseModel):
    """Body for POST /world/time/set."""

    hour: int = Field(..., ge=0, le=23, description="Hour (0-23)")
    minute: int = Field(0, ge=0, le=59, description="Minute (0-59)")


class TimeSpeedRequest(BaseModel):
    """Body for POST /world/time/speed."""

    speed: str = Field(
        ...,
        description="Time speed: 'realtime', 'fast', 'ultra', or 'hyper'",
    )


class SaveRequest(BaseModel):
    """Body for POST /world/save."""

    filename: str = Field(
        ...,
        min_length=1,
        description="Save file name (without extension)",
    )


class LoadRequest(BaseModel):
    """Body for POST /world/load."""

    filename: str = Field(
        ...,
        min_length=1,
        description="Save file name to load (without extension)",
    )


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class TimeStateResponse(BaseModel):
    """Current simulation time state."""

    day: int
    hour: int
    minute: int
    is_daytime: bool
    day_of_week: str
    weekend: bool
    total_minutes_elapsed: int
    speed_multiplier: float
    speed_label: str


class PositionResponse(BaseModel):
    x: int
    y: int
    z: int


class SimSummaryResponse(BaseModel):
    """Lightweight Sim info for the /world/sims listing."""

    sim_id: str
    name: str
    position: PositionResponse
    room: str
    current_activity: str
    needs_summary: Dict[str, float]


class SimDetailResponse(BaseModel):
    """Detailed Sim info for GET /world/sims/{sim_id}."""

    sim_id: str
    name: str
    position: PositionResponse
    room: str
    current_activity: str
    needs: Dict[str, float]
    mood: str
    weekend: bool
    relationships: List[Dict[str, Any]]
    schedule: Dict[str, Any]


class FurnitureResponse(BaseModel):
    entity_id: str
    furniture_type: str
    position: PositionResponse
    affordances: List[str]
    in_use_by: Optional[str]


class RoomResponse(BaseModel):
    """A room with its furniture and current occupants."""

    name: str
    furniture: List[FurnitureResponse]
    occupants: List[str]


class EntitySummaryResponse(BaseModel):
    """Summary of any entity (Sims, furniture, etc.)."""

    entity_id: str
    position: Optional[PositionResponse]
    components: List[str]


class WorldStateResponse(BaseModel):
    """Full world snapshot returned by GET /world/state."""

    simulation_id: str
    tick_count: int
    state: str
    config: Dict[str, Any]
    time: TimeStateResponse
    rooms: List[RoomResponse]
    sims: List[SimSummaryResponse]
    entities: List[EntitySummaryResponse]


class TimeControlResponse(BaseModel):
    """Response for time-control POST endpoints."""

    previous_time: TimeStateResponse
    new_time: TimeStateResponse


class SpeedChangeResponse(BaseModel):
    """Response for POST /world/time/speed."""

    previous_speed: float
    previous_label: str
    new_speed: float
    new_label: str


class SaveResponse(BaseModel):
    """Response for POST /world/save."""

    filename: str
    saved: bool
    message: str


class LoadResponse(BaseModel):
    """Response for POST /world/load."""

    filename: str
    loaded: bool
    message: str
    time: TimeStateResponse
