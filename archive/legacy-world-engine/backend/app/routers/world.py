"""
World State Router

Exposes the WorldEngine simulation as a REST API for time control, Sim
inspection, room queries, and world save/load.

The WorldEngine is instantiated on app startup with a TimeManager and a
pre-built house containing rooms, furniture, and Sims.  It is advanced by
a background ticker thread so that polled state reflects a live simulation.
"""
from __future__ import annotations

import json
import logging
import re
import sys
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Ensure the project root (where ``src/`` lives) is importable.
# backend/app/routers/world.py  ->  4 dirname() calls  ->  project root
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from fastapi import APIRouter, Depends, HTTPException

from src.simulation.environment import (
    WorldEngine,
    WorldEngineConfig,
    SimulationState,
    TimeManager,
)
from src.simulation.environment.ecs import (
    AgentController,
    Entity,
    Interactable,
    Position,
)
from src.simulation.environment.schedule import (
    FurnitureComponent,
    FurnitureType,
    NeedsComponent,
    RoomComponent,
    ScheduleComponent,
)
from src.simulation.environment.relationships import RelationshipComponent

from ..schemas.world import (
    LoadRequest,
    SaveRequest,
    SpeedChangeResponse,
    SimDetailResponse,
    SimSummaryResponse,
    TimeAdvanceRequest,
    PositionResponse,
    RoomResponse,
    FurnitureResponse,
    TimeControlResponse,
    TimeSetRequest,
    TimeSpeedRequest,
    TimeStateResponse,
    WorldStateResponse,
    EntitySummaryResponse,
    SaveResponse,
    LoadResponse,
    TIME_SPEED_MULTIPLIERS,
)

router = APIRouter()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
WORLD_SAVES_DIR = _PROJECT_ROOT / "data" / "world_saves"

# Save filenames are restricted to a strict allowlist: no separators and no
# dots, so traversal payloads cannot be expressed at all.  Combined with the
# resolve/containment check in ``_validated_save_path`` this both hardens the
# endpoints and gives static analysers (CodeQL) a recognizable guard.
_FILENAME_PATTERN = re.compile(r"[a-zA-Z0-9_-]+")


def _validated_save_path(filename: str) -> Path:
    """Validate *filename* and return a save path confined to WORLD_SAVES_DIR."""
    if not _FILENAME_PATTERN.fullmatch(filename):
        raise HTTPException(
            status_code=400,
            detail="filename must contain only alphanumeric characters, hyphens, and underscores",
        )

    saves_root = WORLD_SAVES_DIR.resolve()
    # False positive: *filename* is allowlisted to [a-zA-Z0-9_-]+ (no path
    # separators or dots can be expressed) and the result is containment-
    # checked against WORLD_SAVES_DIR below. Suppressed as reviewed false
    # positive — approved by CEO, 2026-08-21 (PR #91 review 4995091171).
    # codeql[py/path-injection]
    save_path = (WORLD_SAVES_DIR / f"{filename}.json").resolve()
    if saves_root != save_path and saves_root not in save_path.parents:
        raise HTTPException(status_code=400, detail="Invalid filename")
    return save_path

# ---------------------------------------------------------------------------
# Module-level engine & helpers
# ---------------------------------------------------------------------------
_world_engine: Optional[WorldEngine] = None
_sim_names: Dict[str, str] = {}
_engine_lock = threading.Lock()
_ticker_stop: Optional[threading.Event] = None
_ticker_thread: Optional[threading.Thread] = None


def get_engine() -> WorldEngine:
    """Dependency that returns the shared WorldEngine singleton."""
    if _world_engine is None:
        raise HTTPException(status_code=503, detail="World engine is not initialized")
    return _world_engine


# ---------------------------------------------------------------------------
# Pre-built house definition
# ---------------------------------------------------------------------------

