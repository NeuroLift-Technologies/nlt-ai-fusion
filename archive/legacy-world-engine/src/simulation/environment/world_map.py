"""
Spatial World Map

Manages the discrete grid system for the simulation.
Provides spatial indexing, queries (e.g., finding nearby entities),
and pathfinding for agents navigating the environment.
"""

from typing import List, Dict, Tuple, Optional, Set
import heapq
from .ecs import Registry, Position, Entity

class GridManager:
    """
    Manages a discrete 2D grid representation of the world.
    Responsible for bounds checking, spatial queries, and pathfinding.
    """
    
    def __init__(self, width: int = 100, height: int = 100, registry: Optional[Registry] = None):
        self.width = width
        self.height = height
        self.registry = registry
        
    def in_bounds(self, x: int, y: int) -> bool:
        """Check if coordinates are within the grid bounds."""
        return 0 <= x < self.width and 0 <= y < self.height

    def get_entities_at(self, x: int, y: int) -> List[Entity]:
        """Find all entities currently at a specific coordinate."""
        if not self.registry:
            return []
            
        result = []
        # In a highly optimized engine, we'd use a 2D array or quadtree for indexing.
        # For simplicity, we iterate over entities with Position components.
        entities_with_pos = self.registry.get_entities_with(Position)
        for entity in entities_with_pos:
            pos = self.registry.get_component(entity, Position)
            if pos and pos.x == x and pos.y == y:
                result.append(entity)
        return result

    def get_entities_in_radius(self, center_x: int, center_y: int, radius: int) -> List[Entity]:
        """Find all entities within a Chebyshev distance radius (square radius)."""
        if not self.registry:
            return []
            
        result = []
        entities_with_pos = self.registry.get_entities_with(Position)
        for entity in entities_with_pos:
            pos = self.registry.get_component(entity, Position)
            if pos:
                # Chebyshev distance (max of x and y differences)
                dist = max(abs(pos.x - center_x), abs(pos.y - center_y))
                if dist <= radius:
                    result.append(entity)
        return result

    def is_walkable(self, x: int, y: int) -> bool:
        """
        Determine if a grid cell can be walked into.
        Returns False if out of bounds or occupied by a blocking entity.
        """
        if not self.in_bounds(x, y):
            return False
            
        entities = self.get_entities_at(x, y)
        for entity in entities:
            # We assume anything interactable is a solid object for now.
            # In a full system, we'd have a 'Collider' component.
            if self.registry and self.registry.has_component(entity, __import__('src.simulation.environment.ecs', fromlist=['Interactable']).Interactable):
                return False
                
        return True

    def find_path(self, start_x: int, start_y: int, goal_x: int, goal_y: int) -> List[Tuple[int, int]]:
        """
        A* pathfinding implementation on the 2D grid.
        Returns a list of (x, y) coordinates representing the path, or empty list if no path.
        """
        if not self.in_bounds(start_x, start_y) or not self.in_bounds(goal_x, goal_y):
            return []
            
        # Optimization: If the goal itself is occupied, we pathfind to a walkable adjacent tile.
        # But standard A* checks goal walkability. If goal is solid, we can't reach it.
        # To handle walking *up to* an interactable, the agent should goal to an adjacent cell.
        
        frontier: List[Tuple[float, int, int]] = []
        heapq.heappush(frontier, (0, start_x, start_y))
        came_from: Dict[Tuple[int, int], Optional[Tuple[int, int]]] = {}
        cost_so_far: Dict[Tuple[int, int], float] = {}
        
        start = (start_x, start_y)
        goal = (goal_x, goal_y)
        
        came_from[start] = None
        cost_so_far[start] = 0.0
        
        while frontier:
            _, current_x, current_y = heapq.heappop(frontier)
            current = (current_x, current_y)
            
            if current == goal:
                break
                
            # Check neighbors (4-way movement)
            neighbors = [
                (current_x + 1, current_y),
                (current_x - 1, current_y),
                (current_x, current_y + 1),
                (current_x, current_y - 1)
            ]
            
            for next_x, next_y in neighbors:
                next_node = (next_x, next_y)
                
                # Check walkability (unless it is the goal itself, maybe we want to walk TO a solid object)
                if not self.is_walkable(next_x, next_y) and next_node != goal:
                    continue
                    
                new_cost = cost_so_far[current] + 1.0 # Cost is 1 per step
                
                if next_node not in cost_so_far or new_cost < cost_so_far[next_node]:
                    cost_so_far[next_node] = new_cost
                    priority = new_cost + self._heuristic(goal_x, goal_y, next_x, next_y)
                    heapq.heappush(frontier, (priority, next_x, next_y))
                    came_from[next_node] = current
                    
        # Reconstruct path
        if goal not in came_from:
            return [] # No path found
            
        path = []
        current = goal
        while current != start:
            path.append(current)
            current = came_from[current]  # type: ignore[assignment]
        path.append(start)
        path.reverse()
        
        return path[1:] # Return path excluding the start node

    def _heuristic(self, x1: int, y1: int, x2: int, y2: int) -> float:
        """Manhattan distance heuristic for A*."""
        return abs(x1 - x2) + abs(y1 - y2)
