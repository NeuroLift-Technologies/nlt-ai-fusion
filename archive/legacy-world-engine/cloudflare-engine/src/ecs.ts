/**
 * Entity Component System (ECS) in TypeScript
 * Designed to run in a Cloudflare Durable Object.
 */

export class Component {
  // Base class or interface for components
}

export class Entity {
  id: string;
  constructor(id?: string) {
    this.id = id || crypto.randomUUID();
  }
}

export abstract class System {
  registry!: Registry;
  setRegistry(registry: Registry) {
    this.registry = registry;
  }
  abstract update(deltaTime: number): void;
}

export class Registry {
  private entities: Set<Entity> = new Set();
  // Map of ComponentName -> { EntityID -> ComponentInstance }
  private components: Map<string, Map<string, any>> = new Map();
  private systems: System[] = [];

  addEntity(entity: Entity) {
    this.entities.add(entity);
  }

  removeEntity(entity: Entity) {
    this.entities.delete(entity);
    for (const [_, entityMap] of this.components) {
      entityMap.delete(entity.id);
    }
  }

  addComponent<T extends Component>(entity: Entity, componentName: string, component: T) {
    if (!this.components.has(componentName)) {
      this.components.set(componentName, new Map());
    }
    this.components.get(componentName)!.set(entity.id, component);
  }

  getComponent<T>(entity: Entity, componentName: string): T | undefined {
    return this.components.get(componentName)?.get(entity.id) as T | undefined;
  }

  hasComponent(entity: Entity, componentName: string): boolean {
    return this.components.get(componentName)?.has(entity.id) || false;
  }

  getEntitiesWith(...componentNames: string[]): Entity[] {
    const result: Entity[] = [];
    for (const entity of this.entities) {
      const hasAll = componentNames.every(name => this.hasComponent(entity, name));
      if (hasAll) {
        result.push(entity);
      }
    }
    return result;
  }

  registerSystem(system: System) {
    system.setRegistry(this);
    this.systems.push(system);
  }

  tick(deltaTime: number) {
    for (const system of this.systems) {
      system.update(deltaTime);
    }
  }
}

// --- Standard Core Components ---

export class Position extends Component {
  constructor(public x: number = 0, public y: number = 0, public z: number = 0) {
    super();
  }
}

export class Interactable extends Component {
  constructor(public affordances: string[] = [], public inUseBy: string | null = null) {
    super();
  }
}

export class AgentController extends Component {
  public currentIntent: any | null = null;
  public intentProgress: number = 0;
  constructor(public agentId: string) {
    super();
  }
}