# (x, y, furniture_type, room_name, affordances)
_FURNITURE_LAYOUT: List[Tuple[int, int, FurnitureType, str, List[str]]] = [
    # Bedroom
    (2, 1, FurnitureType.BED, "bedroom", ["sleep", "rest"]),
    # Kitchen
    (5, 1, FurnitureType.FRIDGE, "kitchen", ["get_food"]),
    (6, 1, FurnitureType.STOVE, "kitchen", ["cook"]),
    (5, 2, FurnitureType.COUNTER, "kitchen", ["prepare"]),
    (5, 3, FurnitureType.TABLE, "kitchen", ["eat", "use"]),
    # Living room
    (9, 1, FurnitureType.COUCH, "living_room", ["sit", "relax"]),
    (10, 1, FurnitureType.COMPUTER, "living_room", ["use", "work"]),
    (9, 3, FurnitureType.TABLE, "living_room", ["eat", "use"]),
    # Bathroom
    (12, 1, FurnitureType.TOILET, "bathroom", ["use"]),
    (13, 1, FurnitureType.SHOWER, "bathroom", ["shower"]),
    # Office
    (15, 2, FurnitureType.COMPUTER, "office", ["use", "work"]),
    (15, 3, FurnitureType.TABLE, "office", ["use", "work"]),
]

# (x, y, agent_id, name, room_name)
_SIM_LAYOUT: List[Tuple[int, int, str, str, str]] = [
    (2, 2, "sim_alex", "Alex", "bedroom"),
    (8, 2, "sim_jamie", "Jamie", "living_room"),
]


def _build_house() -> Tuple[WorldEngine, Dict[str, str]]:
    """
    Instantiate a WorldEngine with a TimeManager and a pre-built house.

    The house contains five rooms (bedroom, kitchen, living room, bathroom,
    office), each with furniture, plus two Sims with autonomous schedules
    and needs.

    Returns a tuple of ``(engine, sim_names)`` where *sim_names* maps each
    Sim's entity id to a display name.
    """
    config = WorldEngineConfig(
        grid_width=20,
        grid_height=20,
        seconds_per_tick=1.0,
        time_speed_multiplier=1.0,
    )
    time_manager = TimeManager(
        start_day=1,
        start_hour=10,
        start_minute=0,
        speed_multiplier=1.0,
    )
    engine = WorldEngine(config=config, time_manager=time_manager)

    sim_names: Dict[str, str] = {}

    # --- furniture ----------------------------------------------------------
    for x, y, ftype, room, affordances in _FURNITURE_LAYOUT:
        entity = engine.spawn_entity()
        engine.registry.add_component(entity, Position(x, y, 0))
        engine.registry.add_component(entity, FurnitureComponent(ftype))
        engine.registry.add_component(entity, Interactable(affordances))
        engine.registry.add_component(entity, RoomComponent(room))

    # --- sims ---------------------------------------------------------------
    sim_entities: List[Entity] = []
    for x, y, agent_id, name, room in _SIM_LAYOUT:
        entity = engine.spawn_entity()
        engine.registry.add_component(entity, Position(x, y, 0))
        engine.registry.add_component(entity, AgentController(agent_id=agent_id))
        engine.registry.add_component(entity, NeedsComponent())
        engine.registry.add_component(entity, ScheduleComponent())
        engine.registry.add_component(entity, RoomComponent(room))
        sim_entities.append(entity)
        sim_names[entity.entity_id] = name

    # --- relationships between all Sim pairs --------------------------------
    for i in range(len(sim_entities)):
        for j in range(i + 1, len(sim_entities)):
            engine.relationship_manager.get_or_create(
                sim_entities[i].entity_id,
                sim_entities[j].entity_id,
            )

    # --- run a few ticks so schedules/activities resolve --------------------
    for _ in range(5):
        try:
            engine.run_simulation_step()
        except Exception:
            pass

    return engine, sim_names


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------

def _speed_label(multiplier: float) -> str:
    """Return the label closest to the given speed multiplier."""
    return min(
        TIME_SPEED_MULTIPLIERS,
        key=lambda label: abs(TIME_SPEED_MULTIPLIERS[label] - multiplier),
    )


