# AI-Fusion Quick Start

**Updated:** 2026-10-30

## Repository boundaries

- `nlt-ai-fusion` provides Avatar/Aide cognition, learning workflows, model adapters, and application APIs.
- `nlt-world-engine` (Godot 4.7.2) owns the authoritative physical world.
- The World Engine Reviewer is the human-facing representation of Godot state. It is not a simulation runtime or a Fusion endpoint.
- Historical Python, Cloudflare, and browser world implementations are in `archive/legacy-world-engine/`; do not use them for new development.

Before coding, read `NLT-DEV-OTOI.md`, `AGENTS.md`, `CLAUDE.md`, and `docs/active-threads.md`.

## Python environment and tests

From the repository root:

```bash
python -m pip install -r requirements.txt
python -m pytest
```

The active cognitive session API is `src.simulation.session_orchestrator.SessionOrchestrator`. It coordinates Avatar/Aide task attempts and coaching. It does not instantiate or advance a physical world.

## API

```bash
cd apps/api
python -m pip install -r requirements.txt
PYTHONPATH=../../src python -m uvicorn main:app --reload --port 8000
```

## Web application

```bash
cd apps/web
corepack enable
pnpm install --frozen-lockfile
cp .env.local.example .env.local
pnpm dev
```

## Mobile application

```bash
cd apps/mobile
npm ci
cp .env.example .env
npx expo start
```

## Local Godot ↔ Fusion agent-loop test

The opt-in `nlt.agent-loop.v1` test path is local-only. It does not establish a public endpoint or remote transport.

### Terminal 1: start Fusion

On Windows PowerShell, with the Fusion and `nlt-world-engine` repositories checked out side by side:

```powershell
$fusionVenv = 'C:\path\to\your\GGUF-enabled\virtualenv'
$fusionPython = Join-Path $fusionVenv 'Scripts\python.exe'
$env:FUSION_GGUF_MODEL = Join-Path $HOME 'Downloads\Qwen3-0.6B-Q8_0.gguf'
$env:FUSION_AGENT_LOOP_PORT = '8001'

uv pip install --python $fusionPython -r requirements-gguf.txt
uv pip install --python $fusionPython 'fastapi>=0.115.0' 'uvicorn>=0.30.0'
& $fusionPython -m src.fusion.agent_loop_http
```

Leave the process running. Unset `FUSION_GGUF_MODEL` to use the deterministic fallback.

### Terminal 2: start the opt-in Godot scene

```powershell
$worldEngineProject = '..\nlt-world-engine\world-engine-godot'
$env:NLT_AGENT_LOOP_ENABLED = '1'
$env:NLT_AGENT_LOOP_ENDPOINT = 'http://127.0.0.1:8001/agent-loop/perception'
& $env:GDA_GODOT --path $worldEngineProject
```

`GDA_GODOT` must point to the Godot 4.7.2 .NET executable. Inspect Fusion logs for perception requests and Godot logs for intent acceptance/rejection and physical movement. A successful HTTP response alone is not proof that the physical action completed; verify the resulting world state in a subsequent perception.

Stop both processes with `Ctrl+C`. Unset `FUSION_GGUF_MODEL`, `NLT_AGENT_LOOP_ENABLED`, and `NLT_AGENT_LOOP_ENDPOINT` when finished.

## Important limitations

- The agent-loop endpoint is loopback-only. Do not expose it publicly by changing the bind address or URL alone.
- Godot applies ASFDK-C# governance and independently validates physical preconditions. Fusion returns semantic intents only.
- The agent-loop and `SessionOrchestrator` are distinct workflows today. The embodied experience-to-learning update path and Advocate fusion bridge remain open engineering work.
- Legacy scripts such as `scripts/run_training_session.py` and `scripts/test_training_loop.py` have documented interface/import failures. Treat them as diagnostics, not validated end-to-end demos.
