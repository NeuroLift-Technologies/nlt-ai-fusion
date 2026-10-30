import pytest
from datetime import timedelta
from src.simulation.environment.ecs import Entity, Position, Interactable, AgentController, System
from src.simulation.environment.world_engine import WorldEngine, SimulationState
from src.simulation.environment.world_map import GridManager
from src.simulation.environment.agent_interface import AgentInterface

class DummyMovementSystem(System):
    """A simple system to test ECS updates."""
    def update(self, delta_time: float) -> None:
        entities = self.registry.get_entities_with(Position, AgentController)
        for entity in entities:
            pos = self.registry.get_component(entity, Position)
            controller = self.registry.get_component(entity, AgentController)
            
            # Very simple fake movement based on intent
            if controller.current_intent and controller.current_intent["type"] == "move":
                target = controller.current_intent["data"]
                # Move 1 step towards target
                if pos.x < target["x"]: pos.x += 1
                elif pos.x > target["x"]: pos.x -= 1
                elif pos.y < target["y"]: pos.y += 1
                elif pos.y > target["y"]: pos.y -= 1
                
                if pos.x == target["x"] and pos.y == target["y"]:
                    controller.current_intent = None # Finished

def test_ecs_basic_operations():
    engine = WorldEngine()
    entity = engine.spawn_entity()
    
    pos = Position(1, 2, 0)
    engine.registry.add_component(entity, pos)
    
    assert engine.registry.has_component(entity, Position)
    retrieved_pos = engine.registry.get_component(entity, Position)
    assert retrieved_pos.x == 1
    assert retrieved_pos.y == 2
    
    engine.remove_entity(entity)
    assert not engine.registry.has_component(entity, Position)

def test_spatial_grid_queries():
    engine = WorldEngine()
    
    e1 = engine.spawn_entity()
    engine.registry.add_component(e1, Position(5, 5, 0))
    
    e2 = engine.spawn_entity()
    engine.registry.add_component(e2, Position(5, 6, 0))
    
    e3 = engine.spawn_entity()
    engine.registry.add_component(e3, Position(20, 20, 0))
    
    # Radius 2 from (5,5) should catch e1 and e2, but not e3
    nearby = engine.grid.get_entities_in_radius(5, 5, 2)
    assert e1 in nearby
    assert e2 in nearby
    assert e3 not in nearby

def test_pathfinding():
    engine = WorldEngine()
    
    # Put a solid object at (2, 2)
    wall = engine.spawn_entity()
    engine.registry.add_component(wall, Position(2, 2, 0))
    engine.registry.add_component(wall, Interactable(["examine"])) # Interactable acts as solid
    
    assert not engine.grid.is_walkable(2, 2)
    assert engine.grid.is_walkable(2, 3)
    
    # Path from (1, 2) to (3, 2) should go around the wall at (2, 2)
    path = engine.grid.find_path(1, 2, 3, 2)
    
    assert len(path) > 0
    assert (2, 2) not in path # Must not step on the wall

def test_engine_tick_and_agent_interface():
    engine = WorldEngine()
    engine.registry.register_system(DummyMovementSystem())
    
    agent = AgentInterface(engine, "agent_1")
    # Agent starts at (0,0) by default
    
    agent.submit_intent("move", data={"x": 3, "y": 0})
    
    assert agent.check_intent_status() is not None
    
    # Tick 1: moves to (1, 0)
    engine.run_simulation_step()
    pos = engine.registry.get_component(agent.entity, Position)
    assert pos.x == 1
    assert pos.y == 0
    
    # Tick 2: moves to (2, 0)
    engine.run_simulation_step()
    
    # Tick 3: moves to (3, 0)
    engine.run_simulation_step()
    pos = engine.registry.get_component(agent.entity, Position)
    assert pos.x == 3
    assert pos.y == 0
    
    # Intent should be cleared by DummyMovementSystem
    assert agent.check_intent_status() is None