def _time_state(engine: WorldEngine) -> TimeStateResponse:
    tm = engine.time_manager
    return TimeStateResponse(
        day=tm.day,
        hour=tm.hour,
        minute=tm.minute,
        is_daytime=tm.is_daytime,
        day_of_week=tm.day_of_week,
        weekend=tm.weekend,
        total_minutes_elapsed=tm.total_minutes_elapsed,
        speed_multiplier=tm.speed_multiplier,
        speed_label=_speed_label(tm.speed_multiplier),
    )


def _position_response(comp: Position) -> PositionResponse:
    return PositionResponse(x=comp.x, y=comp.y, z=getattr(comp, "z", 0))


def _is_sim(entity: Entity, registry) -> bool:
    """Return True if the entity has the components that identify a Sim."""
    return (
        registry.has_component(entity, AgentController)
        and registry.has_component(entity, Position)
        and registry.has_component(entity, ScheduleComponent)
    )


def _get_sim_name(sim_id: str) -> str:
    return _sim_names.get(sim_id, sim_id)


def _mood_from_needs(needs: Dict[str, float]) -> str:
    """Derive a mood label from a Sim's need levels."""
    if not needs:
        return "neutral"
    lowest = min(needs.values())
    if lowest < 20:
        return "distressed"
    if lowest < 40:
        return "uncomfortable"
    if lowest >= 70:
        return "happy"
    return "content"


def _serialize_sim_summary(entity: Entity, engine: WorldEngine) -> SimSummaryResponse:
    registry = engine.registry
    pos = registry.get_component(entity, Position)
    schedule = registry.get_component(entity, ScheduleComponent)
    needs = registry.get_component(entity, NeedsComponent)

    room = "unknown"
    room_comp = registry.get_component(entity, RoomComponent)
    if room_comp is not None:
        room = room_comp.room_name

    needs_summary: Dict[str, float] = {}
    if needs is not None:
        needs_summary = {k.value: v for k, v in needs.needs.items()}

    activity = "idle"
    if schedule is not None and schedule.current_activity:
        activity = schedule.current_activity

    return SimSummaryResponse(
        sim_id=entity.entity_id,
        name=_get_sim_name(entity.entity_id),
        position=_position_response(pos) if pos else PositionResponse(x=0, y=0, z=0),
        room=room,
        current_activity=activity,
        needs_summary=needs_summary,
    )


def _serialize_sim_detail(entity: Entity, engine: WorldEngine) -> SimDetailResponse:
    registry = engine.registry
    pos = registry.get_component(entity, Position)
    schedule = registry.get_component(entity, ScheduleComponent)
    needs = registry.get_component(entity, NeedsComponent)
    room_comp = registry.get_component(entity, RoomComponent)

    room = room_comp.room_name if room_comp is not None else "unknown"

    full_needs: Dict[str, float] = {}
    if needs is not None:
        full_needs = {k.value: v for k, v in needs.needs.items()}

    # Relationships
    relationships: List[Dict[str, Any]] = []
    for rel_comp in engine.relationship_manager.get_all_for_sim(entity.entity_id):
        other_id = rel_comp.other_sim(entity.entity_id)
        relationships.append({
            "other_sim_id": other_id,
            "other_sim_name": _get_sim_name(other_id) if other_id else None,
            "friendship": rel_comp.friendship,
            "romance": rel_comp.romance,
            "familiarity": rel_comp.familiarity,
            "interaction_count": rel_comp.interaction_count,
        })

    # Schedule
    schedule_data: Dict[str, Any] = {}
    if schedule is not None:
        schedule_data = schedule.to_dict()

    activity = "idle"
    if schedule is not None and schedule.current_activity:
        activity = schedule.current_activity

    return SimDetailResponse(
        sim_id=entity.entity_id,
        name=_get_sim_name(entity.entity_id),
        position=_position_response(pos) if pos else PositionResponse(x=0, y=0, z=0),
        room=room,
        current_activity=activity,
        needs=full_needs,
        mood=_mood_from_needs(full_needs),
        weekend=schedule.weekend if schedule else False,
        relationships=relationships,
        schedule=schedule_data,
    )


