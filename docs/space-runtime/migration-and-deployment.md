# AI-Fusion Space — migration and deployment plan

**Target:** `divergent-tech/Ai-fusion` (existing Space, currently `NO_APP_FILE`)
**Runtime:** `spaces/ai-fusion/` — Docker SDK, port 7860

## 1. Deployment structure

The Space does not mirror the repository. `spaces/ai-fusion/sync-to-hub.sh` assembles a
runtime payload; the assembled tree is what the image builds from:

```
(assembled payload = Space repo root)
├── README.md                 # Space card (sdk: docker, app_port: 7860) + operator docs
├── Dockerfile                # python:3.11-slim, non-root uid 1000, HEALTHCHECK
├── requirements.txt          # fastapi / uvicorn / pydantic — nothing else
├── .env.example              # variable names, no values
├── PAYLOAD_MANIFEST.txt      # source commit + assembled-at stamp
├── app/                      # the Space-only layer (settings, governance, routes, main)
├── src/                      # cognitive core, copied verbatim from the repository
└── services/api/app/         # session_service.py + schemas.py only
```

Excluded by construction: `apps/`, `backend/`, `archive/`, `supabase/`, `docs/`,
`tests/`, `scripts/`, `config/`, `data/` and the repository's root `requirements.txt`.

Why copy at assembly time instead of committing a second `src/` under `spaces/`: the
constraint is "avoid duplicating source code unnecessarily". The Space therefore holds no
fork that can drift — a stale deployment is impossible to mistake for the repository,
because `PAYLOAD_MANIFEST.txt` records the commit it was built from.

## 2. Migration plan — reuse, adapt, exclude

| Disposition | Component | Detail |
|---|---|---|
| **Reuse (verbatim)** | `src/` (avatars, aides, advocates, fusion, simulation, core, ai) | Copied into the payload; no edits, no wrappers, no framework |
| **Reuse (verbatim)** | `src/fusion/agent_loop_http.create_app` | Mounted as-is at `/`; the frozen contract keeps its tested behaviour |
| **Reuse (verbatim)** | `services/api/app/session_service.py` + `schemas.py` | The documented session boundary, imported rather than reimplemented |
| **Adapt (thin layer only)** | Runtime configuration, governance context, `/v1` routes, health/readiness, image | All new code lives in `spaces/ai-fusion/app/`; ~5 files, no changes to `src/` |
| **Excluded** | `apps/web`, `apps/mobile`, `packages/simulation-sdk` | Client surfaces; they call the Space over HTTP |
| **Excluded** | `backend/app` (legacy, placeholder fusion) | Conflicts C1/C3; superseded by `/v1/fusion/*` |
| **Excluded** | `apps/api` (thin surface, broken imports) | Conflicts C1/C2 |
| **Excluded** | `archive/**` | Retired runtimes; `CLAUDE.md` forbids importing them |
| **Excluded** | `tests/`, `.github/`, `scripts/`, docs | Verification and tooling, not runtime |
| **Excluded for now** | `ModelFusionEngine` HTTP surface, training trigger | Conflict C6: no queue, no durable run state |
| **Excluded for now** | `supabase` client | Durable-state decision pending; enabled by configuration, not by image |

## 3. Deployment runbook

### 3.1 Prerequisites

- Write access to `divergent-tech/Ai-fusion` (this agent's session has read-only Hub
  access — see §6).
