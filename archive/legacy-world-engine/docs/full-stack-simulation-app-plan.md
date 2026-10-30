# Full-Stack Simulation App Plan (Web + Android + iOS)

## Objective

Evolve `neurolift-ai-fusion` from a Python-first simulation codebase into a product-ready full-stack platform with:

- a web application,
- a shared mobile app (Android + iOS),
- and a simulation API layer backed by existing Python domain logic.

## Current implementation baseline (source-verified 2026-04-30)

- **API starter live** in `services/api/app/` using FastAPI and the existing `SessionOrchestrator`.
- **Web starter live** in `apps/web/` with a static HTML/JavaScript console that calls `/health` and `/sessions/demo-run`.
- **Mobile starter live** in `apps/mobile/` as an Expo app for Android and iOS that calls `/health` and `/sessions/demo-run`.
- **Shared SDK starter live** in `packages/simulation-sdk/` with TypeScript contracts and a source-only client wrapper for `/health` and `POST /sessions/run`.

## Target Monorepo Layout

```text
apps/
  web/                  # Browser app (participant + coach dashboards)
  mobile/               # Cross-platform mobile app (Android/iOS)
services/
  api/                  # Simulation API (session orchestration, auth, telemetry)
packages/
  simulation-sdk/       # Shared contracts/types/client SDK for app consumption
src/                    # Existing Python simulation domain (current engine)
```

## Product Surface Areas

### 1) Web App (`apps/web`)
- session setup and scenario launch
- live simulation timeline and interventions
- post-session review with progress metrics

### 2) Mobile App (`apps/mobile`)
- run and review sessions on Android/iOS
- in-session prompts and coaching nudges
- push notifications for reflection checkpoints

### 3) API Layer (`services/api`)
- secure APIs for session creation, retrieval, and analytics
- gateway between clients and `src/` simulation domain
- event ingestion and audit-ready logs

### 4) Shared Contracts (`packages/simulation-sdk`)
- API request/response schemas
- event models used by web + mobile
- typed client utilities to reduce drift across frontends

## Migration Phases

1. **Foundation (complete):** repository cleanup + app/service/package scaffolding.
2. **Starter implementation (complete):** API + web + mobile + SDK starter code connected.
3. **API hardening:** authentication, persistence integration, and robust error contracts.
4. **Product UX:** richer web/mobile flows for session management and analytics.
5. **Convergence:** unified telemetry, identity, and release workflows across all surfaces.

## Verified starter contracts

| Surface | Source path | Public contract |
| --- | --- | --- |
| API routes | `services/api/app/main.py` | `GET /health`, `GET /sessions/demo-run`, `POST /sessions/run` |
| API schemas | `services/api/app/schemas.py` | `ScenarioInput`, `SessionRunRequest`, `SessionRunResponse` |
| Simulation adapter | `services/api/app/session_service.py` | Runs `StayAlertAvatar` + `AttentionCoaching` through `SessionOrchestrator` |
| Static web console | `apps/web/index.html`, `apps/web/main.js` | Buttons for API health and demo session calls |
| Expo mobile starter | `apps/mobile/App.tsx` | Buttons for API health and demo session calls |
| SDK contracts | `packages/simulation-sdk/src/types.ts` | TypeScript request/response shapes mirroring Pydantic models |
| SDK client | `packages/simulation-sdk/src/client.ts` | `health()` and `runSession(payload)` fetch wrappers |

### Important constraints

- The API starter has no authentication, persistence, CORS middleware, or background job queue yet.
- The current API adapter labels runs with `avatar_id` and `aide_id`, but it always instantiates the sustained-attention `StayAlertAvatar` and `AttentionCoaching` pair.
- The static web console reads `window.NEUROLIFT_API_URL` or falls back to `http://localhost:8000`; CORS must be added before cross-origin browser calls are production-ready.
- The Expo app reads `EXPO_PUBLIC_API_URL` or falls back to `http://localhost:8000`; device/emulator networking may need a LAN or emulator-specific host.
- The SDK is source-only in this baseline; there is no package manifest, build output, or publish workflow under `packages/simulation-sdk/`.

## Guardrails for Implementation

- Keep provider-agnostic AI integration boundaries.
- Preserve human-in-the-loop review for critical decisions.
- Keep simulation domain in `src/` as source-of-truth during migration.
- Avoid direct client access to persistence layers; use service APIs.
