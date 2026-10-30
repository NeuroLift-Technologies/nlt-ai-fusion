# Legacy World Engine Archive

**Archive date:** 2026-10-30  
**Disposition:** Preserved, not active  
**Replacement:** `NeuroLift-Technologies/nlt-world-engine` (Godot 4.7.2)

This directory preserves superseded implementations and documentation from earlier attempts to host or render the physical world inside `nlt-ai-fusion`. The archive is intentionally retained for provenance, historical research, and selective code reference.

## Why these files were archived

The platform now has one authoritative physical simulation: the Godot World Engine in the sibling `nlt-world-engine` repository. Fusion owns cognition, learning, coaching, model adapters, and Avatar–Aide fusion. A Python ECS, Cloudflare Durable Object world, or browser-side simulation would create competing physical authorities and ambiguous state ownership.

## Archived contents

| Archive area | Historical contents |
|---|---|
| `python/` | Python ECS/grid WorldEngine, spatial map, time/schedule/relationship components, legacy NPC model, WebSocket client, demo script, and tests coupled to those implementations |
| `cloudflare-root/` | Root Wrangler entrypoint and Durable Object ECS/grid implementation |
| `cloudflare-engine/` | Separate Cloudflare Durable Object World Engine implementation and Wrangler package |
| `web/` | Browser-only React world prototype, old Sims-style `/world` route/components, and `world3d` demo |
| `backend/` | Old FastAPI `/api/world` router, response schemas, and endpoint tests |
| `docs/` | Design specs and deployment/migration plans specific to the retired physical-world implementations |
| `historical/` | Earlier implementation summaries that describe the retired architecture |

## Usage rules

- Do not import archived Python modules into active code.
- Do not deploy archived Wrangler projects or treat their WebSocket endpoint as the current observer feed.
- Do not use the archived browser prototype or `/world` page as the World Engine Reviewer.
- Do not restore the old `/api/world` endpoint as a competing physical state API.
- If a concept or algorithm is worth reusing, port it deliberately into the correct owner repository and update its contract/tests.

## What remains active in Fusion

The cognitive training workflow remains in `src/simulation/session_orchestrator.py` and `src/simulation/scenarios/`. Avatar, Aide, Advocate, readiness, fusion, and agent-loop modules remain active. The local `nlt.agent-loop.v1` endpoint returns semantic intents only; Godot applies ASFDK-C# governance and owns physical execution.

## Dependency cleanup note

The root JavaScript lockfile still contains the historical Wrangler toolchain dependencies. They were not removed in this archival change because lockfile regeneration requires a package-manager install/verification pass. They are not an active World Engine deployment contract.
