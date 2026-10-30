# Gradio Spaces Deployment Guide

This document describes how to deploy NeuroLift AI-Fusion to Hugging Face Spaces using Gradio, with configurations optimized for the free tier.

## Overview

We provide **two Gradio Space configurations** that work with Hugging Face's free tier:

| Space | SDK | GPU | Decision Source | Use Case |
|-------|-----|-----|----------------|----------|
| **ai-fusion-zerogpu** | Gradio | ZeroGPU | Baseline | Demo, no model inference |
| **ai-fusion-lite** | Gradio | Lite CPU | GGUF | Small model inference on CPU |

## Quick Start

### ZeroGPU Space (Easiest)

The ZeroGPU space requires **no GPU** and uses the deterministic baseline decision source.

```bash
# From repository root
cd spaces/ai-fusion-zerogpu
./sync-to-hub.sh --push <your-hf-username>/ai-fusion-zerogpu
```

Then on Hugging Face:
1. Create a new Space
2. Select **Gradio** SDK
3. Select **ZeroGPU** hardware
4. Upload the assembled payload from `build/space-ai-fusion-zerogpu/`
5. Deploy!

### Lite CPU Space (GGUF Models)

The Lite CPU space can run **GGUF models on CPU** for actual LLM inference.

```bash
# From repository root
cd spaces/ai-fusion-lite
./sync-to-hub.sh --push <your-hf-username>/ai-fusion-lite
```

Then on Hugging Face:
1. Create a new Space
2. Select **Gradio** SDK
3. Select **Lite CPU** hardware
4. Upload the assembled payload from `build/space-ai-fusion-lite/`
5. **Upload a GGUF model** to `/data/models/` in your Space
6. Set environment variables:
   - `FUSION_AGENT_LOOP_MODEL=gguf`
   - `FUSION_GGUF_MODEL=/data/models/your-model.gguf`
7. Deploy!

## Space Comparison

### ZeroGPU Space (`ai-fusion-zerogpu`)

**Pros:**
- ✅ Works on **ZeroGPU** (completely free)
- ✅ Instant startup (no model loading)
- ✅ Deterministic, repeatable results
- ✅ Minimal CPU usage
- ✅ Perfect for testing and demos

**Cons:**
- ❌ No LLM inference (baseline only)
- ❌ Limited to deterministic decision making
- ❌ Cannot learn or adapt

**Best for:**
- Demonstrations
- Testing the agent-loop contract
- Development and debugging
- Educational purposes

### Lite CPU Space (`ai-fusion-lite`)

**Pros:**
- ✅ **Actual LLM inference on CPU**
- ✅ Can run GGUF models up to ~2GB
- ✅ Model-based decision making
- ✅ Still free-tier compatible
- ✅ Good for small models

**Cons:**
- ❌ Slower inference (1-5 seconds per decision)
- ❌ Model loading takes 30-60 seconds
- ❌ Limited by free-tier CPU allocation
- ❌ Memory constraints (~8GB RAM)

**Best for:**
- Small model experimentation
- GGUF model testing
- CPU-based inference demos
- Lightweight production use

## Configuration

### Environment Variables

Both spaces support these common variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `FUSION_AGENT_LOOP_MODEL` | `baseline` (ZeroGPU), `gguf` (Lite) | Decision source type |
| `FUSION_AGENT_LOOP_TIMEOUT` | `15` (ZeroGPU), `20` (Lite) | Max seconds per decision |
| `FUSION_AGENT_LOOP_HISTORY` | `10` | Past decisions remembered per agent |
| `NLT_GOVERNANCE_MODE` | `permissive` | Governance enforcement mode |
| `NLT_GOVERNANCE_VERSION` | `ORG-DEV-OTOI-1.0.3` | Accepted governance version |
| `ALLOWED_ORIGINS` | empty | CORS origins (comma-separated) |

