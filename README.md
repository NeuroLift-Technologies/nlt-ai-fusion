# NeuroLift AI Fusion

**Full-Stack Avatar-Aide-Advocate Training Platform**

A full-stack web and mobile platform backed by a Python AI simulation engine. AI Avatars with ADHD traits experience authentic life struggles in a Sims/RPG-style environment while AI Aides provide real-time coaching. After sufficient training they fuse into Advocates that combine lived understanding with expert solutions.

> **Sibling repo:** [`nlt-world-engine`](https://github.com/NeuroLift-Technologies/nlt-world-engine) owns the **physical simulation layer**. Godot 4.7.2 is the target runtime; `WorldEngine/` is the retained UE reference implementation. This repo owns the **intelligence**—ADHD trait models, Aide coaching, session orchestration, and fusion. The closed-loop agent contract is defined, but the live Fusion ↔ Godot runtime connection is not yet wired.

```yaml
ai_assistant_directive:
  priority: 1
  instruction: "Before performing any development or coding tasks, read NLT-DEV-OTOI.md."
  description: "NLT-DEV-OTOI.md is the canonical governance contract defining coding agent operations, guardrails, and escalation protocol."
  required_file: "NLT-DEV-OTOI.md"
```

## Quick Start

### API (FastAPI — Python)
```bash
cd apps/api
pip install -r requirements.txt
PYTHONPATH=../../src uvicorn main:app --reload
# → http://localhost:8000/docs
```

### Web App (Next.js)
```bash
cd apps/web
corepack enable
pnpm install --frozen-lockfile
cp .env.local.example .env.local   # set NEXT_PUBLIC_API_URL
pnpm dev
# → http://localhost:3000
```

### Mobile App (Expo — iOS & Android)
```bash
cd apps/mobile
npm install
cp .env.example .env
npx expo start
# → scan QR with Expo Go on your device
```

### Simulation Engine (Python — Intelligence Layer)
```bash
pip install -r requirements.txt
pytest
```

> **Note:** The physical simulation runtime is in [`nlt-world-engine/world-engine-godot`](https://github.com/NeuroLift-Technologies/nlt-world-engine/tree/main/world-engine-godot), not this repo. This repo provides the Python intelligence (Avatar trait models, Aide coaching, session orchestration). The legacy lightweight Python world in `src/simulation/environment/` is for testing and reference only; it is not a second physical source of truth for a Godot integration.

### Physical-world agent loop

The `nlt.agent-loop.v1` contract describes a closed-loop boundary between the two repositories:

```text
Godot physical perception → Fusion semantic intent → Godot validation/execution → next perception
```

The world engine supplies an agent-specific snapshot of physical facts (self state, scene, visible
entities, and affordances). Fusion may respond with semantic intents such as `approach`, `look_at`,
`use`, `sit`, `rest`, `communicate`, or `wait`—never coordinates, velocity, teleportation, or
object-state writes. Godot applies ASFDK-C# governance at intent ingress, then independently
validates current physical conditions before executing consequences. Fusion returns semantic
intent only; it does not govern or execute physical effects.

The protocol and current status are documented in the
[agent-loop feature overview](https://github.com/NeuroLift-Technologies/nlt-world-engine/blob/main/docs/agent-loop.md)
and [versioned contract](https://github.com/NeuroLift-Technologies/nlt-world-engine/blob/main/docs/contracts/agent-loop-v1.md).
Fusion's `src/fusion/agent_loop.py` provides the validating decision seam, exposed locally by
`src/fusion/agent_loop_http.py` at `POST http://127.0.0.1:8001/agent-loop/perception`. Set
`FUSION_AGENT_LOOP_MODEL` to `baseline`, `gguf` (with `FUSION_GGUF_MODEL`) or `transformers` (with
`FUSION_TRANSFORMERS_MODEL`); with neither variable set the endpoint uses a deterministic model-free
control decision. `FUSION_AGENT_LOOP_TIMEOUT` (default 15 s) bounds each decision; see
[docs/agent-loop-model-adapter.md](docs/agent-loop-model-adapter.md). Inference runs outside the ASGI event loop, and malformed,
stale, or unavailable decisions fail closed. The endpoint is loopback-only and does not perform
ASFDK governance or physical execution. The existing `nlt.state-feed.v1` is a separate observer
feed, not this control protocol.

#### Agent-loop status (AGENT-LOOP-003, 2026-10-29)

- **Decision source.** Fusion registers each agent (F0), remembers its last decisions and their
  outcomes (F1), derives a goal from the Avatar's state (F2), and ranks the choices a model is
  shown (F3). Without a model, the goal baseline takes the first-ranked option (F4).
- **Ranking, not filtering.** Only five rules drop a choice: three anti-repeat rules, a reach guard
  for targets the avatar will have walked out of reach of, and targets it has been stuck short of
  twice. Everything else is offered in ranked order: goal-relevant targets, then places not yet
  visited, then the rest, approaches before holding actions. Actions on targets that do not serve
  the goal are demoted, never forbidden. With nothing goal-relevant in view, the ranking explores:
  unvisited places farthest first, and a walk under way is finished first.
- **Bounded decisions.** Each decision is limited by `FUSION_AGENT_LOOP_TIMEOUT` (15 s). A model
  call that overruns gets 503 and quarantines the model until it returns.
- **Measured** (headless Godot 4.7.2, 240 s, CPU): the goal baseline walks from the spawn into the
  office and sits at a desk, with no engine rejections. Qwen3-0.6B reached the office in 2 of 5
  runs; it takes the first-ranked option only 12-34% of the time, so the model, not the ranking,
  limits it. Qwen3-1.7B and Qwen2.5-3B were not reliably better and are about 3× slower. Details:
  [AGENT-LOOP-003 brief §12](docs/specs/AGENT-LOOP-003-fusion-state-and-goals-brief.md).

### JavaScript dependency boundaries

The repository currently has multiple JavaScript package-manager surfaces:

| Path | Lockfile | Use for |
| --- | --- | --- |
| `apps/web/` | `pnpm-lock.yaml` | Next.js web surface and `/simulation-lab` |
| `apps/mobile/` | `package-lock.json` | Expo mobile starter |
| `cloudflare-engine/` | `package-lock.json` | World Engine Worker and local Wrangler CLI |

Use the lockfile in the package you are changing. For web-only dependency work,
run pnpm inside `apps/web/` so the checked-in `pnpm-lock.yaml` stays in sync and
avoid creating an `apps/web/package-lock.json`. For the Cloudflare worker, run
`npm ci` from `cloudflare-engine/` so local `npx wrangler ...` commands use the
repo-pinned Wrangler v4 dependency instead of a global install.

---

[![Deploy to Cloudflare Workers](https://deploy.workers.cloudflare.com/button)](https://deploy.workers.cloudflare.com/?url=https://github.com/NeuroLift-Technologies/neurolift-ai-fusion)
[![Visit Site](https://img.shields.io/badge/Visit%20Site-neuroliftsolutions.com-F38020?style=for-the-badge&logo=cloudflare&logoColor=white)](https://neuroliftsolutions.com)

## 🎯 Project Vision

**Mission:** "Nothing About Us Without Us" - neurodivergent voices lead development

This project implements **experiential learning** for AI systems, not traditional data training. Avatars don't just analyze patterns about ADHD - they actually live through the struggles, experience real stress, make mistakes, and learn through doing with Aide support.

### Core Innovation

Nobody else is training AI this way. While the industry has solved infrastructure (MCP, A2A protocols), two critical gaps remain:
- **User preference enforcement: UNSOLVED** ← OTOI addresses this
- **AI capability reliability: UNSOLVED** (38.1% computer use accuracy, 85% agentic AI failure rate)

This simulation approach addresses both gaps through authentic experiential learning.

## 🏗️ Architecture Overview

### The Avatar-Aide-Advocate Process

#### Phase 1: Avatar Creation
- Each Avatar embodies a specific ADHD trait/executive function deficit
- Experiences authentic stress, frustration, and failure patterns
- Lives through simulated everyday scenarios where their specific trait creates challenges
- Makes real mistakes with real consequences in the virtual environment

#### Phase 2: Aide Development
**Foundation Components:**
1. **RRT (Rapid Response Team) Core** - Pre-existing therapeutic knowledge with dormant burnout response
2. **PhD-Level Expertise** - Deep academic research on specific executive functions
3. **Real-World Feedback** - Input from people with ADHD who've mastered that specific area

**Role:** Coach, therapist, and assistant operating IN the simulation environment alongside the Avatar

#### Phase 3: Simulation Training
**Environment:** Sims/RPG-style virtual world — the target physical runtime is **[Godot 4.7.2 in `nlt-world-engine`](https://github.com/NeuroLift-Technologies/nlt-world-engine/tree/main/world-engine-godot)**. `WorldEngine/` retains the UE 5.8 reference implementation. The transport-neutral agent-loop contract is defined, and Fusion exposes a loopback HTTP endpoint at `POST /agent-loop/perception`. With Godot's opt-in loop enabled, the two run end to end over loopback HTTP; see "Agent-loop status" above.

**Scenario Categories:**
- **Workplace:** HR compliance, meetings, project management, performance reviews
- **Personal:** Household management, social relationships, financial tasks, self-care
- **Social Dynamics:** Rejection sensitivity, emotional regulation, social cues

**Key Environmental Features:**
- **Neurotypical NPCs:** Complete same tasks easily, creating realistic social comparison
- **Biased NPCs:** Exhibit workplace discrimination, microaggressions, ableism
- **Random Dysfunction Injection:** Suddenly adds new executive function challenges
- **Real Consequences:** Failed tasks have meaningful impact, creating authentic learning pressure

#### Phase 4: Fusion into Advocate
**When:** After Avatar demonstrates consistent independence across scenarios  
**How:** Combine Avatar's experiential struggle awareness with Aide's proven expertise  
**Result:** An Advocate that both understands what ADHD struggles feel like AND knows what actually works

## 🎮 The 20 Avatar-Aide-Advocate Pairs

> Canonical persona catalog (spec): `StayAlert` → `RSDShield` (20 advocates). These are **catalog entries**, not an implementation status claim — this repo implements the generic `base_advocate` + prototype pairs (see [`docs/implementation_summary.md`](docs/implementation_summary.md)); the [`nlt-adhd`](https://github.com/NeuroLift-Technologies/nlt-adhd) App scaffolds all 20 dirs in `src/advocates/` (MVP wires 6: 01, 04, 05, 07, 09, 20 — the remaining 14 are stubs).

### Executive Function Focused (14 pairs):
1. **StayAlert** - Sustained attention deficit
2. **ImpulseGuard** - Impulsivity control
3. **FocusFlow** - Hyperfocus management
4. **Timely** - Time blindness
5. **MemoryMate** - Working memory deficits
6. **MoodEase** - Emotional regulation
7. **TaskKickstart** - Task initiation difficulty
8. **CalmCore** - Low frustration tolerance
9. **Planner Pro** - Prioritization and planning
10. **SmoothSwitch** - Transition difficulties
11. **AwareMate** - Self-monitoring challenges
12. **SteadyMind** - Poor impulse control
13. **FocusRecharge** - Effortful focus fatigue
14. **EffortAlign** - Effort vs. productivity perception

### Non-Executive Function (6 pairs):
15. **StressShield** - Stress sensitivity
16. **SensoryBalance** - Sensory sensitivity
17. **SocialSync** - Social challenges
18. **SensorySeeker** - Sensory-seeking behavior
19. **ConfidenceCoach** - Self-esteem and identity
20. **RSDShield** - Rejection sensitivity dysphoria

## 🎮 Unreal Engine AI Tools (Retained Reference)

> **Note:** This catalog describes the retained UE 5.8 reference project in [`nlt-world-engine/WorldEngine`](https://github.com/NeuroLift-Technologies/nlt-world-engine). Godot 4.7.2 is the target physical runtime; the UE implementation remains a frozen behavioral oracle until the port passes conformance.

**What this repo needs to know:**

- The UE WorldEngine is the retained reference for Mass Entity population, StateTree behavior, Smart Objects, deterministic tick, and RL/PPO training (Learning Agents plugin); it is not the target runtime.
- The retained UE reference's in-engine **LLM control path** (`UMLInferenceBridgeSubsystem` in nlt-world-engine) drives `AAvatarAIController::ExecuteLLMCommand` directly — the model controls the actor inside the engine, not through the public web server.
- Fusion's transport-neutral agent-loop contract is documented in [`docs/architecture.md`](docs/architecture.md); the Godot runtime reaches it over loopback HTTP (opt-in), and no other transport is selected yet.

UE-side plugin/tooling details: see the **UE Plugins Enabled** table and subsystem docs in [`nlt-world-engine/README.md`](https://github.com/NeuroLift-Technologies/nlt-world-engine).

---

## 🔁 CI and Repository Automation

### Workflows

| Workflow | Role | Trigger |
|----------|------|---------|
| `shared-ci.yml` | Shared lint, test, and security jobs (defined locally — the retired `.github-private` reusable workflows no longer exist) | push to main, PR to main, workflow_dispatch |
| `python-app.yml` | Python/API checks for `src/`, `tests/`, `backend/`, `requirements.txt`, `pytest.ini`, `apps/api/` | push to main, PR to main (when those paths change), workflow_dispatch |
| `redteam-ci.yml` | Progressive 3-level clearance (syntax → coverage → security) | push to main, PR to main |
| `pgsa-portability-gate.yml` | Secrets scanning + provenance validation | push to main, PR to main |
| `pr-cleanup.yml` | Stale PR marking, auto-close, merged branch deletion | daily schedule + manual |
| `sync-governance-public.yml` | Syncs governance docs from `.github-private` | repository_dispatch + weekly schedule |

### Key constraints

- Pushes to non-`main` branches do not auto-run CI unless a PR targets `main`
- `shared-ci.yml` defines its lint/test/security jobs locally (the previous reusable workflows in `.github-private` were retired)
- `pr-cleanup.yml` exempts draft PRs from staleness; branch deletion skips protected branches and forks
- Governance sync requires `document_name` + base64-encoded `content` in `repository_dispatch` payload

Full CI/CD documentation: [`docs/CI_HARNESS_README.md`](docs/CI_HARNESS_README.md)

### 🌐 Cloudflare Integration

Our infrastructure leverages Cloudflare for:
- **WordPress Hosting**: Optimized performance and caching
- **Cloudflare Workers**: Serverless edge computing
- **Cloudflare Pages**: Static site hosting for documentation and app interfaces
- **CDN**: Global content delivery for fast access
- **Security**: DDoS protection, WAF, and bot mitigation

| Worker | Purpose |
|--------|---------|
| **`neurolift-world-engine`** | Separate Cloudflare ECS prototype (`cloudflare-engine/src/index.ts`) with a WebSocket `/connect` gateway; it is not the Godot 4.7.2 runtime or the `nlt.agent-loop.v1` Fusion ↔ Godot connection |

Deployment details: [`docs/cloudflare/CLOUDFLARE_SETUP.md`](docs/cloudflare/CLOUDFLARE_SETUP.md)

## 🛡️ Privacy-First Design

<!-- 
NON-NEGOTIABLES FOR PRODUCTION & END USER USE:
The following 4 principles are mandatory requirements for any production 
deployment or end-user facing application of this framework.

Note: "Local Processing" does not apply during development and training phases,
where cloud/remote processing may be used for Avatar-Aide simulation training.
-->

- **Local Processing:** All processing happens locally *(exempt during development/training)*
- **No Data Collection:** No external data transmission without explicit consent
- **No Monetization:** User data never monetized
- **Transparent:** Clear about what data exists and where

> **⚠️ Production Requirements:** The above 4 principles are **non-negotiable** for production and end-user use. "Local Processing" may be relaxed during development and training phases only.

## 🏆 Success Criteria

1. **Structure Complete:** Repository organized exactly as specified
2. **Documentation Clear:** Any neurodivergent developer can understand the system
3. **Prototype Working:** At least one Avatar-Aide pair trains successfully
4. **Progress Measurable:** Can track Avatar learning from struggle to independence
5. **Realistic Simulation:** Scenarios authentically represent ADHD challenges
6. **Fusion Validated:** Resulting Advocate demonstrates both empathy and expertise
7. **Community Ready:** Code is documented well enough for contributors

## 🤝 Contributing

This project follows "Nothing About Us Without Us" principles. We welcome contributions from:
- Neurodivergent developers and researchers
- ADHD specialists and therapists
- AI/ML researchers interested in experiential learning
- Anyone committed to authentic representation

Formal `CONTRIBUTING.md` guidance is being drafted; for now, follow the CI workflow and documentation standards in this README.

## 📚 Documentation

- [Architecture Overview](docs/architecture.md)
- [Quick Start Guide](QUICKSTART.md)
- [TOI-OTOI Integration](TOI-OTOI-INTEGRATION.md)
- [Implementation Summary](docs/implementation_summary.md)
- [Cloudflare Setup Guide](docs/cloudflare/CLOUDFLARE_SETUP.md)

## 📞 Contact

**Founder:** Joshua W. Dorsey, Sr. (ADHD cognitive profile)
- Multi-threaded thinker — may switch contexts frequently
- Prefers iterative development with frequent check-ins
- Values authentic neurodivergent representation
- **Email:** neuro.edge24@gmail.com
- **Website:** [neuroliftsolutions.com](https://neuroliftsolutions.com)

## 📄 License

[License TBD - Open Source]

## 🎯 Current Status

**Development Phase:** Fusion & AI Model Layer (Phases 5–6); Godot 4.7.2 migration and the Fusion ↔ Godot runtime connection remain in progress.
**Last Updated:** September 2026  
**Next Milestone:** Expand remaining 16 Avatar-Aide pairs → real-world testing with neurodivergent community  
**Spec:** [`docs/specs/advocate-model-fusion-spec.md`](docs/specs/advocate-model-fusion-spec.md) + [`docs/research/Trajectory Distillation for Behavioral AI Fusion.md`](docs/research/Trajectory%20Distillation%20for%20Behavioral%20AI%20Fusion.md)

---

**This project (together with [`nlt-world-engine`](https://github.com/NeuroLift-Technologies/nlt-world-engine)) represents a new paradigm in AI training — learning through experience, not just data. Welcome to building something genuinely innovative.**
