# World Engine Prototype — Data Schema

**Source:** `prototypes/world-engine/data.js`
**Consumed by:** `prototypes/world-engine/{sim,hud,world-view,app}.jsx`
**Status:** Design spec — frontend prototype only. Not yet wired to the Python `WorldEngine` (`src/simulation/environment/world_engine.py`).
**Last updated:** 2026-05-26

This document is the canonical schema for the browser-side World Engine prototype shipped under `prototypes/world-engine/`. It is intentionally kept separate from the Python simulation engine so the two can be reconciled later through an API contract.

---

## Top-level namespace

```js
window.WE_DATA = { AVATARS, AIDES, SCENARIOS, ROOMS, NPCS, STRATEGIES, EVENT_KINDS }
```

All consumers read from this single global. No async loading, no API calls.

---

## Invariants

The prototype assumes (and the data file is validated against) these cross-references:

| Invariant | Where enforced |
|---|---|
| Every `AVATARS[i].id` has a matching key in `AIDES` | `sim.jsx` looks up `WE.AIDES[a.id]` during coaching |
| Every `AVATARS[i].flavor` is a key in `STRATEGIES` | `sim.jsx` picks from `WE.STRATEGIES[a.flavor]` |
| Every `SCENARIOS[i].room` is a `ROOMS[id]` | `sim.jsx` routes the avatar to a room on scenario start |
| Every `NPCS[i].room` is a `ROOMS[id]` | `sim.jsx` filters NPCs by avatar's current room for interruptions |
| Avatar `id` values are unique | implicit, used as React keys |

---

## Avatar

The 20-avatar roster (14 Executive Function, 6 Non-Executive Function), matching the canonical roster in the top-level `README.md`. The ids `stay_alert` and `task_kickstart` align directly with the Python implementations in `src/avatars/adhd_traits/`; the remaining 18 are design proposals.

```ts
type Avatar = {
  id: string;          // snake_case, unique. Matches src/avatars/adhd_traits/ where implemented.
  name: string;        // PascalCase display name
  trait: string;       // human-readable trait label
  tag: string;         // 2-char chip badge
  hue: number;         // 0-360, drives avatar color + accent
  flavor: FlavorKey;   // selects bias table in sim.jsx and STRATEGIES key
  blurb: string;       // one-line trait description
};
```

### FlavorKey

```
'attention' | 'initiation' | 'impulse' | 'memory' | 'time' | 'emotion'
| 'focus' | 'frustration' | 'planning' | 'transition' | 'monitor'
| 'fatigue' | 'effort' | 'stress' | 'sensory' | 'social' | 'identity'
```

The flavor maps into `FLAVOR_BIAS` in `sim.jsx`:

```ts
type FlavorBias = {
  drift: number;       // probability multiplier for FOCUS_DRIFT
  hyperfocus: number;  // probability multiplier for HYPERFOCUS_ENTER
  stress: number;      // multiplier for stress accumulation
  resist?: number;     // initiation-specific
  blurt?: number;      // impulse-specific
};
```

### Canonical roster

| # | id | trait | flavor |
|---|---|---|---|
| 1 | `stay_alert` | Sustained Attention | attention |
| 2 | `impulse_guard` | Impulsivity Control | impulse |
| 3 | `focus_flow` | Hyperfocus Management | focus |
| 4 | `timely` | Time Blindness | time |
| 5 | `memory_mate` | Working Memory | memory |
| 6 | `mood_ease` | Emotional Regulation | emotion |
| 7 | `task_kickstart` | Task Initiation | initiation |
| 8 | `calm_core` | Frustration Tolerance | frustration |
| 9 | `planner_pro` | Prioritization & Planning | planning |
| 10 | `smooth_switch` | Transition Difficulty | transition |
| 11 | `aware_mate` | Self-Monitoring | monitor |
| 12 | `steady_mind` | Habit-Loop Control | impulse |
| 13 | `focus_recharge` | Focus Fatigue | fatigue |
| 14 | `effort_align` | Effort vs. Output | effort |
| 15 | `stress_shield` | Stress Sensitivity | stress |
| 16 | `sensory_balance` | Sensory Sensitivity | sensory |
| 17 | `social_sync` | Social Challenges | social |
| 18 | `sensory_seeker` | Sensory Seeking | sensory |
| 19 | `confidence_coach` | Self-Esteem & Identity | identity |
| 20 | `rsd_shield` | Rejection Sensitivity | emotion |

