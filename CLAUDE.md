# CLAUDE.md — Repository Context for AI Agents

**Repository:** `NeuroLift-Technologies/nlt-ai-fusion`  
**Governance:** ORG-DEV-OTOI-1.0.3  
**Last updated:** 2026-10-30

> This repository owns the AI-Fusion cognitive layer. The authoritative physical simulation lives in sibling `NeuroLift-Technologies/nlt-world-engine` and runs on Godot 4.7.2.

## What this repository is

AI-Fusion implements the Avatar–Aide–Advocate cognitive and learning platform:

- **Avatars** model trait-specific experience, task behavior, and learning.
- **Aides** provide domain expertise, coaching strategies, and intervention feedback.
- **Advocates** represent the fused capabilities of a trained Avatar–Aide pair.
- **Fusion** owns readiness assessment, fusion results, model adapters, and semantic decision-making.
- **Session orchestration** coordinates task/scenario-level Avatar–Aide observe/coach/retry workflows.

The Advocate is the result of the trained Avatar–Aide pair, not a third independent agent.

## System boundaries

- `nlt-world-engine` / Godot owns physical reality: world state, space, time, physics, movement, objects, affordances, and physical consequences.
- This repository owns cognitive intelligence and learning.
- ASFDK-C# governance and physical validation occur at the Godot intent-ingress boundary.
- The World Engine Reviewer observes and represents Godot world state. It is not a simulation authority or AI decision-maker.
- Fusion does not interact with the Reviewer.

Do not reintroduce a Python ECS world, Cloudflare Durable Object world, or browser-based simulation as a competing physical runtime. Historical implementations are preserved under `archive/legacy-world-engine/` and must not be imported by active code.

## Repository structure

- `src/avatars/` — Avatar foundations and trait implementations.
- `src/aides/` — Aide foundations, coaching, and expertise.
- `src/advocates/` — Advocate interfaces and support behavior.
- `src/fusion/` — Readiness, fusion, agent-loop validation, HTTP adapter, and model decision sources.
- `src/simulation/session_orchestrator.py` — Current task/scenario-level Avatar–Aide orchestration.
- `src/simulation/scenario_catalog.py` — Reusable cognitive/task scenario catalogue.
- `src/simulation/scenarios/` — Multi-step scenario abstractions.
- `src/core/` — Shared events and core infrastructure.
- `src/ai/` — Model interfaces, registry, and training support.
- `src/database/` — Persistence abstractions and database clients.
- `apps/api/` — FastAPI application surface.
- `apps/web/` — Next.js web application.
- `apps/mobile/` — Expo mobile application.
- `tests/` — Active Python test suite.
- `docs/` — Architecture, protocols, implementation status, governance, and handoffs.
- `archive/legacy-world-engine/` — Preserved historical simulation code; not an active runtime.

The `backend/app` tree is a legacy API surface. Its former `/world` router was removed from active routing because it depended on the retired Python WorldEngine. Prefer the documented `apps/api/` surface for current application work unless a task explicitly targets the legacy backend.

## Technology stack

| Layer | Technology |
|---|---|
| Cognitive runtime | Python 3.11+ |
| API | FastAPI |
| Web | Next.js + TypeScript |
| Mobile | Expo / React Native |
| Database | Supabase / PostgreSQL where explicitly integrated |
| Testing | pytest |
| CI/CD | GitHub Actions |
| Supporting infrastructure | Cloudflare DNS, security, CDN, and approved edge services |
| Physical simulation | Godot 4.7.2 in sibling `nlt-world-engine` |

## Commands

### Python

```bash
python -m pip install -r requirements.txt
pytest
pytest tests/test_simulation/test_session_orchestrator.py
pytest tests/test_fusion
```

### API

```bash
cd apps/api
pip install -r requirements.txt
PYTHONPATH=../../src uvicorn main:app --reload --port 8000
```

### Web

```bash
cd apps/web
corepack enable
pnpm install --frozen-lockfile
pnpm dev
pnpm run build
pnpm run lint
```

### Mobile

```bash
cd apps/mobile
npm install
npx expo start
```

### Local agent-loop test

The Fusion HTTP endpoint is a local development/test adapter for `nlt.agent-loop.v1`. See `QUICKSTART.md` and `docs/agent-loop-model-adapter.md`. Do not expose the loopback endpoint publicly or assume the current local path is a production remote transport.

## Architectural invariants

1. **Physical authority:** Godot owns physical state and consequences.
2. **Semantic boundary:** Fusion returns constrained semantic intents, never direct physical state writes or coordinates.
3. **Governance:** Godot applies ASFDK-C# at intent ingress and independently validates physical execution.
4. **Cognitive ownership:** Avatar experience, Aide expertise, and Advocate fusion live in AI-Fusion.
5. **Advocate identity:** Advocate is the resulting fused capability of the trained Avatar–Aide pair, not an independent third source model.
6. **Observer separation:** Reviewer is an observer/representation, not an integration surface for Fusion.
7. **Learning evidence:** Inference is not training. Claim learning only when behavior change, persistence, and evaluation are demonstrated.
8. **Human sovereignty:** Human authority and OTOI approval requirements remain binding.

## Development conventions

- Follow PEP 8 and use type hints on public interfaces.
- Add tests for behavioral changes.
- Use absolute imports from the `src/` package root.
- Avoid circular imports and implicit cross-layer dependencies.
- Keep model-provider selection configurable; do not hardcode provider lock-in.
- Never commit credentials, API tokens, private keys, or local model weights.
- Do not add external service integrations, change persistence architecture, or alter deployment architecture without Joshua's explicit approval.
- Do not modify canonical governance files without the formal amendment process.

## Required reading

Before development, read:

1. `NLT-DEV-OTOI.md`
2. `AGENTS.md`
3. `CLAUDE.md`
4. `docs/active-threads.md`
5. `docs/architecture.md`

Follow OTOI §4.1: work on a feature branch and submit changes through a Pull Request. Never push directly to `main` or another protected branch.

## Handoff requirements

For significant work:

- Update `docs/active-threads.md`.
- Write an agent registration under `docs/agent-log/registrations/`.
- Write a handoff under `docs/agent-log/handoffs/`.
- Record important intent and architectural risks under `docs/agent-log/intent/`.
- Use ISO 8601 timestamps with UTC offset.
- Use commit format: `[AGENT_NAME] type(scope): description`.

---

*Repository context for AI agents | NeuroLift Technologies | ORG-DEV-OTOI-1.0.3*