#### Lite CPU Specific

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FUSION_GGUF_MODEL` | **Yes** | unset | Path to GGUF model file |
| `NEUROLIFT_MODELS_DIR` | No | `/data/models` | Model directory |

### Recommended GGUF Models for Lite CPU

These models work well on free-tier Lite CPU (8GB RAM):

| Model | Size | Est. Speed | Quality | Notes |
|-------|------|------------|---------|-------|
| `Qwen2.5-0.6B-Instruct-Q4_K_M.gguf` | ~380MB | ~20-30 t/s | ⭐⭐⭐⭐ | Fast, good quality |
| `Qwen2.5-0.6B-Instruct-Q8_0.gguf` | ~760MB | ~15-20 t/s | ⭐⭐⭐⭐⭐ | Better quality, slower |
| `TinyLlama-1.1B-Instruct-Q4_K_M.gguf` | ~590MB | ~10-15 t/s | ⭐⭐⭐⭐ | Good balance |
| `Phi-2-Q4_K_M.gguf` | ~1.3GB | ~5-8 t/s | ⭐⭐⭐⭐⭐ | Excellent reasoning |
| `Mistral-7B-Instruct-v0.2-Q4_K_M.gguf` | ~4.1GB | ~2-4 t/s | ⭐⭐⭐⭐⭐ | High quality, slow |

**Recommendation:** Start with `Qwen2.5-0.6B-Instruct-Q4_K_M.gguf` for the best balance of speed and quality.

**Warning:** Models > 4GB may exceed free-tier memory limits and fail to load.

## Deployment Steps

### Step 1: Assemble the Payload

```bash
# For ZeroGPU Space
cd spaces/ai-fusion-zerogpu
./sync-to-hub.sh --out /tmp/zerogpu-payload

# For Lite CPU Space
cd spaces/ai-fusion-lite
./sync-to-hub.sh --out /tmp/lite-payload
```

This creates a clean payload in the specified directory with:
- `README.md` - Space metadata and documentation
- `requirements.txt` - Python dependencies
- `.env.example` - Example environment variables
- `app/` - Gradio application code
- `src/` - Fusion runtime core

### Step 2: Create the Space on Hugging Face

1. Go to [Hugging Face Spaces](https://huggingface.co/spaces)
2. Click **Create new Space**
3. Enter a name (e.g., `ai-fusion-zerogpu`)
4. Select **Gradio** as the SDK
5. Select the appropriate hardware:
   - **ZeroGPU** for the baseline-only space
   - **Lite CPU** for the GGUF space
6. Keep **Visibility** as Public or Private as needed
7. Click **Create Space**

### Step 3: Upload Files

Upload all files from your assembled payload directory to the Space:

```bash
# Using hf CLI
cd /tmp/zerogpu-payload
hf upload <your-username>/ai-fusion-zerogpu . --repo-type space
```

Or use the web interface to upload files manually.

### Step 4: Configure Environment Variables

On the Space's **Settings** tab:

1. Go to **Environment Variables**
2. Add variables from `.env.example` as needed
3. For Lite CPU Space, **must** set:
   - `FUSION_GGUF_MODEL=/data/models/your-model.gguf`

### Step 5: Upload Models (Lite CPU Only)

For the Lite CPU Space:

1. Go to the **Files** tab
2. Navigate to `/data/models/`
3. Upload your GGUF model file
4. Set `FUSION_GGUF_MODEL` to the full path (e.g., `/data/models/qwen2.5-0.6b-q4_k_m.gguf`)

### Step 6: Deploy

Click **Deploy** on the Space's **App** tab. The Space will build and start.

- **ZeroGPU**: Starts immediately
- **Lite CPU**: Takes 30-60 seconds for model loading

## Verification

### Check Space Status

```bash
# Health check
curl https://<your-username>-ai-fusion-zerogpu.hf.space/health

# Readiness check
curl https://<your-username>-ai-fusion-zerogpu.hf.space/readyz

# List agents
curl https://<your-username>-ai-fusion-zerogpu.hf.space/v1/fusion/agents
```

### Test the Agent Loop

```bash
curl -X POST \
  https://<your-username>-ai-fusion-zerogpu.hf.space/agent-loop/perception \
  -H "Content-Type: application/json" \
  -d '{
    "agentId": "stay_alert",
    "observedTick": 12345,
    "self": {
      "id": "stay_alert",
      "position": {"x": 0, "y": 0, "z": 0},
      "state": "idle"
    },
    "scene": {"timeOfDay": "morning"},
    "entities": [
      {
        "id": "desk_01",
        "type": "desk",
        "position": {"x": 2, "y": 0, "z": 1},
        "affordances": ["approach", "use"]
      }
    ],
    "visibleEntities": ["desk_01"],
    "capabilities": ["walk", "look", "use"]
  }'