Rows 1-14 are Executive Function; rows 15-20 are Non-Executive Function.

---

## Avatar runtime state

`spawnAvatar(def, room)` in `sim.jsx` extends each `Avatar` definition with the runtime fields below. Use this as the contract for any future API that streams avatar state into the prototype.

```ts
type AvatarRuntime = Avatar & {
  state: 'idle' | 'working' | 'drifting' | 'hyperfocus' | 'overwhelmed' | 'coached';
  emotional: 'focused' | 'energized' | 'calm' | 'neutral' | 'tense' | 'frustrated' | 'overwhelmed' | 'flat';
  focus: number;          // 0-1
  cogLoad: number;        // 0-1
  stress: number;         // 0-1
  burnout: number;        // 0-1
  independence: number;   // 0-1, grows with training
  fusionReady: number;    // 0-1, Avatar → Advocate progression
  successRate: number;    // EMA of scenario success
  scenarioId: string | null;
  elapsed: number;        // sim minutes in current scenario
  expected: number;       // expected scenario duration in minutes
  interventions: number;
  successes: number;
  failures: number;
  room: RoomId;
  px: number; py: number;     // current tile
  tx: number; ty: number;     // target tile
  facing: 'north' | 'south' | 'east' | 'west';
};
```

---

## Aide

```ts
type Aide = {
  name: string;    // display name (Coach/Dr. + surname)
  style: string;   // coaching modality
  focus: string;   // short list of techniques (` · ` separator)
};

type Aides = Record<AvatarId, Aide>;  // keyed by avatar id, 1:1
```

Each avatar has exactly one paired Aide. Aide names may repeat across avatars where the same coach has expertise in multiple traits.

---

## Scenario

Mirrors `src/simulation/environment/scenarios.py:Scenario` with compressed field names. Scenario IDs use the same prefix convention (`wp_*`, `pers_*`, `soc_*`, `acad_*`).

```ts
type Scenario = {
  id: string;
  name: string;
  cat: 'workplace' | 'personal' | 'social' | 'academic';
  room: RoomId;
  desc: string;
  minutes: number;       // expected duration
  complexity: 'low' | 'medium' | 'high';
  aversive: number;      // 0-1, dispreference
  cog: number;           // 0-1, cognitive demand
  base: number;          // 0-1, baseline success rate
  sustained: boolean;    // requires sustained focus
  ctx: Record<string, unknown>;
};
```

| Python field (`scenarios.py`) | JS field (`data.js`) |
|---|---|
| `scenario_id` | `id` |
| `name` | `name` |
| `category.value` | `cat` |
| `description` | `desc` |
| `expected_duration` (timedelta) | `minutes` (number) |
| `complexity` | `complexity` |
| `aversiveness` | `aversive` |
| `cognitive_demand` | `cog` |
| `base_success_rate` | `base` |
| `requires_sustained_focus` | `sustained` |
| `context` | `ctx` |
| _new_ | `room` (routing target) |

---

## Room

```ts
type RoomId = 'office' | 'meeting' | 'home' | 'phone' | 'lounge';

type Room = {
  id: RoomId;
  name: string;
  x: number; y: number;     // top-left tile in iso world grid
  w: number; h: number;     // tile dimensions
  color: string;            // accent hex
  floor: string;            // floor tile hex
  props: Prop[];
};

type Prop = {
  kind: 'desk' | 'monitor' | 'chair' | 'plant' | 'whiteboard' | 'longtable'
      | 'screen' | 'sofa' | 'tv' | 'counter' | 'fridge' | 'phone' | 'table';
  x: number; y: number;     // tile coords relative to room origin
  w?: number; h?: number;   // multi-tile props (default 1×1)
};
```

World grid is 24 × 18 logical tiles in iso projection (32 × 16 screen px per tile, see `world-view.jsx`).

---

## NPC

```ts
type NPC = {
  id: string;
  name: string;
  role: 'manager' | 'coworker' | 'friend' | 'stranger' | 'family' | 'phone caller';
  room: RoomId;
  biased: boolean;          // affects stress impact on interruption
  x: number; y: number;     // tile coords relative to room origin
  hue: number;              // visual accent
  invisible?: boolean;      // off-screen presence (e.g. phone caller)
};
```

NPCs are placed inside a room and only interact with avatars currently in that room.

---

## Strategy

```ts
type Strategies = Record<FlavorKey, string[]>;
```

