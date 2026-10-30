# AI-Fusion Space — architecture and service boundaries

**Runtime:** `spaces/ai-fusion/` (Docker Space, port 7860)
**Source of truth:** `NeuroLift-Technologies/nlt-ai-fusion`
**Governance:** ORG-DEV-OTOI-1.0.3

## 1. What runs in the Space

```mermaid
flowchart LR
  subgraph Godot["nlt-world-engine (Godot 4.7.2)"]
    P[Physical perception] --> A[ASFDK-C# at intent ingress]
    A --> V[Physical validation]
    V --> X[Execution + consequences]
  end

  subgraph Space["AI-Fusion Space (this runtime)"]
    S[agent-loop seam<br/>/agent-loop/perception]
    R[AgentRegistry<br/>Avatar + Aide pairs]
    D[Decision source<br/>baseline | gguf | transformers]
    F[FusionEngine + ReadinessAssessor]
    O[SessionOrchestrator<br/>/v1/sessions]
    G[Governance context<br/>capability gate]
    S --> G --> R --> D --> S
    R --> F
    R --> O
  end

  X --> P
  P -->|perception| S
  S -->|intent only| A
  F -->|one-way state feed| RD[Renderer]
  API[NeuroLift API platform] -->|/v1/*| G
```

The Space serves three things and nothing else: semantic decisions for the agent loop,
Avatar/Aide fusion semantics, and the session loop that produces the experience those
semantics depend on.

## 2. Cognition preserved as-is

The runtime imports the existing implementations. It does not reimplement, wrap in a
generic agent framework, or collapse the three roles:

| Role | Implementation | Distinct responsibility preserved |
|---|---|---|
| **Avatar** (System 1) | `src/avatars/base_avatar.py`, `adhd_traits/stay_alert_avatar.py`, `adhd_traits/task_kickstart_avatar.py`, `adhd_traits/attention_deficit.py` | Trait-specific experience, struggle, attention energy, task attempts |
| **Aide** (System 2) | `src/aides/base_aide.py`, `coaching/stay_alert_aide.py`, `expertise/attention_expert.py`, `executive_function_expertise/attention_coaching.py` | Coaching strategy selection, intervention outcomes |
| **Advocate** | `src/advocates/base_advocate.py` + `FusionEngine.fuse()` output | The *result* of a trained pair; not a third agent inserted between them |
| **ADHD / executive-function modelling** | `adhd_traits/*`, trait configs (`avatar_configs/stay_alert.json`, `aide_configs/stay_alert_aide.json`) | Trait parameters loaded from JSON at startup, unchanged |
| **Training / evaluation / adaptation** | `src/simulation/session_orchestrator.py`, `scenarios/`, `scenario_catalog.py`, `src/ai/trainer.py`, `src/ai/dataset.py` | Observe → coach → retry loop; `fusion_ready` is an outcome, not a flag |
| **Model adapters / inference orchestration** | `src/ai/registry.py`, `protocol.py`, `adapters/{rule_fallback,openai_compat,transformer_policy}.py`, `fusion/{gguf,transformers}_agent_decision.py` | Provider-agnostic backends; the Space binds one at startup via `FUSION_AGENT_LOOP_MODEL` |

`/v1/fusion/agents` returns pairs the registry actually built (`stay_alert_001` today) and
`/v1/fusion/readiness` asks the real `ReadinessAssessor`, so a fabricated capability cannot
be served: `/v1/fusion/attempt` on an untrained pair returns `success: false` with
`Not ready. Blocking dimensions: [...]`.

## 3. World Engine boundary

| Concern | Authority | In this runtime |
|---|---|---|
| World state, space, time, physics, collisions, affordances' physical truth | `nlt-world-engine` (Godot) | never read, never written |
| Rendering | Reviewer / Godot client | Fusion only *publishes* the state feed; it consumes nothing visual |
| Semantic decision | **Fusion** | `POST /agent-loop/perception` → `intent` |
| Intent verbs | Contract `nlt.agent-loop.v1` | `approach`, `look_at`, `use`, `sit`, `rest`, `communicate`, `wait` — no coordinates, no velocity, no object writes |
| ASFDK governance, live-world revalidation, execution | **Godot intent ingress** | not implemented here; carried as context only |
| Shared service contracts | NeuroLift API platform | `/v1/*` with governance headers |

The `agent-loop` app is mounted unchanged (`create_app` from
`src/fusion/agent_loop_http.py`), which keeps the contract's own guarantees: unknown
`agentId` → 404, duplicate in-flight → 429, timeout → 503 plus model quarantine,
malformed envelope → 422, and nothing in a response that could be mistaken for physical
state.

## 4. Governance on every non-contract route

Default is `NLT_GOVERNANCE_MODE=enforce`. Every `/v1/*` route requires a context that
carries identity, session, provenance and a capability grant:

| Header | Meaning |
|---|---|
| `X-NLT-Agent-Id` | Calling service identity |
| `X-NLT-Session-Id` | Session the action belongs to |
| `X-NLT-Provenance` | Build/version lineage of the caller (`nlt-api/1.0.0`) |
| `X-NLT-Governance-Version` | Governance version the caller operates under (must match `NLT_GOVERNANCE_VERSION`) |
| `X-NLT-Capabilities` | Comma-separated grants: `fusion.read`, `fusion.fuse`, `fusion.session.run`, `runtime.info` |

Rules the implementation enforces, in order:

1. Reaching the endpoint is not authorization: a request with no context gets
   `403 governance_context_missing`.
2. Identity without a capability gets `403 capability_not_granted` naming the missing grant.
3. A governance version the runtime does not accept gets `403 governance_version_unsupported`.
4. Every successful response echoes the context it acted on, so a downstream service can
   attribute the work.
5. `NLT_GOVERNANCE_MODE=permissive` (local development only) never masquerades as
   authorization: responses carry `governance_enforced: false` and an empty context.

`/agent-loop/*` is the one exception, and deliberately so: that seam is the frozen
`nlt.agent-loop.v1` contract, it is called by Godot where ASFDK already gates the intent,
and its own threat model (registry allow-list, one-in-flight, quarantine) is part of the
contract. Changing it here would fork the contract; the conflict is recorded below (C7).

## 5. Data and storage separation

| Data class | Where it lives | Durable? | Rule |
|---|---|---|---|
| Runtime state (in-flight decisions, quarantine, agent memory) | process memory | no | Lost on restart by design; the contract documents that a restart clears agent memory |
| Simulation observations (perceptions) | Godot → this runtime, request-scoped | no | Never persisted; contains physical state Fusion does not own |
| Training datasets | external object storage / Supabase (operator-supplied) | **yes** | Not baked into the image; the Space mounts nothing for it |
| Evaluation results and fusion reports | `/data` artifacts + external store when configured | partial | `/data` is a Space bucket, suitable for artifacts, not a system of record |
| Model checkpoints | `/data/models` (`NEUROLIFT_MODELS_DIR`) | **yes** | The only reason `/data` is writable; readiness fails if it is not |
| Configuration and metadata | Space *Variables* and *Secrets* | yes | Secrets never in git, never echoed — `Settings.describe()` reports only booleans |

The Space filesystem is ephemeral outside `/data`. Anything that must survive a rebuild
belongs in Supabase/object storage behind configuration, which is why the runtime reports
`supabase_configured` instead of pretending state is durable.

## 6. Architectural conflicts — reported, not silently resolved

| # | Conflict | Evidence | Why this work did not "fix" it |
|---|---|---|---|
| **C1** | **Three overlapping Python API surfaces**: `apps/api` (avatars/aides/sessions/advocates), `backend/app` (avatars/aides/sessions/scenarios/fusion/ai/health), `services/api` (sessions/run + demo-run) | `CLAUDE.md` calls `backend/app` legacy and points at `apps/api`, but `services/api/README.md` calls itself *the* service boundary; `apps/api` is the thinnest of the three | Retiring an API surface is a product/integration decision with client impact (web, mobile, Neon/API platform). The Space reuses `services/api.app.session_service` and exposes a `/v1` path, leaving the three apps untouched |
| **C2** | `apps/api/routers/sessions.py` imports modules that do not exist: `src.avatars.stay_alert_avatar`, `src.avatars.task_kickstart_avatar` (real paths are `src/avatars/adhd_traits/…`) | `PYTHONPATH=. python -c "import src.avatars.stay_alert_avatar"` → `ModuleNotFoundError`; no test covers that router, so CI stays green | Fixing it changes the app the web/mobile clients may still call; the failure is latent only because nothing exercises it |
| **C3** | `backend/app/routers/fusion.py` fabricates readiness: `readiness_score = round(random.uniform(0.5, 1.0), 3)` and stores fusions in a module-level dict | Direct read of the router; the real `ReadinessAssessor` lives in `src/fusion/readiness_assessor.py` and is unused by every HTTP surface | Replacing it changes a live endpoint's semantics; `/v1/fusion/attempt` now serves the real engine in parallel |
| **C4** | `src/simulation/npcs/` (NPC disposition/reaction) has a test but no runtime consumer | Only `tests/test_simulation/test_base_npc.py` references it | Excluded from the Space and flagged: either it is dead code, or a scenario feature is unwired |
| **C5** | Governance version drift: `config/global-toi-config.json` says `otoi.version = "1.2.0"`, while `NLT-DEV-OTOI.md`, `CLAUDE.md` and every doc say `ORG-DEV-OTOI-1.0.3` | File read | The runtime accepts 1.0.3 (the documented contract). Which file is canonical is Joshua's call |
| **C6** | `TrainingPipeline.run_async` starts a bare thread inside the serving process; there is no queue, no persistence of the run, and no completion signal | `src/ai/trainer.py`; `backend/app/routers/ai.py` exposes it as `POST /train` returning `training_started` | Exposing that over HTTP in a Space would invite a training request on ephemeral storage. Left unexposed here, reported as a design gap |
| **C7** | The `nlt.agent-loop.v1` seam is **ungoverned by this runtime's capability gate** — it is authenticated by network position (loopback) and gated by ASFDK at Godot ingress | `docs/agent-loop-model-adapter.md`, `src/fusion/agent_loop_http.py` | Adding a header requirement would fork a frozen cross-repo contract; the Space keeps the seam verbatim and documents the exposure |
| **C8** | The state feed carries `position` and `velocity` per agent (currently `0,0,0` placeholders) even though physics is Godot's | `src/fusion/state_feed.py` output, asserted in `tests/test_runtime.py::test_state_feed_is_published_not_received` | The contract `nlt-world-engine/docs/contracts/state-feed-v1.md` is owned jointly; unilaterally dropping fields would break the renderer. Flagged for the contract owner |

Each of these is a decision for the repository owner, not something a deployment should
quietly settle.