```

Expected response:
```json
{
  "intent": {
    "action": "approach",
    "target": "desk_01",
    "reason": "goal-based ranking"
  }
}
```

## Troubleshooting

### ZeroGPU Space Issues

| Issue | Solution |
|-------|----------|
| Space won't start | Check `requirements.txt` has all dependencies |
| Agents not registered | Verify `src/fusion/agent_loop_registry.py` is included |
| Slow responses | This shouldn't happen with baseline - check CPU usage |

### Lite CPU Space Issues

| Issue | Solution |
|-------|----------|
| Model not loading | Verify `FUSION_GGUF_MODEL` path is correct |
| Model file not found | Upload model to `/data/models/` first |
| Out of memory | Use a smaller model (< 2GB) |
| Slow inference | Expected for CPU - try a smaller model |
| Timeout errors | Increase `FUSION_AGENT_LOOP_TIMEOUT` (max 25) |

### Common Issues

| Issue | Solution |
|-------|----------|
| 503 Service Unavailable | Space is still starting - wait and retry |
| 403 Forbidden | Check CORS settings and `ALLOWED_ORIGINS` |
| 404 Not Found | Verify the endpoint URL is correct |
| Module not found | Check `requirements.txt` includes all dependencies |

## Updating Spaces

To update a deployed Space:

```bash
# Make changes to the repository
# Then reassemble and upload

cd spaces/ai-fusion-zerogpu
./sync-to-hub.sh --push <your-username>/ai-fusion-zerogpu

# Or for manual upload
./sync-to-hub.sh --out /tmp/new-payload
cd /tmp/new-payload
hf upload <your-username>/ai-fusion-zerogpu . --repo-type space
```

The Space will automatically redeploy when files change.

## Monitoring

### Space Logs

View logs on the **Logs** tab of your Space:
- Startup errors
- Model loading progress
- Request/response logging
- Error messages

### Metrics

The Gradio UI includes basic metrics:
- Request count
- Average response time
- Model loading time (Lite CPU)

## Security Considerations

### Free Tier Limitations

- **No authentication**: Anyone can access your Space
- **Rate limits**: Hugging Face applies rate limits
- **No secrets protection**: Environment variables are visible in settings
- **Ephemeral storage**: `/data` is not persistent on free tier

### Production Recommendations

For production use:
1. **Upgrade to paid tier** for:
   - GPU support
   - Larger models
   - Persistent storage
   - Authentication
   - Higher rate limits

2. **Use Docker Space** for:
   - Full control over environment
   - Better security
   - More configuration options

3. **Add authentication**:
   - Use Hugging Face tokens
   - Implement API keys
   - Use OAuth

## Architecture Details

### ZeroGPU Space Architecture

```
┌─────────────────────────────────────────────────────┐
│                 Gradio UI (Web)                      │
├─────────────────────────────────────────────────────┤
│  app/main.py (Gradio interface)                       │
├─────────────────────────────────────────────────────┤
│  FastAPI Endpoints                                    │
│  - /health, /readyz, /v1/runtime/info                 │
│  - /v1/fusion/agents, /agent-loop/perception         │
├─────────────────────────────────────────────────────┤
│  FusionAgentLoop (baseline decision source)          │
│  - Deterministic goal-based ranking                   │
│  - No model inference                                 │
├─────────────────────────────────────────────────────┤
│  AgentRegistry (pre-registered agents)                │
└─────────────────────────────────────────────────────┘
```

### Lite CPU Space Architecture

```
┌─────────────────────────────────────────────────────┐
│                 Gradio UI (Web)                      │
├─────────────────────────────────────────────────────┤
│  app/main.py (Gradio interface)                       │
├─────────────────────────────────────────────────────┤
│  FastAPI Endpoints                                    │
│  - /health, /readyz, /v1/runtime/info                 │
│  - /v1/fusion/agents, /agent-loop/perception         │
├─────────────────────────────────────────────────────┤
│  FusionAgentLoop (GGUF decision source)              │
│  - LlamaCppAgentLoopDecision                          │
│  - CPU inference via llama-cpp-python                 │
├─────────────────────────────────────────────────────┤
│  GGUF Model (loaded from /data/models/)              │
│  - Small language model                               │
│  - 4-bit quantization (Q4_K_M)                        │
├─────────────────────────────────────────────────────┤
│  AgentRegistry (pre-registered agents)                │
└─────────────────────────────────────────────────────┘
```

## API Reference

Both spaces expose these endpoints through Gradio:

### Health and Status

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Liveness check |
| GET | `/readyz` | Readiness check (model loaded for Lite) |
| GET | `/v1/runtime/info` | Runtime metadata and version info |

### Fusion API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/v1/fusion/agents` | List all registered agents |
| POST | `/v1/fusion/readiness` | Check readiness for a specific pair |
| POST | `/v1/fusion/attempt` | Attempt fusion (not implemented in demo) |

### Agent Loop (nlt.agent-loop.v1)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/agent-loop/perception` | Submit perception, get intent |
| GET | `/agent-loop/status` | Quarantine and status info |

## Gradio UI Reference

### ZeroGPU Space UI

The ZeroGPU Space UI includes:

