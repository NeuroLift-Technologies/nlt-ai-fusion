"""
World Engine

Core simulation engine that manages the virtual world.
Now powered by a hybrid Entity-Component System (ECS) to efficiently
handle thousands of objects, spatial queries, and ticking mechanics.

The engine owns a :class:`~.ecosystem.TimeManager`-like clock (delegated
to :class:`~.time_manager.TimeManager`), a
:class:`~.relationships.RelationshipManager`, and an ECS
:class:`~.ecosystem.Registry` backed by a spatial
:class:`~.world_map.GridManager`.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Type
import json
import uuid
from datetime import datetime, timedelta

from .ecs import Registry, Entity, System, Position, Interactable, AgentController
from .world_map import GridManager


@dataclass
class WorldEngineConfig:
    """Configuration for a :class:`WorldEngine` instance."""

    grid_width: int = 100
    grid_height: int = 100
    seconds_per_tick: float = 1.0
    time_speed_multiplier: float = 1.0


class SimulationState(Enum):
    """Current state of the simulation"""
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


class EventType(Enum):
    """Types of events emitted by the simulation engine"""
    TICK = "tick"
    ENTITY_ADDED = "entity_added"
    ENTITY_REMOVED = "entity_removed"
    ENTITY_MOVED = "entity_moved"
    INTERACTION_STARTED = "interaction_started"
    INTERACTION_COMPLETED = "interaction_completed"


# ---------------------------------------------------------------------------
# Internal component serializers
# ---------------------------------------------------------------------------
# Maps component-type -> (qualifier string, to_dict callable).
# Components without a registered serializer fall back to a generic dump
# of public attributes.

def _serialize_component(comp: Any) -> Dict[str, Any]:
    """Serialize a component instance to a JSON-friendly dict."""
    if hasattr(comp, "to_dict"):
        return comp.to_dict()
    # Fallback: dump public attributes
    result: Dict[str, Any] = {}
    for attr_name in dir(comp):
        if attr_name.startswith("_") or attr_name.startswith("to_dict"):
            continue
        try:
            val = getattr(comp, attr_name)
        except AttributeError:
            continue
        if callable(val):
            continue
        result[attr_name] = val
    return result


# Maps (module_name, class_name) -> factory callable for deserialization
_COMPONENT_FACTORIES: Dict[str, Any] = {}


def _register_component_factory(cls: Type[Any]) -> Type[Any]:
    _COMPONENT_FACTORIES[f"{cls.__module__}.{cls.__name__}"] = cls
    return cls


# Registry of component classes we know how to reconstruct
from .ecs import Position as _Position, Interactable as _Interactable, AgentController as _AgentController
_register_component_factory(_Position)
_register_component_factory(_Interactable)
_register_component_factory(_AgentController)

try:
    from .schedule import (
        FurnitureComponent, FurnitureType, NeedsComponent, NeedType,
        RoomComponent, ScheduleComponent,
    )
    _register_component_factory(FurnitureComponent)
    _register_component_factory(NeedsComponent)
    _register_component_factory(RoomComponent)
    _register_component_factory(ScheduleComponent)
except ImportError:
    FurnitureComponent = FurnitureType = NeedsComponent = NeedType = RoomComponent = ScheduleComponent = None  # type: ignore

try:
    from .relationships import RelationshipComponent
    _register_component_factory(RelationshipComponent)
except ImportError:
    RelationshipComponent = None  # type: ignore

try:
    from .time_manager import TimeManager
except ImportError:
    TimeManager = None  # type: ignore


class WorldEngine:
    """
    The main driver for the ECS and spatial grid.
    Advances time, runs systems, and emits global events.
    """

    def __init__(
        self,
        config: Optional[Any] = None,
        time_manager: Optional[Any] = None,
    ):
        # Normalise config to a WorldEngineConfig dataclass
        if config is None:
            config = WorldEngineConfig()
        elif isinstance(config, dict):
            config = WorldEngineConfig(**config)
        elif not isinstance(config, WorldEngineConfig):
            raise TypeError(
                f"config must be a WorldEngineConfig, dict, or None, "
                f"got {type(config).__name__}"
            )
        self.config: WorldEngineConfig = config

        # Time management
        if time_manager is None:
            time_manager = TimeManager(
                start_day=1,
                start_hour=10,
                start_minute=0,
                speed_multiplier=config.time_speed_multiplier,
            )
        self.time_manager = time_manager

        # Relationship management
        from .relationships import RelationshipManager
        self.relationship_manager: RelationshipManager = RelationshipManager()

        # Core state
        self.simulation_id: str = str(uuid.uuid4())
        self.current_state: SimulationState = SimulationState.INITIALIZING

        # Legacy time fields (kept for backward compatibility)
        self.simulation_time: datetime = datetime.now()
        self.tick_count: int = 0
        self.time_per_tick: timedelta = timedelta(seconds=config.seconds_per_tick)

        # Architecture
        self.registry: Registry = Registry()
        self.grid: GridManager = GridManager(
            width=config.grid_width,
            height=config.grid_height,
            registry=self.registry,
        )

        # Event Bus
        self.event_listeners: Dict[EventType, List[Any]] = {e: [] for e in EventType}

        self.initialize()

    def initialize(self) -> None:
        """Set up initial systems and state."""
        self.current_state = SimulationState.RUNNING

        # Register Core Systems here. E.g.:
        # self.registry.register_system(MovementSystem())
        # self.registry.register_system(InteractionSystem())

    def spawn_entity(self) -> Entity:
        """Create and register a new entity."""
        entity = Entity()
        self.registry.add_entity(entity)
        self.emit_event(EventType.ENTITY_ADDED, {"entity_id": entity.entity_id})
        return entity

    def remove_entity(self, entity: Entity) -> None:
        """Remove an entity from the world."""
        self.registry.remove_entity(entity)
        self.emit_event(EventType.ENTITY_REMOVED, {"entity_id": entity.entity_id})

    def run_simulation_step(self) -> bool:
        """
        Run one 'tick' of the simulation.
        Processes all ECS systems, updates time, and fires events.
        """
        if self.current_state != SimulationState.RUNNING:
            return False

        try:
            # Time delta for systems is usually seconds
            dt = self.time_per_tick.total_seconds()

            # 1. Run ECS Systems
            self.registry.tick(dt)

            # 2. Update legacy simulation_time
            self.simulation_time += self.time_per_tick

            # 3. Advance the time manager (game minutes = real seconds * speed)
            if self.time_manager is not None:
                game_minutes = dt * self.time_manager.speed_multiplier
                self.time_manager.advance(game_minutes)

            self.tick_count += 1

            # 3. Emit global tick event
            self.emit_event(EventType.TICK, {
                "tick_count": self.tick_count,
                "simulation_time": self.simulation_time.isoformat(),
            })

            return True

        except Exception as e:
            self.current_state = SimulationState.ERROR
            print(f"Simulation tick failed: {e}")
            return False

    def emit_event(self, event_type: EventType, data: Dict[str, Any]) -> None:
        """Simple pub/sub for engine events."""
        listeners = self.event_listeners.get(event_type, [])
        for listener in listeners:
            try:
                # Expecting a callable listener: listener(event_type, data)
                listener(event_type, data)
            except Exception as e:
                print(f"Error in event listener: {e}")

    def subscribe(self, event_type: EventType, listener: Any) -> None:
        """Subscribe to engine events."""
        if event_type in self.event_listeners:
            self.event_listeners[event_type].append(listener)

    # ------------------------------------------------------------------
    # State persistence
    # ------------------------------------------------------------------

    def save_state(self) -> str:
        """Serialise the engine's full state to a JSON string."""
        entities_data: List[Dict[str, Any]] = []
        comp_types = self.registry.get_component_types()

        for entity in self.registry.get_entities():
            entity_entry: Dict[str, Any] = {"entity_id": entity.entity_id}
            components: Dict[str, Any] = {}
            for comp_type in comp_types:
                comp = self.registry.get_component(entity, comp_type)
                if comp is not None:
                    qual = f"{comp_type.__module__}.{comp_type.__name__}"
                    components[qual] = _serialize_component(comp)
            entity_entry["components"] = components
            entities_data.append(entity_entry)

        state: Dict[str, Any] = {
            "simulation_id": self.simulation_id,
            "current_state": self.current_state.value,
            "simulation_time": self.simulation_time.isoformat(),
            "tick_count": self.tick_count,
            "time_per_tick_seconds": self.time_per_tick.total_seconds(),
            "time_manager": self.time_manager.to_dict() if self.time_manager else None,
            "config": {
                "grid_width": self.config.grid_width,
                "grid_height": self.config.grid_height,
                "seconds_per_tick": self.config.seconds_per_tick,
                "time_speed_multiplier": self.config.time_speed_multiplier,
            },
            "entities": entities_data,
            "relationships": self.relationship_manager.to_dict() if self.relationship_manager else None,
        }
        return json.dumps(state, indent=2)

    def load_state(self, state_json: str) -> None:
        """Restore engine state from a JSON string produced by :meth:`save_state`."""
        if not state_json:
            raise ValueError("state_json is empty")
        try:
            state = json.loads(state_json)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON state: {exc}") from exc

        # Replace registry (fresh start)
        self.registry = Registry()
        self.grid = GridManager(
            width=self.config.grid_width,
            height=self.config.grid_height,
            registry=self.registry,
        )

        # Core scalar fields
        self.simulation_id = state["simulation_id"]
        self.current_state = SimulationState(state["current_state"])
        self.simulation_time = datetime.fromisoformat(state["simulation_time"])
        self.tick_count = state["tick_count"]
        self.time_per_tick = timedelta(seconds=state["time_per_tick_seconds"])

        # Time manager
        if self.time_manager is not None and state.get("time_manager"):
            self.time_manager = TimeManager.from_dict(state["time_manager"])

        # Relationships
        if self.relationship_manager is not None and state.get("relationships"):
            self.relationship_manager.from_dict(state["relationships"])

        # Entities & components
        entities_data = state.get("entities", [])
        for entry in entities_data:
            entity = Entity(entity_id=entry["entity_id"])
            self.registry.add_entity(entity)
            components = entry.get("components", {})
            for qual_name, comp_data in components.items():
                comp_cls = _COMPONENT_FACTORIES.get(qual_name)
                if comp_cls is None:
                    continue
                if hasattr(comp_cls, "from_dict"):
                    comp = comp_cls.from_dict(comp_data)
                else:
                    # Fallback: attempt direct construction
                    try:
                        comp = comp_cls(**comp_data)
                    except TypeError:
                        continue
                self.registry.add_component(entity, comp)

        self.emit_event(EventType.TICK, {
            "tick_count": self.tick_count,
            "simulation_time": self.simulation_time.isoformat(),
            "event": "state_loaded",
        })
