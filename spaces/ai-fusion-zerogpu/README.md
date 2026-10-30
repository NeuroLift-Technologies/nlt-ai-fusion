---
title: AI-Fusion ZeroGPU Runtime
emoji: [33m[1m[4mZ[0m
colorFrom: blue
colorTo: cyan
sdk: gradio
app_port: 7860
pinned: false
license: apache-2.0
short_description: ZeroGPU Gradio demo for NeuroLift AI Fusion - baseline decision source
---

# NeuroLift AI-Fusion ZeroGPU Demo

**Free-tier compatible Gradio Space** demonstrating the NeuroLift AI-Fusion cognitive layer with **ZeroGPU** (CPU-only inference). This Space uses the deterministic **baseline** decision source which requires no GPU and consumes minimal CPU.

## What This Space Does

This is a **demo interface** for the Fusion runtime's agent-loop decision seam. It:

- Runs the **baseline** decision source (deterministic goal-based ranking)
- Exposes a simple Gradio UI to simulate Godot perception inputs
- Returns semantic intents (`approach`, `look_at`, `use`, `sit`, `rest`, `wait`)
- Demonstrates the `nlt.agent-loop.v1` contract behavior
- Uses **ZeroGPU** - no GPU required, runs on free-tier CPU

## What It Does NOT Do

- ❌ Does NOT run LLMs or neural models (those require GPU)
- ❌ Does NOT connect to Godot (this is a demo, not production)
- ❌ Does NOT persist training data
- ❌ Does NOT perform actual Fusion of Avatar+Aide pairs

For actual model-based decision making, use the **Lite CPU Space** with GGUF models.

## Quick Start

The Space auto-launches when you open it. Use the Gradio interface to:

1. **Select an agent** from registered Avatar/Aide pairs
2. **Send a perception** (simulated Godot state)
3. **View the intent** returned by the baseline decision source
4. **Inspect the ranking** of available choices

## Configuration

### Environment Variables (Space Secrets/Variables)

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `FUSION_AGENT_LOOP_MODEL` | `baseline` | No | Decision source: `baseline`, `gguf`, or `transformers` |
| `FUSION_AGENT_LOOP_TIMEOUT` | `15` | No | Max seconds per decision (must be < 30s for Godot) |
| `FUSION_AGENT_LOOP_HISTORY` | `10` | No | How many past decisions each agent remembers |

### For ZeroGPU (this Space)

Keep `FUSION_AGENT_LOOP_MODEL=baseline` - this is the only mode that works without a GPU.

## Architecture

```
Gradio UI → FastAPI endpoints → FusionAgentLoop → BaselineDecisionSource
                                    ↓
                             AgentRegistry (pre-registered agents)
```

## Registered Agents

This demo includes these pre-registered agent pairs (from `agent_loop_registry.py`):

- `stay_alert` - Attention deficit Avatar
- `timely` - Time blindness Avatar  
- `memory_mate` - Working memory Avatar
- `planner_pro` - Planning deficit Avatar

## API Endpoints

The Gradio UI wraps these underlying endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Liveness check |
| `/readyz` | GET | Readiness check |
| `/v1/runtime/info` | GET | Runtime metadata |
| `/v1/fusion/agents` | GET | List registered agents |
| `/agent-loop/perception` | POST | Submit perception, get intent |
| `/agent-loop/status` | GET | Quarantine status |

## Limitations

### Free Tier Constraints

- **No GPU**: Cannot run `gguf` or `transformers` models
- **CPU-only**: Baseline decision source is lightweight but deterministic
- **No persistence**: `/data` is ephemeral on free tier
- **Rate limits**: Hugging Face free tier has request limits

### Baseline Decision Source

The baseline uses **goal-based ranking** (AGENT-LOOP-003 F4):
- Ranks choices by: goal-relevant targets → unvisited places → everything else
- Always takes the **first-ranked** option
- No model inference, no learning
- Deterministic and repeatable

## Deployment

This Space is assembled from the main repository using `sync-to-hub-zerogpu.sh`:

```bash
# From repository root
spaces/ai-fusion-zerogpu/sync-to-hub.sh --push <your-hf-username>/ai-fusion-zerogpu
```

## Next Steps

For more advanced capabilities:

1. **Lite CPU Space**: Use GGUF models with CPU inference
2. **Full Docker Space**: Run the complete API with all capabilities
3. **Local development**: Clone the repo and run locally

## Links

- [Main Repository](https://github.com/NeuroLift-Technologies/nlt-ai-fusion)
- [Documentation](https://github.com/NeuroLift-Technologies/nlt-ai-fusion/tree/main/docs)
- [Lite CPU Space](https://huggingface.co/spaces/<your-username>/ai-fusion-lite) (GGUF models)
- [Full API Space](https://huggingface.co/spaces/<your-username>/ai-fusion) (Docker)

---

**Status**: Demo/Experimental | **Tier**: Free (ZeroGPU) | **Model**: Baseline (CPU)