def _serialize_furniture(entity: Entity, registry) -> FurnitureResponse:
    pos = registry.get_component(entity, Position)
    furniture = registry.get_component(entity, FurnitureComponent)
    interactable = registry.get_component(entity, Interactable)
    return FurnitureResponse(
        entity_id=entity.entity_id,
        furniture_type=furniture.furniture_type.value if furniture else "unknown",
        position=_position_response(pos) if pos else PositionResponse(x=0, y=0, z=0),
        affordances=interactable.affordances if interactable else [],
        in_use_by=interactable.in_use_by if interactable else None,
    )


def _serialize_room(room_name: str, engine: WorldEngine) -> RoomResponse:
    """Build a RoomResponse by scanning the registry for entities in *room_name*."""
    registry = engine.registry

    furniture_list: List[FurnitureResponse] = []
    occupants: List[str] = []

    for entity in registry.get_entities_with(Position, RoomComponent):
        room_comp = registry.get_component(entity, RoomComponent)
        if room_comp is None or room_comp.room_name != room_name:
            continue

        # Furniture entities are those with FurnitureComponent
        if registry.has_component(entity, FurnitureComponent):
            furniture_list.append(_serialize_furniture(entity, registry))

        # Sims in this room
        elif _is_sim(entity, registry):
            occupants.append(_get_sim_name(entity.entity_id))

    return RoomResponse(
        name=room_name,
        furniture=furniture_list,
        occupants=occupants,
    )


def _serialize_entity_summary(entity: Entity, registry) -> EntitySummaryResponse:
    pos = registry.get_component(entity, Position)
    comp_names: List[str] = []
    for comp_type in registry.get_component_types():
        comp = registry.get_component(entity, comp_type)
        if comp is not None:
            comp_names.append(comp_type.__name__)
    return EntitySummaryResponse(
        entity_id=entity.entity_id,
        position=_position_response(pos) if pos else None,
        components=comp_names,
    )


# ---------------------------------------------------------------------------
# Public lifecycle functions (called from main.py)
# ---------------------------------------------------------------------------


def init_world_engine() -> WorldEngine:
    """Create the shared WorldEngine and start the background ticker."""
    global _world_engine, _sim_names, _ticker_stop, _ticker_thread

    if _world_engine is None:
        engine, sim_names = _build_house()
        with _engine_lock:
            _world_engine = engine
            _sim_names = sim_names

    if _ticker_thread is None or not _ticker_thread.is_alive():
        _ticker_stop = threading.Event()
        _ticker_thread = threading.Thread(
            target=_ticker_loop,
            daemon=True,
        )
        _ticker_thread.start()

    return _world_engine


def shutdown_world_engine() -> None:
    """Stop the background ticker."""
    global _ticker_thread
    if _ticker_stop is not None:
        _ticker_stop.set()
    thread = _ticker_thread
    _ticker_thread = None
    if thread is not None and thread.is_alive():
        thread.join(timeout=2.0)


@asynccontextmanager
async def lifespan(app: Any):
    """FastAPI lifespan hook — initialise the world engine on startup."""
    init_world_engine()
    yield
    shutdown_world_engine()


def _ticker_loop() -> None:
    """Run simulation steps on a fixed real-time interval."""
    assert _ticker_stop is not None
    assert _world_engine is not None
    last_error_log = 0.0
    while not _ticker_stop.wait(1.0):
        try:
            with _engine_lock:
                if _world_engine.current_state == SimulationState.RUNNING:
                    _world_engine.run_simulation_step()
        except Exception:
            # Keep the ticker alive, but surface failures (rate-limited so a
            # persistently broken step does not flood the logs at 1/sec).
            now = time.monotonic()
            if now - last_error_log >= 30.0:
                last_error_log = now
                logger.exception(
                    "World tick failed (suppressing similar errors for 30s)"
                )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/state", response_model=WorldStateResponse, summary="Get full world snapshot")
