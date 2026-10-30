# Intent Log Entry

**Date:** 2026-10-30  
**Agent:** ChatGPT GPT-6  
**Session:** chatgpt-gpt6-2026-10-30-legacy-world-archive  
**OTOI Version:** ORG-DEV-OTOI-1.0.3  
**Working repo:** NeuroLift-Technologies/nlt-ai-fusion  
**Branch:** chore/archive-legacy-world-engine

## Action

Preserve superseded physical-world implementations under `archive/legacy-world-engine/`, remove their active entrypoints and runtime references, and align the README and architecture documentation with the Godot-owned physical simulation boundary.

## Rationale

The sibling `nlt-world-engine` Godot 4.7.2 project is the sole physical simulation authority. Keeping a Python ECS world, Cloudflare Durable Object world, browser-side world simulation, and legacy Sims API active creates competing physical authorities and ambiguous state ownership.

The Avatar–Aide cognitive training workflow, session orchestration, trait models, Aide expertise, model adapters, readiness assessment, and Advocate fusion logic are retained.

## Scope

- Archive Python physical-world ECS, world-specific NPCs, network client, demo, and coupled tests.
- Archive Cloudflare Durable Object world implementations and Wrangler entrypoints.
- Archive browser-only world prototype, old Sims viewer route/components, and world3d demo.
- Archive the legacy FastAPI `/api/world` router/schema/test and remove its registration from the compatibility API.
- Update Fusion package exports, README, Quick Start, architecture, implementation summary, backend docs, CI/mypy references, and repo agent context.
- Preserve `SessionOrchestrator`, `src/simulation/scenarios/`, and the current Fusion agent-loop.

## Risks and mitigations

- **Risk:** Active cognitive training code imports legacy world modules. **Mitigation:** Keep the session orchestrator and training scenario modules in place, remove legacy exports from `src/simulation/__init__.py`, and archive only the world-specific modules.
- **Risk:** Web clients may still call `/api/world`. **Mitigation:** Archive the old route and its dedicated UI route/components together; retain the homepage's sibling World Engine section.
- **Risk:** Wrangler dependencies remain in the root lockfile. **Mitigation:** Keep them temporarily and document that lockfile regeneration is a separate verified task.
- **Risk:** Documentation may overstate integration. **Mitigation:** State that local opt-in agent-loop works, remote transport is not established, and the embodied experience-to-learning bridge remains open.

## Alternatives considered

1. Delete the old code — rejected because it destroys provenance and historical reference material.
2. Keep old runtime code in place but label it deprecated — rejected because imports, API routes, browser routes, and deployment entrypoints remain discoverable.
3. Archive the code and remove active references — selected as reversible and consistent with the single-authority Godot architecture.

## Escalation

No new provider, external integration, database, or production deployment is introduced. Human review is required before merge. The archive does not modify the sibling repository or deploy anything.
