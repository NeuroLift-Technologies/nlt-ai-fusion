/**
 * Spatial Grid Map in TypeScript
 * Runs inside the Durable Object to manage spatial queries.
 */

import { Registry, Entity, Position, Interactable } from "./ecs";

export class GridManager {
  constructor(public width: number = 100, public height: number = 100, public registry: Registry) {}

  inBounds(x: number, y: number): boolean {
    return x >= 0 && x < this.width && y >= 0 && y < this.height;
  }

  getEntitiesInRadius(centerX: number, centerY: number, radius: number): Entity[] {
    const result: Entity[] = [];
    const entitiesWithPos = this.registry.getEntitiesWith("Position");

    for (const entity of entitiesWithPos) {
      const pos = this.registry.getComponent<Position>(entity, "Position");
      if (pos) {
        const dist = Math.max(Math.abs(pos.x - centerX), Math.abs(pos.y - centerY));
        if (dist <= radius) {
          result.push(entity);
        }
      }
    }
    return result;
  }

  isWalkable(x: number, y: number): boolean {
    if (!this.inBounds(x, y)) return false;

    const entitiesWithPos = this.registry.getEntitiesWith("Position");
    for (const entity of entitiesWithPos) {
      const pos = this.registry.getComponent<Position>(entity, "Position");
      if (pos && pos.x === x && pos.y === y) {
        if (this.registry.hasComponent(entity, "Interactable")) {
          return false; // Solid object
        }
      }
    }
    return true;
  }

  findPath(startX: number, startY: number, goalX: number, goalY: number): {x: number, y: number}[] {
    // Simplified A* or BFS for the worker.
    // For now, returning a direct line if walkable, to keep the DO bundle small.
    // A robust implementation would use a proper priority queue.
    const path: {x: number, y: number}[] = [];
    
    // Naive direct line pathfinding (Placeholder for full A*)
    let currX = startX;
    let currY = startY;
    let failsafe = 0;

    while ((currX !== goalX || currY !== goalY) && failsafe < 100) {
      failsafe++;
      let nextX = currX;
      let nextY = currY;

      if (currX < goalX) nextX++;
      else if (currX > goalX) nextX--;
      
      if (currY < goalY) nextY++;
      else if (currY > goalY) nextY--;

      // If we hit a wall before the goal, just stop
      if (!this.isWalkable(nextX, nextY) && (nextX !== goalX || nextY !== goalY)) {
        break;
      }

      currX = nextX;
      currY = nextY;
      path.push({x: currX, y: currY});
    }

    return path;
  }
}