Each flavor maps to a list of coaching technique labels. `sim.jsx` picks one at random when an Aide intervenes.

---

## Event

The tick loop emits events through `mkEvent(kind, avatar, text, scenarioId?, who?, meta?)` in `sim.jsx`.

```ts
type EventKind =
  | 'TASK_START' | 'FOCUS_DRIFT' | 'FOCUS_RECOVER'
  | 'HYPERFOCUS_ENTER' | 'HYPERFOCUS_EXIT'
  | 'NPC_INTERRUPT' | 'NPC_REACTION'
  | 'COACHING_INTERVENTION' | 'STRATEGY_APPLIED'
  | 'STRESS_SPIKE' | 'COGNITIVE_LOAD_HIGH' | 'BURNOUT_RISK'
  | 'CHECKPOINT_PASSED' | 'TASK_COMPLETE' | 'TASK_FAIL'
  | 'TICK' | 'ENTITY_MOVED' | 'INDEPENDENCE_GAIN';

type Event = {
  id: string;            // unique
  t: number;             // wall-clock ms
  kind: EventKind;
  text: string;
  avatarId: string;
  avatarName: string;
  avatarHue: number;
  who?: string;          // NPC or Aide name, if relevant
  scenarioId?: string;
  strategy?: string;     // COACHING_INTERVENTION only
  effectiveness?: number; // 0-1, COACHING_INTERVENTION only
};
```

### Mapping to Python `SignalType`

Future wiring should preserve this mapping (`src/core/events.py`):

| Prototype `EventKind` | Python `SignalType` |
|---|---|
| `TASK_START` | `SCENARIO_STARTED` |
| `TASK_COMPLETE` | `AVATAR_TASK_COMPLETED` / `SCENARIO_COMPLETED` |
| `TASK_FAIL` | `AVATAR_TASK_FAILED` |
| `FOCUS_DRIFT`, `STRESS_SPIKE`, `COGNITIVE_LOAD_HIGH` | `AVATAR_STRUGGLING` + `AVATAR_STATE_CHANGED` |
| `HYPERFOCUS_ENTER` / `_EXIT` | `AVATAR_STATE_CHANGED` |
| `BURNOUT_RISK` | `AVATAR_BURNOUT_WARNING` / `AVATAR_BURNOUT` |
| `NPC_INTERRUPT`, `NPC_REACTION` | `NPC_INTERACTION` |
| `COACHING_INTERVENTION` | `AIDE_COACHING_DELIVERED` |
| `STRATEGY_APPLIED` | `AIDE_STRATEGY_ADAPTED` |
| `INDEPENDENCE_GAIN` | `AVATAR_INDEPENDENCE_MILESTONE` |
| `ENTITY_MOVED` | `ENVIRONMENT_CHANGED` |
| `TICK` | `EventType.TICK` (engine-internal) |

---

## Tweaks (live tuning)

`app.jsx` declares the editable tweak surface via the `EDITMODE-BEGIN/END` marker:

```ts
type Tweaks = {
  selectedAvatar: string;
  timeScale: number;          // 0.25 – 6.0
  tickHz: number;             // 1 – 12
  dysfunctionOn: boolean;     // gate for trait-driven dysfunction injection
  theme: 'dark' | 'light' | 'brand';
  density: 'comfortable' | 'compact';
  accent: [string, string];   // [primary, secondary]
  urgencyThreshold: number;   // 0.2 – 0.95
  showLabels: boolean;
};
```

---

## Open questions for wiring

When the prototype is later wired to the Python engine, these decisions are still owed:

1. **Source of truth for avatars** — does the JS roster become canonical, or does the Python generate it (e.g., from `src/avatars/avatar_configs/*.json`)? Only `stay_alert.json` exists today; the other 18 configs would need to be authored.
2. **Scenario synchronization** — `scenarios.py` defines 13 scenarios with no spatial layout; `data.js` defines 11 with `room` routing. Pick one, generate the other.
3. **Transport** — REST snapshot polling, Server-Sent Events, or WebSocket via the existing Cloudflare Durable Object (`cloudflare-engine/src/index.ts`).
4. **State serialization boundary** — runtime state (`AvatarRuntime`) currently lives only in the JS sim. The Python `BaseAvatar` has overlapping but not identical fields (`emotional_state`, `cognitive_load`, `stress_level`, `current_focus`); a shared DTO needs to be defined before wire-up.
