# AI-Fusion Quick Start

**Repository:** `NeuroLift-Technologies/nlt-ai-fusion`  
**Last updated:** 2026-10-30

This repository owns cognitive intelligence and learning workflows. The authoritative physical simulation is the sibling [`nlt-world-engine`](https://github.com/NeuroLift-Technologies/nlt-world-engine) repository running Godot 4.7.2.

## 1. Python environment

```bash
python3 -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt
```

Run the current cognitive/session and Fusion tests:

```bash
pytest tests/test_simulation/test_session_orchestrator.py
pytest tests/test_fusion
```

Run the complete Python suite when changing shared Python modules:

```bash
pytest
```

## 2. Run the local Fusion agent-loop endpoint

The opt-in local test serves `nlt.agent-loop.v1` over loopback HTTP. It is a development/test path, not a public production endpoint.

For a GGUF model in Windows PowerShell:

```powershell
$fusionVenv = (Resolve-Path '.venv').Path
$fusionPython = Join-Path $fusionVenv 'Scripts/python.exe'
$env:FUSION_GGUF_MODEL = Join-Path $HOME 'Downloads/Qwen3-0.6B-Q8_0.gguf'
$env:FUSION_AGENT_LOOP_PORT = '8001'

uv pip install --python $fusionPython -r requirements-gguf.txt
uv pip install --python $fusionPython 'fastapi>=0.115.0' 'uvicorn>=0.30.0'
& $fusionPython -m src.fusion.agent_loop_http
```

Without `FUSION_GGUF_MODEL`, the endpoint uses the deterministic fallback. Other decision-source options and timeout configuration are documented in [`docs/agent-loop-model-adapter.md`](docs/agent-loop-model-adapter.md).

## 3. Connect the sibling Godot project (opt-in)

In a second PowerShell terminal, from the Fusion repository:

```powershell
$worldEngineProject = '..\nlt-world-engine\world-engine-godot'
$env:NLT_AGENT_LOOP_ENABLED = '1'
$env:NLT_AGENT_LOOP_ENDPOINT = 'http://127.0.0.1:8001/agent-loop/perception'
& $env:GDA_GODOT --path $worldEngineProject
```

`GDA_GODOT` must point to the Godot 4.7.2 .NET executable. Use the opt-in test scene and inspect both processes:

- Fusion should log the perception request and semantic intent response.
- Godot should log intent ingress, governance/physical validation, and execution.
- Confirm visible movement and arrival in the Godot world, then confirm the next perception reflects the new physical state.

A successful HTTP response or headless preflight is not proof of physical completion. The current local loop is also separate from `SessionOrchestrator`; it does not yet establish the full embodied Avatar–Aide learning and Advocate-fusion pipeline.

## 4. Application surfaces

### FastAPI API

```bash
cd apps/api
pip install -r requirements.txt
PYTHONPATH=../../src uvicorn main:app --reload --port 8000
```

### Web application

```bash
cd apps/web
corepack enable
pnpm install --frozen-lockfile
cp .env.local.example .env.local
pnpm dev
```

### Mobile application

```bash
cd apps/mobile
npm install
cp .env.example .env
npx expo start
```

## 5. Architecture and governance

- [Current architecture](docs/architecture.md)
- [Implementation status](docs/implementation_summary.md)
- [Agent-loop model adapter](docs/agent-loop-model-adapter.md)
- [AGENT-LOOP-003 brief](docs/specs/AGENT-LOOP-003-fusion-state-and-goals-brief.md)
- [OTOI development contract](NLT-DEV-OTOI.md)

The old Python ECS world, Cloudflare simulation worker, browser simulation prototype, and their obsolete scripts/tests are preserved under [`archive/legacy-world-engine/`](archive/legacy-world-engine/README.md). Do not use those archived paths as active runtime entrypoints.
