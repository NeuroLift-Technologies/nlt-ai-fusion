# NeuroLift AI-Fusion — Compatibility API

This FastAPI application exposes the retained Avatar, Aide, session, scenario, and fusion API routes. It is an application/API surface, not a physical simulation server.

The authoritative physical world, including physics, movement, NPC execution, world time, and spatial state, lives in the sibling [`nlt-world-engine`](https://github.com/NeuroLift-Technologies/nlt-world-engine) Godot 4.7.2 project. The former Python `/api/world` router and its backing world implementation have been archived under [`archive/legacy-world-engine/`](../archive/legacy-world-engine/README.md).

## Quick Start

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Interactive docs: `http://localhost:8000/api/docs`

## Retained API routes

| Prefix | Purpose |
|---|---|
| `/api/health` | Health check |
| `/api/avatars/` | Avatar records and trait metadata |
| `/api/aides/` | Aide records |
| `/api/sessions/` | Cognitive training sessions |
| `/api/fusion/` | Fusion and Advocate operations |
| `/api/scenarios/` | Cognitive training scenario catalog |
| `/api/ai/` | AI/model-related operations |

There is intentionally no `/api/world` route in this compatibility API. Do not reintroduce a second physical-world authority here.

For the current system boundary, see [`docs/architecture.md`](../docs/architecture.md).
