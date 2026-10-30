# AI-Fusion Space — repository audit and module classification

**Repository:** `NeuroLift-Technologies/nlt-ai-fusion` @ `3d087dc` (audited before any change)
**Space:** `divergent-tech/Ai-fusion` (Hugging Face, Docker SDK target)
**Date:** 2026-10-30
**Governance:** ORG-DEV-OTOI-1.0.3

This audit classifies every relevant module, package, script, configuration file and
dependency into the seven requested classes. **Nothing was deleted, archived or moved
during the audit.** The only files added by this work are the runtime in
`spaces/ai-fusion/` and this documentation set.

## 1. Inventory snapshot

| Measure | Count |
|---|---|
| Tracked files | 740 |
| Python files | 159 |
| TypeScript/TSX files | 99 |
| Python test modules (`tests/**/test_*.py`) | 37 |
| Docs files (`docs/**`) | 65 |
| GitHub workflows | 12 |
| Python API surfaces | 3 (`apps/api`, `backend/app`, `services/api`) |
| `requirements*.txt` files | 5 |

## 2. Classification

### Required for current runtime

| Path | Why it is runtime | Space |
|---|---|---|
| `src/avatars/` (`base_avatar.py`, `adhd_traits/*`, `avatar_configs/*.json`) | Avatar state, trait configs, experience memory — loaded at startup from JSON | deployed |
| `src/aides/` (`base_aide.py`, `coaching/`, `expertise/`, `executive_function_expertise/`, `aide_configs/*.json`) | Aide expertise and coaching strategies | deployed |
| `src/advocates/` (`base_advocate.py`) | Advocate result surface consumed by fusions | deployed |
| `src/fusion/` (`fusion_engine`, `readiness_assessor`, `model_fusion`, `state_feed`, `agent_loop*`) | The cognitive core: readiness, fusion, state feed, `nlt.agent-loop.v1` decision seam | deployed |
| `src/simulation/session_orchestrator.py`, `scenario_catalog.py`, `scenarios/` | Avatar–Aide observe/coach/retry loop that produces the experience readiness measures | deployed |
| `src/core/` (`events`, `protocols`, `state_machine`) | Event bus and shared contracts used by every module above | deployed |
| `services/api/app/session_service.py`, `schemas.py` | Canonical session-run service boundary; reused, not reimplemented | deployed |
| `src/avatars/avatar_configs/stay_alert.json`, `src/aides/aide_configs/stay_alert_aide.json` | The one fully implemented roster pair the endpoint registers | deployed |

### Required for training and evaluation

| Path | Why | Space |
|---|---|---|
| `src/ai/registry.py`, `protocol.py`, `trainer.py`, `dataset.py` | Model registry, training pipeline, held-out evaluation data | deployed (registry + protocol); `trainer` reachable via session `ai_config` |
| `src/ai/adapters/rule_fallback.py` | Deterministic baseline when no model is bound | deployed |
| `src/ai/adapters/openai_compat.py` | Remote provider adapter (stdlib `urllib`, provider-agnostic base URL) | deployed, inactive without config |
| `src/ai/adapters/transformer_policy.py` | Local transformer policy adapter | deployed, lazily imported |
| `src/fusion/transformers_agent_decision.py`, `gguf_agent_decision.py` | Local model decision sources selected by `FUSION_AGENT_LOOP_MODEL` | deployed, lazily imported |
| `requirements-ai.txt`, `requirements-gguf.txt` | Optional torch/transformers/llama.cpp wheels | **not** in base image (see §3) |
| `tests/test_fusion/*`, `tests/test_ai/*`, `tests/test_services/*` | The acceptance evidence for the modules above | repo-only (CI), not shipped |

### Required for World Engine integration

| Path | Why | Space |
|---|---|---|
| `src/fusion/agent_loop.py`, `agent_loop_http.py`, `agent_loop_registry.py`, `agent_loop_goals.py`, `agent_loop_memory.py`, `agent_loop_ranking.py`, `agent_loop_deadline.py`, `agent_loop_choices.py`, `agent_loop_baseline.py` | `nlt.agent-loop.v1` transport, envelope validation, per-agent registry, quarantine, goal/memory/ranking | deployed (mounted unchanged) |
| `src/fusion/state_feed.py` | One-way Fusion → renderer state feed | deployed |
| `src/simulation/npcs/` | NPC disposition/reaction model, used only by its unit test | **excluded** — no consumer in the loop; see §4 conflict C4 |

