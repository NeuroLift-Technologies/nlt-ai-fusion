/**
 * NeuroLift World Engine Worker
 *
 * Cloudflare Durable Object that runs the simulation world engine.
 * Handles WebSocket connections for real-time agent interaction,
 * spatial queries via GridManager, and entity movement via MovementSystem.
 */
import { Registry, Entity, Position, AgentController, Interactable, System } from "./ecs";
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

    // Build the world: rooms, furniture, sims
    this.buildWorld();

    // Restore any connected websocket sessions after hibernation.
    this.restoreSessions();

    // Start tick loop
    this.startTickLoop();
  }

  private buildWorld(): void {
    // Rooms with furniture (name, needEffects[6])
    // needs order: hunger, hygiene, bladder, energy, social, fun
    const rooms: Array<{ name: string; furniture: Array<{ name: string; effects: [number, number, number, number, number, number]; pos: [number, number] }> }> = [
      {
        name: "bedroom",
        furniture: [
          { name: "bed", effects: [-1, -1, -1, 3, -1, -1], pos: [2, 1] },
          { name: "night stand", effects: [0, 0, 0, 0, 0, 0], pos: [3, 1] },
          { name: "alarm clock", effects: [0, 0, 0, 0, 0, -1], pos: [3, 2] },
          { name: "dresser", effects: [0, 0, 0, 0, 0, 0], pos: [1, 3] },
        ],
      },
      {
        name: "kitchen",
        furniture: [
          { name: "fridge", effects: [5, 0, -1, 0, 0, 1], pos: [5, 1] },
          { name: "stove", effects: [4, 0, 0, 0, 0, 1], pos: [6, 1] },
          { name: "sink", effects: [0, 2, 0, 0, 0, 0], pos: [7, 1] },
          { name: "counter", effects: [0, 0, 0, 0, 0, 0], pos: [5, 2] },
          { name: "coffee maker", effects: [2, 0, -3, 3, 0, 0], pos: [6, 2] },
          { name: "table", effects: [3, 0, -1, 0, 0, 1], pos: [5, 3] },
        ],
      },
      {
        name: "living room",
        furniture: [
          { name: "couch", effects: [0, 0, 0, 1, 0, 0], pos: [9, 1] },
          { name: "tv", effects: [0, -1, 0, 0, 0, 3], pos: [10, 1] },
          { name: "laptop", effects: [0, 0, 0, -1, 0, 5], pos: [9, 2] },
          { name: "music stereo", effects: [0, 0, 0, 0, 0, 3], pos: [10, 2] },
          { name: "coffee table", effects: [0, 0, 0, 0, 0, 0], pos: [9, 3] },
        ],
      },
      {
        name: "bathroom",
        furniture: [
          { name: "toilet", effects: [0, 0, 5, 0, 0, 0], pos: [12, 1] },
          { name: "shower", effects: [0, 5, 0, 0, 0, 0], pos: [13, 1] },
          { name: "bathtub", effects: [0, 5, 0, 0, 0, 1], pos: [12, 2] },
          { name: "mirror", effects: [0, 0, 0, 0, 0, 0], pos: [13, 2] },
        ],
      },
      {
        name: "office",
        furniture: [
          { name: "desk", effects: [0, 0, 0, 0, 0, 1], pos: [15, 2] },
          { name: "chair", effects: [0, 0, 0, 0, 0, 0], pos: [15, 3] },
          { name: "bookcase", effects: [0, 0, 0, 0, 0, 2], pos: [16, 2] },
          { name: "computer", effects: [0, 0, 0, -1, 0, 5], pos: [15, 1] },
        ],
      },
    ];

    // Spawn furniture into rooms
    for (const roomDef of rooms) {
      for (const furn of roomDef.furniture) {
        const entity = new Entity();
        this.registry.addEntity(entity);
        this.registry.addComponent(entity, "Position", new Position(furn.pos[0], furn.pos[1], 0));
        this.registry.addComponent(entity, "Furniture", { name: furn.name, effects: furn.effects, room: roomDef.name });
        this.registry.addComponent(entity, "Interactable", new Interactable([furn.name], null));
      }
    }

    // Spawn Sims with 6 needs each
    const simDefs = [
      { name: "Alex", room: "bedroom", pos: [2, 2] as [number, number] },
      { name: "Jamie", room: "living room", pos: [8, 2] as [number, number] },
    ];

    for (const simDef of simDefs) {
      const entity = new Entity();
      this.entityById.set(entity.id, entity);
      this.registry.addEntity(entity);
      this.registry.addComponent(entity, "Position", new Position(simDef.pos[0], simDef.pos[1], 0));
      this.registry.addComponent(entity, "AgentController", new AgentController(entity.id));
      this.registry.addComponent(entity, "SimNeeds", { hunger: 5, hygiene: 5, bladder: 5, energy: 5, social: 5, fun: 5 });
      this.registry.addComponent(entity, "SimName", { name: simDef.name });
    }
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
    const url = new URL(request.url);

    // CORS preflight
    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type",
        },
      });
    }

    // REST endpoint: world state
    if (url.pathname === "/api/world/state" && request.method === "GET") {
      return this.handleWorldState();
    }

    // REST endpoint: sim detail
    if (url.pathname.startsWith("/api/world/sims/") && request.method === "GET") {
      const simId = url.pathname.split("/").pop() || "";
      return this.handleSimDetail(simId);
    }

    // REST endpoint: list sims
    if (url.pathname === "/api/world/sims" && request.method === "GET") {
      return this.handleWorldState();
    }

    // REST endpoint: set speed
    if (url.pathname === "/api/world/time/speed" && request.method === "POST") {
      return this.handleSetSpeed(request);
    }

    // WebSocket upgrade
    const upgradeHeader = request.headers.get("Upgrade");
    if (upgradeHeader !== "websocket") {
      return new Response("Expected Upgrade: websocket", { status: 426 });
    }

    const [client, server] = Object.values(new WebSocketPair());

    this.state.acceptWebSocket(server);
    this.sessions.add(server);

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

  private handleWorldState(): Response {
    const sims = this.registry.getEntitiesWith("Position", "AgentController", "SimName", "SimNeeds");
    const entities = this.registry.getEntitiesWith("Position", "Furniture");

    const simResponses = sims.map(e => {
      const pos = this.registry.getComponent<Position>(e, "Position")!;
      const nameComp = this.registry.getComponent<any>(e, "SimName");
      const needsComp = this.registry.getComponent<any>(e, "SimNeeds");
      const needs = needsComp || { hunger: 5, hygiene: 5, bladder: 5, energy: 5, social: 5, fun: 5 };
      return {
        sim_id: e.id,
        name: nameComp?.name || e.id,
        position: { x: pos.x, y: pos.y, z: 0 },
        room: "world",
        current_activity: "idle",
        needs_summary: { hunger: needs.hunger, hygiene: needs.hygiene, bladder: needs.bladder, energy: needs.energy, social: needs.social, fun: needs.fun }
      };
    });

    const furnitureEntities = entities.filter(e => this.registry.hasComponent(e, "Furniture"));
    const roomMap = new Map<string, any[]>();
    for (const furnEnt of furnitureEntities) {
      const furn = this.registry.getComponent<any>(furnEnt, "Furniture");
      const pos = this.registry.getComponent<Position>(furnEnt, "Position")!;
      if (!roomMap.has(furn.room)) roomMap.set(furn.room, []);
      roomMap.get(furn.room)!.push({
        entity_id: furnEnt.id,
        furniture_type: furn.name,
        position: { x: pos.x, y: pos.y, z: 0 },
        affordances: [furn.name],
        in_use_by: null
      });
    }

    const rooms = Array.from(roomMap.entries()).map(([name, furniture]) => ({
      name,
      furniture,
      occupants: simResponses.filter((s: any) => s.room && s.room !== "world" && s.room === name).map((s: any) => s.name)
    }));

    const state = {
      simulation_id: "cf-world-engine",
      tick_count: this.tickCount,
      state: "running",
      config: { grid_width: 100, grid_height: 100, seconds_per_tick: 1, time_speed_multiplier: 1 },
      time: { day: 1, hour: 10, minute: 0, is_daytime: true, speed_multiplier: 1, speed_label: "realtime" },
      rooms,
      sims: simResponses,
      entities: entities.map((e: Entity) => {
        const pos = this.registry.getComponent<Position>(e, "Position")!;
        const comps: string[] = [];
        if (this.registry.hasComponent(e, "Furniture")) comps.push("Furniture");
        if (this.registry.hasComponent(e, "AgentController")) comps.push("AgentController");
        if (this.registry.hasComponent(e, "SimNeeds")) comps.push("SimNeeds");
        if (this.registry.hasComponent(e, "SimName")) comps.push("SimName");
        return { entity_id: e.id, position: { x: pos.x, y: pos.y, z: 0 }, components: comps };
      })
    };

    return new Response(JSON.stringify(state), {
      headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" }
    });
  }

  private handleSimDetail(simId: string): Response {
    const sims = this.registry.getEntitiesWith("Position", "AgentController", "SimName", "SimNeeds");
    const target = sims.find(e => e.id === simId);

    if (!target) {
      return new Response(JSON.stringify({ detail: "Sim not found" }), { status: 404 });
    }

    const pos = this.registry.getComponent<Position>(target, "Position")!;
    const nameComp = this.registry.getComponent<any>(target, "SimName");
    const needsComp = this.registry.getComponent<any>(target, "SimNeeds");
    const needs = needsComp || { hunger: 5, hygiene: 5, bladder: 5, energy: 5, social: 5, fun: 5 };

    return new Response(JSON.stringify({
      sim_id: simId,
      name: nameComp?.name || simId,
      position: { x: pos.x, y: pos.y, z: 0 },
      room: "world",
      current_activity: "idle",
      needs: { hunger: needs.hunger, hygiene: needs.hygiene, bladder: needs.bladder, energy: needs.energy, social: needs.social, fun: needs.fun },
      mood: "happy",
      weekend: false,
      relationships: [],
      schedule: { current_activity: "idle", weekend: false }
    }), { headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" } });
  }

  private async handleSetSpeed(request: Request): Promise<Response> {
    let body: any;
    try {
      body = await request.json();
    } catch {
      return new Response(JSON.stringify({ error: "Invalid JSON body" }), { status: 400, headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" } });
    }
    const speed = body.speed;
    const multipliers: Record<string, number> = { realtime: 1, fast: 5, ultra: 20, hyper: 100 };
    const mult = multipliers[speed] || 1;

    if (this.tickInterval) {
      clearInterval(this.tickInterval);
      this.tickInterval = null;
    }
    const interval = Math.max(100, 1000 / mult);
    this.tickInterval = setInterval(() => {
      if (this.sessions.size === 0 && this.tickInterval) {
        clearInterval(this.tickInterval);
        this.tickInterval = null;
        return;
      }
      this.registry.tick(1.0);
      this.tickCount++;
      this.broadcastState();
    }, interval);

    return new Response(JSON.stringify({
      previous_speed: 1,
      previous_label: "realtime",
      new_speed: mult,
      new_label: speed
    }), { headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" } });
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
    
    if (url.pathname === "/connect" || url.pathname.startsWith("/api/world")) {
      // Create or get the single World Engine instance
      const id = env.WORLD_ENGINE.idFromName("global-world-engine");
      const obj = env.WORLD_ENGINE.get(id);
      return obj.fetch(request);
    }

    return new Response("World Engine Gateway. Connect via WS to /connect?agentId=XXX", {
      headers: { "Access-Control-Allow-Origin": "*" }
    });
  }
};
