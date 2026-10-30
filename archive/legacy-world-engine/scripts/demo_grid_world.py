import os
import sys
import time

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.simulation.environment.world_engine import WorldEngine
from src.simulation.environment.ecs import Position, Interactable, System, AgentController
from src.simulation.environment.agent_interface import AgentInterface

class SimpleMovementSystem(System):
    def update(self, delta_time: float) -> None:
        entities = self.registry.get_entities_with(Position, AgentController)
        for entity in entities:
            pos = self.registry.get_component(entity, Position)
            controller = self.registry.get_component(entity, AgentController)
            
            if controller.current_intent and controller.current_intent["type"] == "move":
                target_x = controller.current_intent["data"]["x"]
                target_y = controller.current_intent["data"]["y"]
                
                if pos.x < target_x: pos.x += 1
                elif pos.x > target_x: pos.x -= 1
                elif pos.y < target_y: pos.y += 1
                elif pos.y > target_y: pos.y -= 1
                
                if pos.x == target_x and pos.y == target_y:
                    print(f"Agent {controller.agent_id} reached destination!")
                    controller.current_intent = None

def print_grid(engine: WorldEngine, width: int, height: int):
    # Clear screen
    os.system('cls' if os.name == 'nt' else 'clear')
    
    grid_display = [["." for _ in range(width)] for _ in range(height)]
    
    entities = engine.registry.get_entities_with(Position)
    for e in entities:
        pos = engine.registry.get_component(e, Position)
        if 0 <= pos.x < width and 0 <= pos.y < height:
            if engine.registry.has_component(e, AgentController):
                grid_display[pos.y][pos.x] = "@" # Agent
            elif engine.registry.has_component(e, Interactable):
                grid_display[pos.y][pos.x] = "C" # Computer/Object
            else:
                grid_display[pos.y][pos.x] = "X"
                
    for row in grid_display:
        print(" ".join(row))
    print(f"Tick: {engine.tick_count}")

def run_demo():
    print("Starting Grid World Demo...")
    engine = WorldEngine({"grid_width": 20, "grid_height": 10})
    engine.registry.register_system(SimpleMovementSystem())
    
    # Spawn a computer object
    computer = engine.spawn_entity()
    engine.registry.add_component(computer, Position(15, 5, 0))
    engine.registry.add_component(computer, Interactable(["work", "play_games"]))
    
    # Spawn the agent
    agent = AgentInterface(engine, "Avatar_01")
    
    print_grid(engine, 20, 10)
    time.sleep(1)
    
    # Agent perceives world
    perception = agent.perceive(vision_radius=20)
    print(f"\nAgent perceives {len(perception.entities)} objects.")
    for desc in perception.describe_surroundings():
        print(f" - Found object {desc['entity_id']} at distance {desc['distance']} with affordances {desc.get('affordances', [])}")
    
    print("\nAgent deciding to move to Computer...")
    time.sleep(2)
    
    # Instruct agent to move to (14, 5) - adjacent to computer
    agent.submit_intent("move", data={"x": 14, "y": 5})
    
    # Run loop
    while agent.check_intent_status() is not None:
        engine.run_simulation_step()
        print_grid(engine, 20, 10)
        time.sleep(0.3)
        
    print("\nSimulation complete!")

if __name__ == "__main__":
    run_demo()