### Required for ASFDK governance

| Path | Why | Space |
|---|---|---|
| `spaces/ai-fusion/app/governance.py` (new) | Carries agent identity, session, provenance, governance version and capabilities; denies work that arrives without a grant | deployed |
| `config/global-toi-config.json` | Global TOI/OTOI settings (privacy, agency, override rights) | **not loaded** — see §4 conflict C5 |
| `scripts/validate_provenance.py` | Repository provenance validation used by CI (PGSA gate) | repo-only |
| `docs/architecture.md` §3, `docs/agent-loop-model-adapter.md` | The written contract for where ASFDK sits (Godot intent ingress) | repo-only |

ASFDK-C# enforcement and physical validation are *not* implemented in this repository;
they run at the Godot intent ingress. The Space therefore carries governance context and
capability gates, and deliberately does not pretend to enforce ASFDK.

### Development-only

| Path | Why | Space |
|---|---|---|
| `.github/workflows/*` (12 files) | CI: lint, tests, clearance levels, gitleaks, CodeQL, Hermes | repo-only |
| `apps/web/` (Next.js), `apps/mobile/` (Expo), `packages/simulation-sdk/` (source-only TS contracts) | Client surfaces; they call the API, they are not the runtime | excluded |
| `requirements.txt` (root) | Superset with `pandas`, `matplotlib`, `seaborn`, `sphinx`, `black`, `isort`, `flake8`, `mypy`, `pre-commit`, `pytest-*` | replaced by the 3-package `spaces/ai-fusion/requirements.txt` |
| `pytest.ini`, `mypy.ini`, `tsconfig.json`, `turbo.json`, `vercel.json`, `package.json` (root) | Tooling for the monorepo, not the runtime | repo-only |
| `scripts/run_clearance_tests.py`, `scan_secrets.py`, `test_cloudflare_access.py` | Operator/CI scripts | repo-only |
| `tests/**` (37 modules) | Verification, not runtime | repo-only |
| `supabase/migrations/*.sql` | Schema for the durable store, applied to Supabase, not to the Space | repo-only |
| `data/*/…_template.json` | JSON templates for training logs / progress / interactions | repo-only |

### Experimental or obsolete

| Path | Why | Disposition (documented, not deleted) |
|---|---|---|
| `backend/app/` (legacy FastAPI: `fusion`, `scenarios`, `ai`, `health` routers) | Declared legacy in `CLAUDE.md`; its `/world` router was retired with the Python WorldEngine. The `fusion` router is a **placeholder** (`random.uniform` readiness, in-memory store) | keep in repo, excluded from Space; superseded by `/v1/fusion/*` |
| `archive/legacy-world-engine/`, `archive/cloudflare/`, `archive/wordpress/`, `archive/azure-*`, `archive/business-structure/`, … | Historical runtimes and non-authoritative experiments; `CLAUDE.md` forbids importing them | keep archived; excluded |
| `apps/api/` thin surface | Superseded in practice by `services/api`; contains a **broken import** (see §4) | excluded from Space; conflict reported C1 |
| `src/ai/trainer.py` background thread | Usable but unqueued: `run_async` spawns a thread inside the process | deployed but not exposed; see C6 |

### Unclear — requires architectural review

| Path | Question |
|---|---|
| `src/database/supabase_client.py` + `supabase/migrations/` | Durable store is optional and unconfigured in the Space. Which entities must persist (sessions, experiences, fusion reports, provenance) versus stay ephemeral is a product decision — see the data section of the boundaries doc |
| `config/training_config.yaml`, `config/simulation_config.yaml` | Read by `src/utils/config_loader.py`, which no runtime path calls. Are they the intended source of training hyper-parameters? |
| `services/api/app/main.py` (its own FastAPI app with `/sessions/run`) | Duplicate of the Space route, and the third API surface. Retire one of them (C1) |
| `src/fusion/model_fusion.py` (`ModelFusionEngine`, trajectory distillation) | Real and tested, but has no HTTP surface and no selected student trainer beyond `NoOpStudentTrainer`. Deliberately not exposed yet: exposing an unqueued trainer over HTTP would be a lie about capability |

## 3. Dependency and compatibility assessment

