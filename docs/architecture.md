# AI-Fusion Architecture

**Status:** Current architecture baseline  
**Date:** 2026-10-30  
**Owner:** Joshua W. Dorsey, Sr.  
**Prepared by:** ChatGPT (GPT-6)  
**Governance:** ORG-DEV-OTOI-1.0.3

## 1. Repository responsibility

`nlt-ai-fusion` is the cognitive intelligence, learning, and application layer of the NeuroLift embodied-AI platform. It does not own the authoritative physical simulation.

| Responsibility | Authoritative location |
|---|---|
| Physical world, spatial state, time, physics, movement, objects, NPC execution, scenario instantiation | `nlt-world-engine` (Godot 4.7.2) |
| Avatar trait models and experiential behavior | `nlt-ai-fusion` |
| Aide expertise, coaching, and intervention policy | `nlt-ai-fusion` |
| Session orchestration, learning records, readiness assessment, and fusion logic | `nlt-ai-fusion` |
| Advocate capability produced from a trained Avatar–Aide pair | `nlt-ai-fusion` |
| Physical execution governance | Godot-side ASFDK-C# boundary in `nlt-world-engine` |
| Human-facing representation of the Godot world | World Engine Reviewer in `nlt-world-engine` |

**Authority rule:** Godot owns physical reality. Fusion owns cognitive semantics and learning. The Reviewer represents and observes the Godot world; it is not another simulator or an intelligence layer. Fusion does not communicate with or control the Reviewer.

## 2. Avatar–Aide–Advocate model

The two source systems are the Avatar and Aide.

- **Avatar:** develops experiential understanding through embodied challenges, mistakes, consequences, and recovery.
- **Aide:** contributes domain expertise, coaching, and intervention strategies. It supports Avatar development without replacing Avatar agency.
- **Advocate:** the result of fusing the trained Avatar–Aide pair. It is not a third independent agent inserted between the two source systems.

The 20-pair roster is a canonical catalog, not evidence that all 20 pairs have been fully implemented, trained, or validated. Implementation and readiness claims must be backed by current pair-level evidence.

## 3. Godot ↔ Fusion control boundary

The versioned contract is `nlt.agent-loop.v1`.

```text
Godot physical perception
        ↓
Fusion semantic decision
        ↓
Godot ASFDK governance and physical validation
        ↓
Godot execution and physical consequences
        ↓
Next perception
```

Godot sends agent-specific physical facts: self state, scene context, visible entities, and affordances. Fusion returns semantic intents such as `approach`, `look_at`, `use`, `sit`, `rest`, `communicate`, or `wait`.

Fusion does not return coordinates, velocity, teleportation commands, or direct world-state writes. Godot applies ASFDK-C# at intent ingress and independently validates physical preconditions before executing an action.

### Current integration status

- Fusion's decision seam is implemented in `src/fusion/agent_loop.py`.
- The local HTTP adapter is `src/fusion/agent_loop_http.py`, exposing `POST /agent-loop/perception`.
- Deterministic, GGUF, and Transformers decision sources are supported by configuration.
- The opt-in local Godot 4.7.2 loop has been exercised in a headless/interactive test path.
- The endpoint is loopback-only. A secure remote transport is not implied by the local integration and remains future work.
- The agent loop is not yet the same workflow as `SessionOrchestrator`; embodied experience-to-learning updates and subsequent Advocate fusion still need an explicit, tested bridge.

The separate `nlt.state-feed.v1` observer protocol must remain distinct from the control loop. The Reviewer consumes the physical representation/state feed; it does not participate in Fusion decision-making.

## 4. Fusion internals

| Module | Responsibility |
|---|---|
| `src/avatars/` | Avatar base behavior and trait-specific implementations |
| `src/aides/` | Aide base behavior, expertise, coaching, and interventions |
| `src/fusion/agent_loop.py` | Validates perception and produces semantic intent |
| `src/fusion/agent_loop_http.py` | Local HTTP adapter for the agent-loop |
| `src/fusion/readiness_assessor.py` | Assesses whether a pair meets fusion-readiness criteria |
| `src/fusion/fusion_engine.py` | Constructs fusion results and Advocate capabilities |
| `src/advocates/` | Advocate interfaces and resulting capabilities |
| `src/simulation/session_orchestrator.py` | Cognitive training-session orchestration, not physical world simulation |
| `src/simulation/scenarios/` | Scenario/task definitions for the cognitive training workflow |
| `apps/api/`, `apps/web/`, `apps/mobile/` | Application surfaces |

`SessionOrchestrator` and the Godot agent loop currently represent related but distinct execution paths. Do not claim the live embodied loop automatically persists learning or trains an Advocate unless that integration is implemented and tested.

## 5. Runtime and persistence boundaries

- Godot owns transient authoritative world state and physical consequences.
- Fusion owns cognitive decision-making, coaching, session-level learning records, readiness evaluation, and fusion artifacts.
- Application persistence and external services remain explicit adapters; a Supabase migration or the presence of a schema does not prove that every runtime path uses it.
- No credential, user-data, or remote-inference integration should be introduced without applicable OTOI approval and privacy controls.

## 6. Retired implementations

Superseded physical-world implementations are preserved under [`archive/legacy-world-engine/`](../archive/legacy-world-engine/README.md), including the Python ECS/grid world, Cloudflare Durable Object ECS/grid runtime, browser-only World Engine prototype, old `/world` Sims viewer, Python WebSocket client, legacy `/api/world` backend router, and documentation specific to those runtimes.

These files are historical reference only. They are not import paths, supported APIs, deployable runtimes, or sources of physical truth.

## 7. Architectural invariants

1. **Capability ≠ authority.** Fusion may propose semantic intent; Godot owns physical execution.
2. **One physical source of truth.** No Python or Cloudflare world runtime competes with Godot.
3. **Reviewer is a projection.** It represents Godot state and does not own simulation or intelligence.
4. **Two source systems, one fusion result.** Advocate emerges from the trained Avatar–Aide pair.
5. **Escalate, do not guess.** Material changes to authority boundaries, transport, persistence, or model-provider commitments require human approval.
6. **Evidence before claims.** Distinguish catalogued, prototyped, implemented, trained, and validated capabilities.
