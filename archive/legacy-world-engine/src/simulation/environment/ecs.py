"""
Entity Component System (ECS) Foundation

This module defines the core ECS architecture for the simulation engine.
It uses a hybrid approach where the physical environment is managed via
ECS for performance and scalability, while cognitive AI agents can interface
with entities using rich object-oriented logic.
"""

import uuid
from typing import Any, Dict, List, Type, TypeVar, Optional, Set, cast

T = TypeVar('T', bound='Component')

class Component:
    """Base class for all data components attached to entities."""
    pass

class Entity:
    """
    An Entity in the world. Represented primarily by its ID.
    Components are managed by the ECS registry.
    """
    def __init__(self, entity_id: Optional[str] = None):
        self.entity_id = entity_id or str(uuid.uuid4())

    def __hash__(self):
        return hash(self.entity_id)

    def __eq__(self, other):
        if not isinstance(other, Entity):
            return False
        return self.entity_id == other.entity_id

class System:
    """
    Base class for all systems that process logic over entities with
    specific components.
    """
    def __init__(self):
        self.registry: Optional['Registry'] = None

    def set_registry(self, registry: 'Registry') -> None:
        self.registry = registry

    def update(self, delta_time: float) -> None:
        """Process entities. Override this in subclasses."""
        pass

class Registry:
    """
    Central manager for the ECS architecture.
    Stores all entities, their components, and runs registered systems.
    """
    def __init__(self):
        self._entities: Set[Entity] = set()
        # Dictionary mapping Component Class -> {Entity ID -> Component Instance}
        self._components: Dict[Type[Component], Dict[str, Component]] = {}
        self._systems: List[System] = []

    def add_entity(self, entity: Entity) -> None:
        """Add an entity to the registry."""
        self._entities.add(entity)

    def remove_entity(self, entity: Entity) -> None:
        """Remove an entity and all its associated components."""
        if entity in self._entities:
            self._entities.remove(entity)
            for component_type in self._components:
                if entity.entity_id in self._components[component_type]:
                    del self._components[component_type][entity.entity_id]

    def add_component(self, entity: Entity, component: Component) -> None:
        """Add a component to an entity."""
        comp_type = type(component)
        if comp_type not in self._components:
            self._components[comp_type] = {}
        self._components[comp_type][entity.entity_id] = component

    def get_component(self, entity: Entity, component_type: Type[T]) -> Optional[T]:
        """Get a specific component for an entity, if it exists."""
        if component_type in self._components:
            return cast(Optional[T], self._components[component_type].get(entity.entity_id))
        return None

    def has_component(self, entity: Entity, component_type: Type[Component]) -> bool:
        """Check if an entity has a specific component."""
        if component_type in self._components:
            return entity.entity_id in self._components[component_type]
        return False

    def get_entities_with(self, *component_types: Type[Component]) -> List[Entity]:
        """Get all entities that have ALL the specified components."""
        if not component_types:
            return list(self._entities)
            
        result = []
        for entity in self._entities:
            has_all = all(self.has_component(entity, c_type) for c_type in component_types)
            if has_all:
                result.append(entity)
        return result

    def get_entities(self) -> List[Entity]:
        """Return all entities in the registry."""
        return list(self._entities)

    def get_component_types(self) -> List[Type[Component]]:
        """Return a list of all component types currently registered."""
        return list(self._components.keys())

    def register_system(self, system: System) -> None:
        """Register a system to be processed during ticks."""
        system.set_registry(self)
        self._systems.append(system)

    def tick(self, delta_time: float) -> None:
        """Run all systems."""
        for system in self._systems:
            system.update(delta_time)

# --- Standard Core Components ---

class Position(Component):
    """Spatial position component for the discrete grid world."""
    def __init__(self, x: int = 0, y: int = 0, z: int = 0):
        self.x = x
        self.y = y
        self.z = z
        
    def __str__(self):
        return f"Position({self.x}, {self.y}, {self.z})"

class Interactable(Component):
    """Component that defines what actions an agent can take on this entity."""
    def __init__(self, affordances: Optional[List[str]] = None):
        self.affordances = affordances or []
        self.in_use_by: Optional[str] = None  # Agent ID currently using this

class AgentController(Component):
    """
    Bridge component connecting an ECS Entity to an external cognitive AI agent.
    The agent submits 'intents' which the systems process over time.
    """
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.current_intent: Optional[Dict[str, Any]] = None
        self.intent_progress: float = 0.0
