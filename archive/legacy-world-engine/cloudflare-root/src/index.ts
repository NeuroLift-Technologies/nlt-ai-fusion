import { Registry, Entity, Position, AgentController, System } from "./ecs";
import { GridManager } from "./world_map";

export interface Env {
  WORLD_ENGINE: DurableObjectNamespace;
}

interface SessionAttachment {
  agentId: string;
  entityId: string;
}

/**
 * Basic Movement System
 */
class MovementSystem extends System {
  update(deltaTime: number): void {
    const agents = this.registry.getEntitiesWith("Position", "AgentController");
    for (const entity of agents) {
      const pos = this.registry.getComponent<Position>(entity, "Position")!;
      const controller = this.registry.getComponent<AgentController>(entity, "AgentController")!;

      if (controller.currentIntent && controller.currentIntent.type === "move") {
        const targetX = controller.currentIntent.data.x;
        const targetY = controller.currentIntent.data.y;

        if (pos.x < targetX) pos.x++;
        else if (pos.x > targetX) pos.x--;
        else if (pos.y < targetY) pos.y++;
        else if (pos.y > targetY) pos.y--;

        if (pos.x === targetX && pos.y === targetY) {
          controller.currentIntent = null; // Arrived
        }
      }
    }
  }
}

/**
 * The Durable Object that runs the World Engine
 */
export class WorldEngineDO {
  private state: DurableObjectState;
  private env: Env;
  private registry: Registry;
  private grid: GridManager;
  private sessions: Set<WebSocket> = new Set();
  private entityById: Map<string, Entity> = new Map();
  private tickInterval: ReturnType<typeof setInterval> | null = null;
  private tickCount: number = 0;

  constructor(state: DurableObjectState, env: Env) {
    this.state = state;
    this.env = env;

    // Initialize ECS
    this.registry = new Registry();
    this.registry.registerSystem(new MovementSystem());
    this.grid = new GridManager(100, 100, this.registry);

    // Setup initial world
    const spawnEntity = new Entity();
    this.registry.addEntity(spawnEntity);
    this.registry.addComponent(spawnEntity, "Position", new Position(0, 0, 0));

    // Restore any connected websocket sessions after hibernation.
    this.restoreSessions();

    // Start tick loop
    this.startTickLoop();
  }

  private restoreSessions() {
    for (const ws of this.state.getWebSockets()) {
      this.sessions.add(ws);
      const attachment = ws.deserializeAttachment() as SessionAttachment | null;
      if (attachment) {
        this.ensureAgentEntity(attachment);
      }
    }
  }

  private ensureAgentEntity(attachment: SessionAttachment): Entity {
    const existing = this.entityById.get(attachment.entityId);
    if (existing) {
      return existing;
    }

    const entity = new Entity(attachment.entityId);
    this.entityById.set(entity.id, entity);
    this.registry.addEntity(entity);
    this.registry.addComponent(entity, "Position", new Position(0, 0, 0));
    this.registry.addComponent(
      entity,
      "AgentController",
      new AgentController(attachment.agentId)
    );
    return entity;
  }

  private removeAgentEntity(attachment: SessionAttachment) {
    const entity = this.entityById.get(attachment.entityId);
    if (!entity) {
      return;
    }

    this.registry.removeEntity(entity);
    this.entityById.delete(attachment.entityId);
  }

  private startTickLoop() {
    if (this.tickInterval !== null) return;

    // Tick every 1 second (1000ms)
    // Stop the loop when nobody is connected so the object can go idle cleanly.
    this.tickInterval = setInterval(() => {
      if (this.sessions.size === 0) {
        if (this.tickInterval !== null) {
          clearInterval(this.tickInterval);
          this.tickInterval = null;
        }
        return;
      }

      this.registry.tick(1.0);
      this.tickCount++;
      this.broadcastState();
    }, 1000);
  }

  private broadcastState() {
    const agents = this.registry.getEntitiesWith("Position", "AgentController");
    const agentStates = agents.map(e => {
      const pos = this.registry.getComponent<Position>(e, "Position")!;
      const ctrl = this.registry.getComponent<AgentController>(e, "AgentController")!;
      return { id: ctrl.agentId, pos: { x: pos.x, y: pos.y }, busy: ctrl.currentIntent !== null };
    });

    const msg = JSON.stringify({
      type: "tick",
      tickCount: this.tickCount,
      agents: agentStates
    });

    for (const ws of this.state.getWebSockets()) {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(msg);
      }
    }
  }

  async fetch(request: Request): Promise<Response> {
    const upgradeHeader = request.headers.get("Upgrade");
    if (upgradeHeader !== "websocket") {
      return new Response("Expected Upgrade: websocket", { status: 426 });
    }

    const [client, server] = Object.values(new WebSocketPair());

    this.state.acceptWebSocket(server);
    this.sessions.add(server);

    const url = new URL(request.url);
    const agentId =
      url.searchParams.get("agentId") ||
      "Unknown_" + Math.floor(Math.random() * 1000);
    const attachment: SessionAttachment = {
      agentId,
      entityId: crypto.randomUUID()
    };

    server.serializeAttachment(attachment);
    this.ensureAgentEntity(attachment);
    this.startTickLoop();

    return new Response(null, {
      status: 101,
      webSocket: client
    });
  }

  async webSocketMessage(ws: WebSocket, message: string | ArrayBuffer) {
    const attachment = ws.deserializeAttachment() as SessionAttachment | null;
    if (!attachment) {
      ws.send(JSON.stringify({ type: "error", error: "Missing session attachment" }));
      return;
    }

    const entity = this.ensureAgentEntity(attachment);

    try {
      const raw =
        typeof message === "string"
          ? message
          : new TextDecoder().decode(message);
      const data = JSON.parse(raw);

      if (data.type === "intent") {
        const ctrl = this.registry.getComponent<AgentController>(
          entity,
          "AgentController"
        );
        if (ctrl) {
          ctrl.currentIntent = data.intent;
        }
        return;
      }

      if (data.type === "perceive") {
        const pos = this.registry.getComponent<Position>(entity, "Position");
        if (pos) {
          const nearby = this.grid.getEntitiesInRadius(
            pos.x,
            pos.y,
            data.radius || 10
          );
          ws.send(
            JSON.stringify({
              type: "perception",
              nearby: nearby.length
            })
          );
        }
        return;
      }

      ws.send(JSON.stringify({ type: "error", error: "Unsupported message type" }));
    } catch (err) {
      console.error("WebSocket message error:", err);
      ws.send(JSON.stringify({ type: "error", error: "Invalid message payload" }));
    }
  }

  async webSocketClose(ws: WebSocket, code: number, reason: string) {
    this.sessions.delete(ws);
    const attachment = ws.deserializeAttachment() as SessionAttachment | null;
    if (attachment) {
      this.removeAgentEntity(attachment);
    }

    if (ws.readyState === WebSocket.OPEN) {
      ws.close(code, reason);
    }
  }
}

/**
 * Worker Entry Point
 * Routes incoming requests to the Durable Object
 */
export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    
    if (url.pathname === "/connect") {
      // Create or get the single World Engine instance
      const id = env.WORLD_ENGINE.idFromName("global-world-engine");
      const obj = env.WORLD_ENGINE.get(id);
      return obj.fetch(request);
    }

    return new Response("World Engine Gateway. Connect via WS to /connect?agentId=XXX");
  }
};