async def get_world_state(engine: WorldEngine = Depends(get_engine)):
    """Return the complete world snapshot: time, rooms, entities, and Sims."""
    with _engine_lock:
        time_state = _time_state(engine)

        room_names: List[str] = []
        for entity in engine.registry.get_entities_with(RoomComponent):
            room_comp = engine.registry.get_component(entity, RoomComponent)
            if room_comp and room_comp.room_name not in room_names:
                room_names.append(room_comp.room_name)

        rooms = [_serialize_room(name, engine) for name in room_names]

        sims: List[SimSummaryResponse] = []
        for entity in engine.registry.get_entities_with(
            AgentController, Position, ScheduleComponent
        ):
            sims.append(_serialize_sim_summary(entity, engine))

        entities = [
            _serialize_entity_summary(e, engine.registry)
            for e in engine.registry.get_entities()
        ]

    return WorldStateResponse(
        simulation_id=engine.simulation_id,
        tick_count=engine.tick_count,
        state=engine.current_state.value,
        config={
            "grid_width": engine.config.grid_width,
            "grid_height": engine.config.grid_height,
            "seconds_per_tick": engine.config.seconds_per_tick,
            "time_speed_multiplier": engine.config.time_speed_multiplier,
        },
        time=time_state,
        rooms=rooms,
        sims=sims,
        entities=entities,
    )


@router.post("/time/advance", response_model=TimeControlResponse, summary="Advance simulation time")
async def advance_time(
    body: TimeAdvanceRequest,
    engine: WorldEngine = Depends(get_engine),
):
    """Advance the simulation clock by *N* real minutes."""
    if body.minutes < 0:
        raise HTTPException(status_code=400, detail="minutes must be non-negative")

    with _engine_lock:
        prev = _time_state(engine)
        engine.time_manager.advance(body.minutes)
        new = _time_state(engine)

    return TimeControlResponse(previous_time=prev, new_time=new)


@router.post("/time/set", response_model=TimeControlResponse, summary="Set the simulation time")
async def set_time(
    body: TimeSetRequest,
    engine: WorldEngine = Depends(get_engine),
):
    """Set the simulation clock to a specific hour and minute on the current day."""
    if not (0 <= body.hour <= 23):
        raise HTTPException(status_code=400, detail="hour must be in 0-23")
    if not (0 <= body.minute <= 59):
        raise HTTPException(status_code=400, detail="minute must be in 0-59")

    with _engine_lock:
        prev = _time_state(engine)
        engine.time_manager.set_time(body.hour, body.minute)
        new = _time_state(engine)

    return TimeControlResponse(previous_time=prev, new_time=new)


@router.post("/time/speed", response_model=SpeedChangeResponse, summary="Set simulation time speed")
async def set_speed(
    body: TimeSpeedRequest,
    engine: WorldEngine = Depends(get_engine),
):
    """Set the time acceleration multiplier (realtime=1x, fast=5x, ultra=20x, hyper=100x)."""
    lower = body.speed.lower().strip()
    if lower not in TIME_SPEED_MULTIPLIERS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid speed '{body.speed}'. Valid speeds: {list(TIME_SPEED_MULTIPLIERS.keys())}",
        )

    new_multiplier = TIME_SPEED_MULTIPLIERS[lower]

    with _engine_lock:
        prev_multiplier = engine.time_manager.speed_multiplier
        prev_label = _speed_label(prev_multiplier)
        engine.time_manager.speed_multiplier = new_multiplier
        engine.config.time_speed_multiplier = new_multiplier

    return SpeedChangeResponse(
        previous_speed=prev_multiplier,
        previous_label=prev_label,
        new_speed=new_multiplier,
        new_label=lower,
    )


