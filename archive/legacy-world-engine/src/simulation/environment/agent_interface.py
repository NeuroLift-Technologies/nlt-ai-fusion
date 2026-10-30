"""
Agent Interface

The API boundary between the physical WorldEngine (ECS) and the 
cognitive AI Agents (like BaseAvatar). Provides perception and action queues.
"""

from typing import Dict, List, Any, Optional
from .world_engine import WorldEngine
from .ecs import Entity, Position, Interactable, AgentController

class PerceptionMap:
    """A snapshot of what the agent can currently see in the world."""
    def __init__(self, my_pos: Position, visible_entities: List[Entity], engine: WorldEngine):
        self.my_pos = my_pos
        self.entities = visible_entities
        self._engine = engine
        
    def describe_surroundings(self) -> List[Dict[str, Any]]:
        """
        Returns a simplified list of objects and affordances for the LLM/Cognitive model.
        """
        descriptions = []
        for e in self.entities:
            pos = self._engine.registry.get_component(e, Position)
            interactable = self._engine.registry.get_component(e, Interactable)
            
            desc = {
                "entity_id": e.entity_id,
                "distance": abs(pos.x - self.my_pos.x) + abs(pos.y - self.my_pos.y) if pos else -1,
            }
            if interactable:
                desc["affordances"] = interactable.affordances
                desc["in_use"] = interactable.in_use_by is not None
                
            descriptions.append(desc)
            
        # Sort by distance
        descriptions.sort(key=lambda x: x["distance"])  # type: ignore[arg-type,return-value]
        return descriptions

class AgentInterface:
    """
    Bridge class instantiated by an AI Agent (like BaseAvatar).
    It links to a specific physical Entity in the WorldEngine.
    """
    
    def __init__(self, engine: WorldEngine, agent_id: str):
        self.engine = engine
        self.agent_id = agent_id
        
        # Spawn an entity for this agent
        self.entity = self.engine.spawn_entity()
        
        # Attach required components
        self.controller = AgentController(agent_id=agent_id)
        self.engine.registry.add_component(self.entity, self.controller)
        self.engine.registry.add_component(self.entity, Position(0, 0, 0))
        
    def perceive(self, vision_radius: int = 5) -> PerceptionMap:
        """Query the world map for nearby entities."""
        pos = self.engine.registry.get_component(self.entity, Position)
        if not pos:
            return PerceptionMap(Position(), [], self.engine)
            
        nearby = self.engine.grid.get_entities_in_radius(pos.x, pos.y, vision_radius)
        # Exclude self
        if self.entity in nearby:
            nearby.remove(self.entity)
            
        return PerceptionMap(pos, nearby, self.engine)
        
    def submit_intent(self, intent_type: str, target_id: Optional[str] = None, data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Submit an action for the ECS engine to process.
        Returns False if the agent is already busy.
        """
        if self.controller.current_intent is not None:
            return False # Agent is currently executing an action
            
        self.controller.current_intent = {
            "type": intent_type,
            "target_id": target_id,
            "data": data or {}
        }
        self.controller.intent_progress = 0.0
        return True
        
    def check_intent_status(self) -> Optional[Dict[str, Any]]:
        """Return the current action the agent is performing."""
        return self.controller.current_intent