1. **Agent Selector**: Dropdown of registered agents
2. **Perception Input**: Text area for JSON perception input
3. **Load Example**: Button to load a sample perception
4. **Get Intent**: Button to process perception and get intent
5. **Result Display**: JSON output of the intent
6. **Documentation**: About section with usage info

### Lite CPU Space UI

The Lite CPU Space UI includes everything from ZeroGPU plus:

1. **Model Status**: Shows loaded model info (size, path)
2. **Model Selector**: Future - select from multiple uploaded models
3. **Performance Metrics**: Decision time, tokens/sec

## Examples

### Example 1: Simple Perception

```json
{
  "agentId": "stay_alert",
  "observedTick": 1,
  "self": {
    "id": "stay_alert",
    "position": {"x": 0, "y": 0, "z": 0},
    "state": "idle",
    "emotionalState": "calm",
    "cognitiveLoad": 0.0
  },
  "scene": {
    "timeOfDay": "morning",
    "lighting": "bright",
    "noiseLevel": "quiet"
  },
  "entities": [
    {
      "id": "desk_01",
      "type": "desk",
      "position": {"x": 2, "y": 0, "z": 1},
      "affordances": ["approach", "use", "look_at"]
    }
  ],
  "visibleEntities": ["desk_01"],
  "targetsInReach": ["desk_01"],
  "capabilities": ["walk", "look", "use", "sit", "rest", "communicate", "wait"]
}
```

**Expected Intent (baseline):**
```json
{
  "action": "approach",
  "target": "desk_01",
  "reason": "goal-based ranking: first option"
}
```

### Example 2: Multiple Entities

```json
{
  "agentId": "planner_pro",
  "observedTick": 2,
  "self": {
    "id": "planner_pro",
    "position": {"x": 0, "y": 0, "z": 0},
    "state": "idle"
  },
  "scene": {"timeOfDay": "morning"},
  "entities": [
    {
      "id": "task_board",
      "type": "task_board",
      "position": {"x": 3, "y": 0, "z": 0},
      "affordances": ["approach", "use"]
    },
    {
      "id": "coffee_machine",
      "type": "coffee_machine",
      "position": {"x": -2, "y": 0, "z": 0},
      "affordances": ["approach", "use"]
    },
    {
      "id": "chair",
      "type": "chair",
      "position": {"x": 1, "y": 0, "z": 0},
      "affordances": ["approach", "sit"]
    }
  ],
  "visibleEntities": ["task_board", "coffee_machine", "chair"],
  "targetsInReach": ["chair"],
  "capabilities": ["walk", "look", "use", "sit"]
}
```

## Migration from Docker Space

If you're migrating from the Docker Space to Gradio Spaces:

### Key Differences

| Aspect | Docker Space | Gradio Spaces |
|--------|--------------|---------------|
| SDK | Docker | Gradio |
| Startup | Docker container | Python process |
| Port | Configurable | Always 7860 |
| GPU | Available (paid) | ZeroGPU or Lite CPU |
| Dependencies | Full control | Limited by SDK |
| Complexity | Higher | Lower |

### Migration Steps

1. **Update imports**: Gradio spaces have different module availability
2. **Simplify configuration**: Use environment variables instead of config files
3. **Adjust dependencies**: Remove unnecessary packages from `requirements.txt`
4. **Update sync script**: Use the new Gradio-specific sync scripts

### Compatibility Notes

- The agent-loop contract remains **unchanged**
- All Fusion APIs are **compatible**
- Agent registration is **identical**
- Decision sources are **the same**

## Related Documentation

- [Main README](../../README.md) - Project overview
- [Architecture](../architecture.md) - System architecture
- [Agent Loop Contract](../contracts/agent-loop-v1.md) - nlt.agent-loop.v1 specification
- [Docker Space Deployment](docker-space.md) - Docker-based deployment
- [Local Development](../../QUICKSTART.md) - Local setup guide

## Support

For issues with Gradio Spaces:
- [Hugging Face Spaces Documentation](https://huggingface.co/docs/hub/spaces)
- [Gradio Documentation](https://www.gradio.app/docs)
- [Hugging Face Forums](https://discuss.huggingface.co/)

For issues with NeuroLift AI-Fusion:
- [GitHub Issues](https://github.com/NeuroLift-Technologies/nlt-ai-fusion/issues)
- [Discussions](https://github.com/NeuroLift-Technologies/nlt-ai-fusion/discussions)

## License

All code in this repository is licensed under [Apache-2.0](../../LICENSE).

---

**Last Updated:** 2026-10-30  
**Version:** 1.0.0