@router.get("/sims", response_model=List[SimSummaryResponse], summary="List all Sims")
async def list_sims(engine: WorldEngine = Depends(get_engine)):
    """Return a lightweight summary of every Sim: name, needs, activity, location."""
    with _engine_lock:
        sims = [
            _serialize_sim_summary(e, engine)
            for e in engine.registry.get_entities_with(
                AgentController, Position, ScheduleComponent
            )
        ]
    return sims


@router.get("/sims/{sim_id}", response_model=SimDetailResponse, summary="Get detailed Sim state")
async def get_sim(
    sim_id: str,
    engine: WorldEngine = Depends(get_engine),
):
    """Return detailed state for a single Sim (matched by entity id or agent id)."""
    with _engine_lock:
        entity = None
        for e in engine.registry.get_entities():
            if e.entity_id == sim_id:
                entity = e
                break
            comp = engine.registry.get_component(e, AgentController)
            if comp is not None and comp.agent_id == sim_id:
                entity = e
                break

        if entity is None:
            raise HTTPException(
                status_code=404, detail=f"Sim '{sim_id}' not found"
            )

        return _serialize_sim_detail(entity, engine)


@router.get("/rooms", response_model=List[RoomResponse], summary="List all rooms")
async def list_rooms(engine: WorldEngine = Depends(get_engine)):
    """Return every room with its furniture and current occupants."""
    with _engine_lock:
        room_names: List[str] = []
        for entity in engine.registry.get_entities_with(RoomComponent):
            room_comp = engine.registry.get_component(entity, RoomComponent)
            if room_comp and room_comp.room_name not in room_names:
                room_names.append(room_comp.room_name)
        rooms = [_serialize_room(name, engine) for name in room_names]
    return rooms


@router.post("/save", response_model=SaveResponse, summary="Save world state to file")
async def save_world(
    body: SaveRequest,
    engine: WorldEngine = Depends(get_engine),
):
    """Persist the current world state as a JSON file in ``data/world_saves/``."""
    save_path = _validated_save_path(body.filename)

    with _engine_lock:
        state_json = engine.save_state()

    # Parse, attach sim names, re-serialise
    state = json.loads(state_json)
    state["sim_names"] = dict(_sim_names)
    state_json = json.dumps(state, indent=2)

    try:
        # False positive: save_path confined by _validated_save_path() (allowlist
        # + containment check). Suppressed — CEO approved, 2026-08-21.
        # codeql[py/path-injection]
        save_path.parent.mkdir(parents=True, exist_ok=True)
        # False positive: see _validated_save_path() containment guarantee.
        # codeql[py/path-injection]
        save_path.write_text(state_json, encoding="utf-8")
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Failed to write save file: {e}")

    return SaveResponse(
        filename=body.filename,
        saved=True,
        message=f"World saved to {save_path}",
    )


@router.post("/load", response_model=LoadResponse, summary="Load world state from file")
async def load_world(
    body: LoadRequest,
    engine: WorldEngine = Depends(get_engine),
):
    """Load a previously saved world state from ``data/world_saves/``."""
    save_path = _validated_save_path(body.filename)
    # False positive: save_path confined by _validated_save_path() (allowlist
    # + containment check). Suppressed — CEO approved, 2026-08-21.
    # codeql[py/path-injection]
    if not save_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Save file '{body.filename}.json' not found in {WORLD_SAVES_DIR}",
        )

    try:
        # False positive: see _validated_save_path() containment guarantee.
        # codeql[py/path-injection]
        raw = save_path.read_text(encoding="utf-8")
        state = json.loads(raw)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Save file is not valid JSON: {e}")

    # Restore sim names if present
    saved_names = state.pop("sim_names", {})

    with _engine_lock:
        try:
            engine.load_state(json.dumps(state))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        _sim_names.clear()
        _sim_names.update(saved_names)

    time_state = _time_state(engine)
    return LoadResponse(
        filename=body.filename,
        loaded=True,
        message=f"World loaded from {save_path}",
        time=time_state,
    )
