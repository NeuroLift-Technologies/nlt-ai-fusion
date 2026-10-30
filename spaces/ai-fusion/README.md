---
title: AI-Fusion Runtime
emoji: 🧠
colorFrom: green
colorTo: red
sdk: docker
app_port: 7860
pinned: false
license: apache-2.0
short_description: Semantic layer of the NeuroLift AI fusion framework
---

# NeuroLift AI-Fusion Runtime

Hosted execution environment for the cognitive layer of NeuroLift AI-Fusion. This
Space runs the Fusion runtime from
[`NeuroLift-Technologies/nlt-ai-fusion`](https://github.com/NeuroLift-Technologies/nlt-ai-fusion);
GitHub stays the source of truth and this Space is assembled from it, never edited
by hand.

**It owns cognitive processing only.** Physics, world state and rendering belong to
`nlt-world-engine` (Godot). Fusion returns semantic intent (`approach`, `look_at`,
`use`, `sit`, `rest`, `wait`) and never coordinates, velocity or object state.
ASFDK governance and physical validation run at the Godot intent ingress — this
service does not enforce them and never claims execution.

## Interfaces

| Route | Method | Purpose |
|---|---|---|
| `/health` | GET | Liveness only. No dependency is touched. |
| `/readyz` | GET | Readiness: decision source resolved, agents registered, `/data` writable. 503 with reasons otherwise. |
| `/v1/runtime/info` | GET | Runtime identity, versions, protocol version, boundaries. Capability `runtime.info`. |
| `/v1/fusion/agents` | GET | Registered Avatar/Aide pairs. Capability `fusion.read`. |
| `/v1/fusion/readiness` | POST | Readiness dimensions for a pair. Capability `fusion.read`. |
| `/v1/fusion/attempt` | POST | Avatar + Aide → Advocate fusion attempt. Capability `fusion.fuse`. |
| `/v1/fusion/state-feed/{agent_id}` | GET | One-way renderer state feed. Capability `fusion.read`. |
| `/agent-loop/perception` | POST | `nlt.agent-loop.v1` decision seam Godot calls. |
| `/agent-loop/status` | GET | Quarantine state, loopback callers only (contract behaviour). |

`/agent-loop/*` is mounted unchanged from `src.fusion.agent_loop_http.create_app`,
so the contract behaviour tested in the repository (registry, one-in-flight,
timeout quarantine, fail-closed errors) is what this Space serves.

## Governance

Governance is enforced by default (`NLT_GOVERNANCE_MODE=enforce`). A request must
carry the caller's context; arriving successfully is not authorization:

```http
X-NLT-Agent-Id: api-platform
X-NLT-Session-Id: <session>
X-NLT-Provenance: nlt-api/1.0.0
X-NLT-Governance-Version: ORG-DEV-OTOI-1.0.3
X-NLT-Capabilities: fusion.read,fusion.fuse
```

Missing or insufficient context returns `403` with a structured reason. Local
development may set `NLT_GOVERNANCE_MODE=permissive`; every response then states
`governance_enforced: false` so a permissive answer can never be read as an
authorized one.

## Configuration

Only non-secret configuration belongs in the Space's *Variables*. Tokens belong in
*Secrets*; they are never committed and never echoed by the runtime.

| Name | Default | Meaning |
|---|---|---|
| `NLT_GOVERNANCE_MODE` | `enforce` | `enforce` or `permissive` |
| `NLT_GOVERNANCE_VERSION` | `ORG-DEV-OTOI-1.0.3` | Version accepted from callers |
| `FUSION_AGENT_LOOP_MODEL` | `baseline` | `baseline`, `gguf` or `transformers` |
| `FUSION_GGUF_MODEL` | unset | Path to a `.gguf`, e.g. `/data/models/model.gguf` |
| `FUSION_TRANSFORMERS_MODEL` | unset | Directory of a local HF model under `/data` |
| `FUSION_AGENT_LOOP_TIMEOUT` | `15` | Per-decision budget, must stay under Godot's 30 s |
| `FUSION_AGENT_LOOP_HISTORY` | runtime default | Decisions each agent remembers |
| `ALLOWED_ORIGINS` | unset | Comma-separated CORS origins |
| `NEUROLIFT_MODELS_DIR` | `/data/models` | Checkpoint directory (persistent bucket) |
| `SUPABASE_URL` / `SUPABASE_KEY` | unset | Set as **Secrets** when durable state is enabled |

`baseline` is the default on purpose: it is the deterministic, model-free decision
source, so the Space boots with no checkpoint present and still answers. Selecting
`gguf` or `transformers` without a model present fails at startup rather than on
the first perception.

## Storage

`/data` is the Space's persistent bucket. It holds model checkpoints and evaluation
artifacts only. The Space filesystem is **not** a system of record: session state,
training data and long-lived provenance live in Supabase / object storage and are
reached through configuration, never through files baked into the image.

## Status

Deployed from GitHub by `spaces/ai-fusion/sync-to-hub.sh`; see
`docs/space-runtime/` in the repository for the audit, boundaries, migration plan
and deployment runbook.
