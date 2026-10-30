---
title: AI-Fusion Lite CPU Runtime
emoji: [32m[1m[4mL[0m
colorFrom: green
colorTo: yellow
sdk: gradio
app_port: 7860
pinned: false
license: apache-2.0
short_description: Lite CPU Gradio demo with GGUF model support
---

# NeuroLift AI-Fusion Lite CPU Demo

**Free-tier compatible Gradio Space** demonstrating the NeuroLift AI-Fusion cognitive layer with **CPU-based GGUF model inference**. This Space can run small language models entirely on CPU using the Lite tier.

## What This Space Does

This is a **demo interface** for the Fusion runtime's agent-loop with **GGUF model support**:

- Runs **GGUF models on CPU** (via llama-cpp-python)
- Exposes a Gradio UI to simulate Godot perception inputs
- Returns semantic intents with **model-based decision making**
- Demonstrates the `nlt.agent-loop.v1` contract with actual LLM inference
- Uses **Lite CPU** tier - runs on free-tier CPU with model size limits

## What It Does NOT Do

- ❌ Does NOT use GPU (CPU-only inference)
- ❌ Does NOT connect to Godot (this is a demo)
- ❌ Does NOT persist training data
- ❌ Model size limited by free-tier CPU constraints

## Quick Start

The Space auto-launches when you open it. Use the Gradio interface to:

1. **Select a GGUF model** (must be in `/data/models/`)
2. **Select an agent** from registered Avatar/Aide pairs
3. **Send a perception** (simulated Godot state)
4. **View the intent** returned by the GGUF model
5. **Monitor performance** - CPU inference may be slow for larger models

## Configuration

### Environment Variables (Space Secrets/Variables)

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `FUSION_AGENT_LOOP_MODEL` | `gguf` | No | Decision source: `baseline`, `gguf`, or `transformers` |
| `FUSION_GGUF_MODEL` | unset | **Yes** | Path to GGUF model file (e.g., `/data/models/qwen2.5-0.6b-instruct.q4_k_m.gguf`) |
| `FUSION_AGENT_LOOP_TIMEOUT` | `15` | No | Max seconds per decision (must be < 30s for Godot) |
| `FUSION_AGENT_LOOP_HISTORY` | `10` | No | How many past decisions each agent remembers |
| `NEUROLIFT_MODELS_DIR` | `/data/models` | No | Directory for model checkpoints |

### Required Setup

For this Space to work, you **must**:

1. Upload a GGUF model to `/data/models/` in your Space
2. Set `FUSION_GGUF_MODEL` to the path (e.g., `/data/models/model.gguf`)
3. Set `FUSION_AGENT_LOOP_MODEL=gguf`

### Recommended Models for Free Tier

These models should work on free-tier CPU (tested with 8GB RAM):

- `Qwen2.5-0.6B-Instruct-Q4_K_M.gguf` (~380MB) - Fast, good quality
- `TinyLlama-1.1B-Instruct-Q4_K_M.gguf` (~590MB) - Slightly larger
- `Phi-2-Q4_K_M.gguf` (~1.3GB) - Good reasoning, slower

**Avoid models > 2GB** - they may exceed free-tier memory limits.

## Architecture

```
Gradio UI → FastAPI endpoints → FusionAgentLoop → LlamaCppAgentLoopDecision
                                    ↓
                             AgentRegistry (pre-registered agents)
                                    ↓
                             GGUF Model (llama-cpp-python on CPU)
```

## Registered Agents

This demo includes these pre-registered agent pairs:

- `stay_alert` - Attention deficit Avatar
- `timely` - Time blindness Avatar
- `memory_mate` - Working memory Avatar
- `planner_pro` - Planning deficit Avatar

## API Endpoints

The Gradio UI wraps these underlying endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Liveness check |
| `/readyz` | GET | Readiness check (verifies model loaded) |
| `/v1/runtime/info` | GET | Runtime metadata |
| `/v1/fusion/agents` | GET | List registered agents |
| `/agent-loop/perception` | POST | Submit perception, get intent |
| `/agent-loop/status` | GET | Quarantine status |

## Model Loading

The Space loads the GGUF model at startup. This can take **30-60 seconds** depending on model size. The `/readyz` endpoint will return 503 until the model is loaded.

### Loading Process

1. Space starts
2. Checks for GGUF model at `FUSION_GGUF_MODEL` path
3. Loads model with llama-cpp-python
4. Verifies model works with a test prompt
5. Marks as ready

### Troubleshooting

If model loading fails:
- Check the model path is correct
- Verify the file exists in `/data/models/`
- Ensure the model is a valid GGUF file
- Check Space logs for error messages
- Try a smaller model

## Performance Expectations

### CPU Inference Speed

| Model | Size | Tokens/sec (CPU) | Decision Time |
|-------|------|------------------|---------------|
| Qwen2.5-0.6B | 380MB | ~20-30 | 1-2 seconds |
| TinyLlama-1.1B | 590MB | ~10-15 | 2-3 seconds |
| Phi-2 | 1.3GB | ~5-8 | 3-5 seconds |

**Note**: These are estimates. Actual performance depends on:
- Hugging Face CPU allocation
- Current load on the server
- Model complexity
- Prompt length

### Timeout Considerations

- Godot expects decisions within **30 seconds**
- `FUSION_AGENT_LOOP_TIMEOUT` defaults to **15 seconds**
- If a decision takes longer, the model is quarantined
- Larger models may hit the timeout on free-tier CPU

## Deployment

This Space is assembled from the main repository using `sync-to-hub-lite.sh`:

```bash
# From repository root
spaces/ai-fusion-lite/sync-to-hub.sh --push <your-hf-username>/ai-fusion-lite
```

### First-Time Setup

1. Create the Space on Hugging Face
2. Upload your GGUF model to `/data/models/` in the Space
3. Set the required environment variables
4. Deploy

### Updating Models

To change models:
1. Upload new GGUF file to `/data/models/`
2. Update `FUSION_GGUF_MODEL` variable
3. Redeploy (model loads on startup)

## Comparison: ZeroGPU vs Lite CPU vs Full

| Feature | ZeroGPU | Lite CPU | Full Docker |
|---------|---------|----------|-------------|
| GPU | ❌ No | ❌ No | ✅ Yes (paid) |
| Model | Baseline | GGUF | Any |
| Speed | Instant | 1-5s | Fast |
| Memory | Low | Medium | High |
| Cost | Free | Free | Paid |
| Complexity | Simple | Medium | Full |

## Next Steps

1. **Try different models**: Experiment with various GGUF models
2. **Monitor performance**: Check decision times in the UI
3. **Upgrade to paid**: For larger models and GPU support
4. **Local testing**: Run locally before deploying to Space

## Links

- [Main Repository](https://github.com/NeuroLift-Technologies/nlt-ai-fusion)
- [Documentation](https://github.com/NeuroLift-Technologies/nlt-ai-fusion/tree/main/docs)
- [ZeroGPU Space](https://huggingface.co/spaces/<your-username>/ai-fusion-zerogpu) (Baseline only)
- [Full API Space](https://huggingface.co/spaces/<your-username>/ai-fusion) (Docker)

---

**Status**: Demo/Experimental | **Tier**: Free (Lite CPU) | **Model**: GGUF on CPU
