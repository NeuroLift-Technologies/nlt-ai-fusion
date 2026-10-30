# CLAUDE.md — Repository Context for AI Agents

**Repository:** NeuroLift-Technologies/neurolift-ai-fusion  
**Governance:** ORG-DEV-OTOI-1.0.0  
**Last updated:** 2026-05-26

> **Are you in the right repo?** This file is for `neurolift-ai-fusion`. If you're working in `.github-private` or another NLT repo and reading this by accident, stop — read AGENTS.md and that repo's own `CLAUDE.md` instead.

---

## What This Repository Is

`nlt-ai-fusion` is the cognitive intelligence, learning, model-adapter, and application layer for NeuroLift Technologies' **Avatar–Aide–Advocate** system. It does not own the authoritative physical world. The sibling `nlt-world-engine` Godot 4.7.2 project owns world state, physics, movement, NPC execution, and physical consequences.

The system enables:
- **Avatars** — AI entities that simulate specific ADHD trait profiles (attention drift, task initiation difficulty, etc.)
- **Aides** — AI coaching agents with domain expertise (attention science, task management, emotional regulation)
- **Advocates** — Capabilities produced by fusing a trained Avatar–Aide pair; not a third independent source agent
- **Training sessions** — Structured interactions that generate learning data and coaching outcomes

---

## Repository Structure

For the current layout, browse the repo or run `git ls-files | head -50`. The key directories:

- `apps/api/` — FastAPI backend (Python 3.11+, exposes cognitive training and model APIs)
- `apps/web/` — Next.js 14 web app (TypeScript + Tailwind)
- `apps/mobile/` — Expo (React Native) iOS & Android
- `src/` — Python cognitive and learning logic: `avatars/`, `aides/`, `core/`, `simulation/session_orchestrator.py`, `simulation/scenarios/`, `fusion/`, `database/`
- `tests/` — pytest test suite
- `docs/` — current architecture, active threads, agent log, AI guidance, and integration contracts
- `config/` — YAML + JSON configuration
- `supabase/` — schema and migrations
- `archive/legacy-world-engine/` — preserved, non-runtime Python/Cloudflare/browser world implementations
- `.claude/` — Claude Code session governance (synced from `.github-private`; do not edit here)
- `.nltotoi/` — governance namespace (validator, contracts, index)

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Cognitive models and training workflows | Python 3.11+ |
| API Backend | FastAPI + uvicorn (`apps/api/`) |
| Web Frontend | Next.js 14 + TypeScript + Tailwind CSS (`apps/web/`) |
| Mobile (iOS + Android) | Expo (React Native) + TypeScript (`apps/mobile/`) |
| Monorepo tooling | npm workspaces + Turborepo |
| Database | Supabase (PostgreSQL) with Row-Level Security |
| Testing | pytest (Python) |
| CI/CD | GitHub Actions (`python-app.yml`, `web.yml`, `mobile.yml`, `shared-ci.yml`) |
| Infrastructure | Cloudflare (Workers, Pages) |
| MCP servers | See `mcp-config.yaml` — GitHub MCP + 13 Cloudflare MCP endpoints |

---

## Commands

### Python cognitive workflows + API

```bash
# Run all tests (config: pytest.ini)
pytest

# Run a single test file
pytest tests/test_<module>.py

# Install deps
pip install -r requirements.txt
pip install -r apps/api/requirements.txt

# Start the FastAPI backend locally
cd apps/api && uvicorn main:app --reload --port 8000
```

### Web (Next.js)

```bash
cd apps/web
npm install            # first time
npm run dev            # dev server
npm run build          # production build
npm run lint
```

### Mobile (Expo)

```bash
cd apps/mobile
npm install            # first time
npx expo start         # dev (iOS Simulator / Android emulator / device)
npx expo prebuild      # generate native projects
```

### Monorepo (Turborepo)

```bash
npx turbo run build    # build everything
npx turbo run test     # run all test pipelines
npx turbo run lint     # lint all packages
```

### Governance

```bash
# Validate governance compliance (if .nltotoi/scripts/ provisioned locally)
bash .nltotoi/scripts/validate-governance.sh --strict

# Or use the slash command in a Claude Code session
# /governance-check
```

---

## Key Architectural Principles

1. **Privacy-first** — Data retention is ephemeral by default; all overrides require human approval. Enforcement points: data layer in `src/database/`, RLS policies in `supabase/`.
2. **Human agency** — Agents are advisory; all strategic and architectural decisions belong to humans (Joshua W. Dorsey, Sr. is final authority). Reflected throughout `src/advocates/` and escalation paths.
3. **Graceful degradation** — All Supabase-dependent features must fall back gracefully when DB is unavailable. Implementation lives in `src/core/` (database abstraction); consult before adding new Supabase calls.
4. **TOI-OTOI compliant** — All components implement the Terms of Interaction framework. See `TOI-OTOI-INTEGRATION.md` for the conformance contract.
5. **Modular design** — Avatars, Aides, and Advocates are independently swappable. Each subsystem lives in its own `src/<role>/` directory with a stable interface boundary.

---

## Development Conventions

### Python Style

- Follow PEP 8
- Type hints on all public functions and methods
- Docstrings on all public classes and methods
- No bare `except:` — always catch specific exceptions

### Testing