- `hf` CLI authenticated, or `HF_TOKEN` in the environment for `huggingface_hub`.
- The Space already carries the bucket volume `divergent-tech/Fusion` at `/data`
  (verified in the Space's runtime metadata, `configuredByUserId` = the account owner).

### 3.2 Assemble and publish

```bash
# 1. from the repository root, on the commit to deploy
git switch main && git pull
spaces/ai-fusion/sync-to-hub.sh --out build/space-ai-fusion

# 2. inspect what will ship (manifest records the exact commit)
cat build/space-ai-fusion/PAYLOAD_MANIFEST.txt

# 3. verify locally before publishing (see §4 for the full gate)
cd build/space-ai-fusion
PYTHONPATH=$PWD uvicorn app.main:create_runtime_app --factory --port 7860 --reload

# 4. publish
spaces/ai-fusion/sync-to-hub.sh --push divergent-tech/Ai-fusion
```

### 3.3 Space settings (one-time, in the Hub UI)

| Setting | Value | Why |
|---|---|---|
| SDK | `docker` (from `README.md` front-matter) | The runtime is a service, not a Gradio UI |
| App port | `7860` | Matches `Dockerfile` `EXPOSE`/`CMD` |
| Hardware | `cpu-basic` | `baseline` decision source needs no accelerator |
| Variables | `NLT_GOVERNANCE_MODE=enforce`, `FUSION_AGENT_LOOP_MODEL=baseline`, `NLT_ENVIRONMENT=production`, `ALLOWED_ORIGINS=<api platform origin>` | Non-secret configuration |
| Secrets | `SUPABASE_URL`, `SUPABASE_KEY` (only when durable state is enabled) | Never in git, never echoed |
| Volume | `divergent-tech/Fusion` → `/data` | Checkpoints and evaluation artifacts |

Do **not** set `NLT_GOVERNANCE_MODE=permissive` in the Space; it exists for local runs.

## 4. Health checks and integration tests

### 4.1 Liveness and readiness

| Probe | Route | Passes when |
|---|---|---|
| Container | `HEALTHCHECK` in `Dockerfile` (30 s interval, 40 s start period) | `/health` returns 200 |
| Liveness | `/health` | Process answers; no dependency is touched |
| Readiness | `/readyz` | Decision source resolved (`FUSION_AGENT_LOOP_MODEL` valid), ≥1 agent registered, `/data` writable — otherwise 503 with `reasons[]` |
| Smoke | `/v1/sessions/demo-run` with a grant | Returns metrics (`total_attempts ≥ 1`, `success_rate` in 0–1) |

`/readyz` deliberately fails when `/data` is unwritable, because that is the one condition
under which the Space would answer decisions but silently lose checkpoints.

### 4.2 Integration test suite (runs without a network or a model file)

`spaces/ai-fusion/tests/test_runtime.py` — 20 tests against the composed app:

| Group | Covers |
|---|---|
| `TestHealth` | liveness; readiness contents; readiness 503 when artifacts are unwritable |
| `TestGovernance` | 403 without context; 403 with identity but no capability; 403 on unsupported governance version; context echoed on success; permissive mode never claims authorization |
| `TestFusionRoutes` | registry listing; 404 on unknown agent; readiness dimensions; fusion refused for an untrained pair; state feed published with `tick`; runtime info boundaries |
| `TestSessionOrchestration` | session metrics; separate capability required; scenario validation before any work runs |
| `TestAgentLoopSeam` | correlated intent through the mounted contract; 404 for unregistered agent; 422 for a malformed envelope |

Run them from the repository root:

```bash
python -m pytest spaces/ai-fusion/tests/ -q
```

The repository's own contract tests must stay green as well, since the Space mounts that
code verbatim:

```bash
python -m pytest tests/test_fusion/ -q
```

### 4.3 Post-deploy verification (against the live Space)

```bash
BASE=https://divergent-tech-ai-fusion.hf.space

curl -sf $BASE/health
curl -sf $BASE/readyz

H=(-H "X-NLT-Agent-Id: deploy-check" -H "X-NLT-Session-Id: verify-1"
   -H "X-NLT-Provenance: deploy-check/1.0" -H "X-NLT-Governance-Version: ORG-DEV-OTOI-1.0.3"
   -H "X-NLT-Capabilities: fusion.read,fusion.session.run")

curl -sf "${H[@]}" $BASE/v1/fusion/agents            # expect stay_alert_001
curl -sf "${H[@]}" $BASE/v1/sessions/demo-run        # expect metrics
curl -s -o /dev/null -w '%{http_code}\n' $BASE/v1/fusion/agents   # expect 403 (no grant)
curl -sf -X POST $BASE/agent-loop/perception \
  -H 'Content-Type: application/json' \
  -d @- <<'JSON'
{"protocolVersion":"nlt.agent-loop.v1","messageType":"perception","messageId":"verify-1",
 "agentId":"stay_alert_001","tick":1,"scene":{"id":"workplace_1","kind":"interior"},
 "self":{"position":{"x":0,"y":0,"z":0},"velocity":{"x":0,"y":0,"z":0}},
 "visibleEntities":[{"id":"desk_1","kind":"place","position":{"x":2,"y":0,"z":2},
   "affordances":["approach","use","sit"],"occupied":false}]}
JSON
# expect {"messageType":"intent","agentId":"stay_alert_001",...,"verb":"sit","targetId":"desk_1"}
```

`/agent-loop/status` is expected to return **403** from outside the host: the contract
serves it on loopback only. Treat that as a pass, not a fault.

## 5. Rollback and operational notes

- **Rollback:** the Space is a git repo — `hf` keeps every commit. Re-publish the previous
  payload (`sync-to-hub.sh --out …` from the older commit) or revert the Space commit in
  the Hub UI; the image rebuilds from it. `/data` is untouched by a code rollback.
- **Startup:** configuration is validated before serving; a bad `NLT_GOVERNANCE_MODE`, an
  unknown `FUSION_AGENT_LOOP_MODEL`, or a selected model without a path fails the boot
  instead of degrading quietly.
- **Shutdown:** uvicorn drains in-flight requests; the lifespan logs the stop. A decision
  that outlives `FUSION_AGENT_LOOP_TIMEOUT` quarantines the model (contract behaviour) and
  the platform's restart is the supervisor — Fusion does not restart itself.
- **Observability:** structured-ish logs on stdout (`INFO: ai_fusion.space: …`) including
  the non-secret configuration summary, registered agents, and the permissive-mode
  warning. No request bodies, perceptions or credentials are logged.
- **Cost/limits:** `zero-a10g` (the Space's previous hardware request) is unnecessary for
  `baseline`; use `cpu-basic`. Model-backed variants need the matching hardware and the
  optional dependency layer, and should then carry a bounded decision timeout.

## 6. Definition-of-done status

| Requirement | Status | Evidence |
|---|---|---|
| Runs the complete current-scope AI-Fusion runtime | **Met** | Decision seam + fusion + session orchestration served from one image; verified by execution (below) |
| Stable service interface | **Met** | `/v1/fusion/*`, `/v1/sessions/*`, `/v1/runtime/info`, `/agent-loop/*`, versioned paths, schemas returned from `src/fusion` dataclasses |
| Communicates with the NeuroLift API platform | **Met (server side)** | Governance headers accepted, context echoed, CORS configurable via `ALLOWED_ORIGINS`; client registration is the platform's side |
| Communicates with the Godot World Engine | **Met (server side)** | `POST /agent-loop/perception` returns a correlated `intent`; verified live |
| Preserves ASFDK governance | **Met (context only)** | Capability gate enforced, context carried, permissive mode labelled — see C7 for the contract-seam exception |
| Deployed into the Space | **Blocked outside this session** | `divergent-tech/Ai-fusion` is still `NO_APP_FILE`; this session's Hub access is read-only (no HF tool registered, no `HF_TOKEN`), so the payload is assembled and verified but not uploaded |

### Verification performed (local, against the assembled payload)

```
spaces/ai-fusion/sync-to-hub.sh --out build/space-ai-fusion
  -> payload: README.md Dockerfile requirements.txt .env.example app/ src/ services/api/app/ PAYLOAD_MANIFEST.txt

cd build/space-ai-fusion && PYTHONPATH=$PWD uvicorn app.main:create_runtime_app --factory --port 7861

GET  /health                                  -> 200 {"status":"ok","service":"ai-fusion-runtime"}
GET  /readyz                                  -> 200 model_kind=baseline, agents=[stay_alert_001], protocol=nlt.agent-loop.v1
GET  /v1/fusion/agents  (no grant)            -> 403 governance_context_missing
GET  /v1/fusion/agents  (grant)               -> 200 count=1, context echoed
POST /v1/fusion/readiness                     -> 200 overall_score=0.167, ready=false
POST /v1/sessions/demo-run                    -> 200 attempts=8 successes=1 success_rate=0.125
POST /agent-loop/perception (tick 42)         -> 200 intent verb=sit targetId=desk_1 agentId=stay_alert_001
POST /agent-loop/perception (ghost agent)     -> 404
```

Test suites: `spaces/ai-fusion/tests/` 20 passed; `tests/test_fusion/test_agent_loop_http.py` 10 passed
(the mounted contract behaves exactly as the repository expects).

## 7. Known limitations of the current runtime

1. **One registered pair.** `stay_alert_001` is the only fully implemented Avatar/Aide pair
   (`build_default_registry`). TaskKickstart exists as a trait module but is not registered;
   adding it means registering it in `agent_loop_registry` — a repository change, not a
   Space change.
2. **Readiness of a fresh pair is 0.167 and never ready.** Fusion only becomes available
   after real session history; that is the design, not a defect. `/v1/fusion/attempt`
   therefore returns `success: false` until sessions have been run.
3. **`ModelFusionEngine` has no route.** Trajectory distillation runs in-process only;
   exposing it needs a durable student trainer and a queue (C6).
4. **No authentication of its own.** The Space trusts the platform in front of it. If the
   Space is exposed directly, put an identity-aware proxy in front and keep
   `NLT_GOVERNANCE_MODE=enforce`.
5. **`/agent-loop/status` is loopback-only**, so on Hugging Face it is unreachable from
   outside. Operator visibility into quarantine currently comes from logs; adding a
   Space-level mirror would duplicate contract state and is left as a decision.