### Minimum complete runtime set

`spaces/ai-fusion/requirements.txt` is three packages:

```
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
pydantic>=2.0.0
```

Justification, verified by importing the assembled payload with only these installed:
`src.fusion`, `src.avatars`, `src.aides`, `src.advocates`, `src.ai.registry`,
`src.ai.trainer`, `src.simulation` and `services.api.app.session_service` need nothing
else — `openai_compat` uses stdlib `urllib`, `supabase` is imported lazily, and torch /
transformers / llama-cpp are imported only inside the adapters that use them.

| Dependency | Runtime need | Decision |
|---|---|---|
| `fastapi`, `uvicorn`, `pydantic` | HTTP surface, ASGI server, schemas | required, pinned as ranges |
| `supabase` | Durable store | **optional** — not in the image; enabled by configuration when the persistence decision lands |
| `torch`, `transformers` (`requirements-ai.txt`) | `TransformersAgentLoopDecision`, `transformer_policy` | optional layer; a variant image, not the default (multi-GB) |
| `llama-cpp-python` (`requirements-gguf.txt`) | `LlamaCppAgentLoopDecision` | optional layer; needs a compiled wheel or build toolchain |
| `numpy`, `pandas`, `matplotlib`, `seaborn` | analysis notebooks, docs figures | not needed; excluded |
| `pytest`, `pytest-cov`, `pytest-asyncio`, `pytest-mock`, `pytest-xdist` | test harness | excluded from the image; tests run in CI against the repo |
| `black`, `isort`, `flake8`, `mypy`, `pre-commit`, `sphinx*` | dev/docs | excluded |
| Node/npm toolchain | web, mobile, TS SDK | not needed by the Space |

### Compatibility findings

1. **Python 3.11** is the repository's target (`apps/api/Dockerfile`, CI workflows) and
   what the Space image uses; the runtime code uses `X | None` typing and dataclasses, so
   3.9 is not supported.
2. **FastAPI lifecycle:** the Space uses a `lifespan` context manager, not the deprecated
   `@app.on_event`, so it runs on current FastAPI without deprecation noise.
3. **Model selection fails closed at startup:** an unknown `FUSION_AGENT_LOOP_MODEL`, or
   `gguf`/`transformers` selected without a model path, raises during boot. This is
   intentional (`docs/agent-loop-model-adapter.md`) and is why `baseline` is the default.
4. **No CPU/GPU assumption is baked in:** the Space requests `cpu-basic`; a GGUF or
   transformers layer would need an upgraded hardware request, recorded as a deployment
   variant rather than a code change.
5. **Config files are not read at runtime** except the roster JSONs that live inside
   `src/` — which is why the payload copies `src/` and not `config/`.

## 4. Missing runtime components (what had to be built)

| Missing | Evidence | Resolved by |
|---|---|---|
| Any HTTP surface for `FusionEngine` / `ReadinessAssessor` | No router imports `fusion_engine` or `readiness_assessor`; `backend/app/routers/fusion.py` computes `random.uniform(0.5, 1.0)` instead | `app/fusion_routes.py` (`/v1/fusion/*`) |
| Governance context carriage | No request schema carries agent identity, session, provenance or capabilities anywhere in `src/`, `apps/api/` or `services/` | `app/governance.py` + capability gates |
| Health and readiness | Only `/health` (no dependency checks) in `apps/api` and `backend/app` | `app/health.py` (`/health`, `/readyz`, `/v1/runtime/info`) |
| Space entrypoint / image | No Dockerfile or app entrypoint for Hugging Face; `apps/api/Dockerfile` builds the API surface but not the fusion runtime | `spaces/ai-fusion/{Dockerfile,app/main.py}` |
| Artifact/checkpoint handling | `NEUROLIFT_MODELS_DIR` defaults to `./data/models` inside the image (ephemeral) | `/data` volume default + readiness probe on writability |
| Reproducible deploy | Nothing assembled a deployable subset from the repo | `spaces/ai-fusion/sync-to-hub.sh` + `PAYLOAD_MANIFEST.txt` |

## 5. Not touched

No file outside `spaces/ai-fusion/` and `docs/space-runtime/` was modified by this work.
No archive was added or removed. The two defects found in existing code are reported
(below and in the boundaries doc) rather than fixed, because both change API surface the
team owns.