- Test file naming: `test_<module_name>.py`
- Run tests: `pytest` (configured in `pytest.ini`)
- Tests live in `tests/`
- Aim for isolation — mock external dependencies (Supabase, etc.)

### Imports

- Use absolute imports from the `src/` root
- No circular imports

### Database

- All DB interactions go through the abstraction layer in `src/core/`
- Never expose raw SQL in business logic layers
- Always handle the case where Supabase is unavailable

---

## Quirks Worth Knowing

- **Physical-world boundary.** The authoritative simulator is the sibling `nlt-world-engine` Godot project. `src/` contains cognitive models, training orchestration, fusion logic, and adapters. Do not add a competing Python/Cloudflare/browser world runtime.
- **Supabase availability is not guaranteed.** Every DB call path must work when Supabase is down. New code that assumes always-on Supabase will fail in CI's `pgsa-portability-gate.yml`. Consult `src/core/database/` for the established fallback pattern before adding new queries.
- **RLS policy changes are escalation-required.** Schema migrations and RLS edits in `supabase/` trigger the escalation rule in OTOI §4.4. Don't push a schema change without an escalation record.
- **Turborepo cache is real.** If `npx turbo run build` succeeds suspiciously fast on a fresh checkout, the cache is hot. To force a clean build: `npx turbo run build --force`.
- **Expo dev client may be required.** Some native modules in `apps/mobile/` need a dev client build (`npx expo run:ios` / `run:android`) rather than the Expo Go app. Check `apps/mobile/app.json` for any custom native modules before assuming Expo Go works.
- **`.claude/` is synced from `.github-private`.** The propagation workflow (`governance-auto-propagate.yml` in `.github-private`) overwrites `.claude/` here on every nightly run. To change session governance behavior, open a PR against `.github-private/.claude/` — not the copy here. Repo-specific overrides belong in `.claude/settings.local.json` (never overwritten).
- **Two `mcp-config.yaml` files.** This repo's `mcp-config.yaml` is sourced from `.github-private` and lists GitHub MCP + 13 Cloudflare MCP servers. Coordinate any change with Joshua.

---

## MCP Configuration

MCP servers available to agents in this repo are declared in `mcp-config.yaml` at the repo root. The set includes:

- **GitHub MCP Server** (HTTP/OAuth)
- **Cloudflare MCP servers** (13): docs, bindings, builds, observability, radar, containers, browser, logpush, AI Gateway, AutoRAG, audit logs, DNS analytics, DEX, CASB, GraphQL

New MCP servers and credential changes must be coordinated with Joshua W. Dorsey, Sr. before merging.

---

## Required Reading for New Agents

Before writing any code, read these files in order:

1. `NLT-DEV-OTOI.md` (repo root synced copy) — OTOI constitutional document
2. `AGENTS.md` — Agent coordination gateway
3. `CLAUDE.md` — This file ✓
4. `docs/active-threads.md` — Current work and ownership
5. `docs/architecture.md` — System architecture

If `NLT-DEV-OTOI.md` is missing in the repository root, request a run of **Sync Governance (Public)** (`.github/workflows/sync-governance-public.yml`) to refresh governance docs from `NeuroLift-Technologies/.github-private`.

The `.claude/hooks/session-start.sh` hook prints this reading order automatically at session start.

---

## Escalation

Any of the following **requires escalation** to Joshua W. Dorsey, Sr. before proceeding:

- Changes to the Avatar or Aide base class interfaces
- New external service integrations
- Database schema migrations
- Changes to RLS policies or data retention rules
- LLM provider decisions
- Production deployment steps

**Contact:** `info@neuroliftsolutions.com`

In a Claude Code session, use `/escalate <topic>`.

---

## Governance

This repository operates under **ORG-DEV-OTOI-1.0.0**. All agents must:

- Complete SOP-NLT-001 onboarding before writing code
- Use the commit format: `[AGENT_NAME] type(scope): description`
- Register at session start in `docs/agent-log/registrations/` (or `/register-session`)
- Write a handoff record at session end in `docs/agent-log/handoffs/` (or `/handoff`)

---

## Quick Reference

| What | Where / How |
|---|---|
| Final authority | Joshua W. Dorsey, Sr. — escalate when in doubt |
| Escalation contact | `info@neuroliftsolutions.com` (or `/escalate`) |
| Commit format | `[AGENT_NAME] type(scope): description` |
| Session register | `/register-session` or `templates/agent-registration.json` |
| Session handoff | `/handoff` or `templates/handoff-record.json` |
| Intent log | `/intent-log <topic>` or `templates/intent-log.md` |
| Governance check | `/governance-check` or `bash .nltotoi/scripts/validate-governance.sh` |
| Run tests | `pytest` (Python) / `npx turbo run test` (monorepo) |
| Web dev server | `cd apps/web && npm run dev` |
| Mobile dev server | `cd apps/mobile && npx expo start` |
| API dev server | `cd apps/api && uvicorn main:app --reload` |
| Canonical governance | `NeuroLift-Technologies/.github-private` |
| OTOI version | `ORG-DEV-OTOI-1.0.0` |
| HAIEF | https://elevaitionfoundation.org |

---

*Repository context for AI agents | NeuroLift Technologies | ORG-DEV-OTOI-1.0.0*
