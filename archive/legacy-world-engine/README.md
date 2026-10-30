# Archived Legacy World Engine Implementations

**Archived:** 2026-10-30  
**Reason:** The physical simulation authority is the Godot-based `nlt-world-engine` repository. AI-Fusion owns cognition, learning, and semantic intent generation, not a competing physical world runtime.

## Contents

This directory preserves historical code and documentation that previously implemented or depended on parallel physical simulation systems:

- `cloudflare-engine/`: Cloudflare Durable Object ECS/grid simulation, WebSocket gateway, package and Wrangler configuration.
- `src/simulation/environment/`: Python ECS/grid WorldEngine, physical components, time, relationships, scheduling, and the original scenario catalogue source.
- `backend/app/routers/world.py` and `backend/app/schemas/world.py`: legacy REST API and schemas for the Python world.
- `src/simulation/network_client.py`: WebSocket client for the retired Cloudflare Worker.
- `src/simulation/training_session.py` and old scripts: legacy training/demo entrypoints, including known broken paths.
- `prototypes/world-engine/` and `docs/specs/world-engine-prototype-schema.md`: standalone browser simulation prototype and its schema.
- `world3d/`: Three.js client for the former Cloudflare Worker.
- `tests/test_simulation/`: tests that exclusively exercised the retired Python physical simulation.
- Legacy build/implementation summaries: retained as historical records, not current status.

## Active replacements

| Archived implementation | Current owner or replacement |
|---|---|
| Python ECS/grid world | Godot 4.7.2 in sibling `nlt-world-engine` |
| Cloudflare Durable Object world | Godot World Engine; no active Cloudflare simulation runtime |
| Python world REST router | Removed from the legacy backend's active router registration |
| Cloudflare WebSocket client | `nlt.agent-loop.v1` semantic HTTP boundary for the local integration test |
| Browser React/Three.js simulations | Godot World Engine plus the World Engine Reviewer |
| Legacy Python scenario module | Active cognitive catalogue at `src/simulation/scenario_catalog.py` |

## Preservation and operational status

These files are preserved for history, comparison, and selective code archaeology. They are not supported runtime entrypoints and must not be imported by active code.

Moving source into this archive does not undeploy or decommission any already-running Cloudflare Worker, alter Vercel resources, or change external infrastructure. Those operations require a separate explicit decision and operational verification.

Do not copy the archived Python ECS or Cloudflare simulation back into active paths. Any new physical simulation behavior belongs in `nlt-world-engine`; cognitive models and semantic decisions belong in `nlt-ai-fusion`.
