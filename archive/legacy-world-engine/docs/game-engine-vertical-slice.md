# NeuroLift AI-Fusion Game Engine Vertical Slice

**Status:** Draft implementation spec  
**Date:** 2026-04-29  
**Owner:** Joshua W. Dorsey, Sr.  
**Agent:** Codex  
**Governance:** ORG-DEV-OTOI-1.0.0  

---

## Purpose

This document defines the first playable and observable vertical slice for the NeuroLift AI-Fusion training methodology: a Sims-like simulation environment where an AI Avatar experiences an executive function challenge, an AI Aide provides expert coaching, and the pair progresses toward measurable self-sufficiency before eventual fusion into an AI Advocate.

The first milestone is intentionally small: one Avatar, one Aide, one realistic scenario, one game world, one monitoring surface, and one measurable independence loop.

---

## Canonical Product Model

The working model for this repository is:

```text
Avatar -> Aide -> Advocate
```

### Avatar

An AI Avatar embodies one ADHD-related executive function challenge. The Avatar must experience realistic friction in daily-life scenarios, including mistakes, stress, overwhelm, delays, and consequences.

The Avatar is not a static role profile. It is a learning entity that develops coping skills through repeated simulated experience.

### Aide

An AI Aide is the professional or expert counterpart for the Avatar's specific executive function challenge. Its goal is to assist the Avatar only as much as needed, then gradually reduce support as the Avatar becomes self-sufficient.

The Aide also learns through experience. It observes what actually helps, what creates dependency, what escalates stress, and which intervention timing works best.

### Advocate

An AI Advocate is created only after the Avatar-Aide pair reaches the fusion criteria set by NeuroLift. Fusion combines:

- The Avatar's learned, experience-based understanding of the struggle
- The Aide's proven executive-function coaching expertise
- The pair's shared history of effective interventions and independence growth

This is the AI-Fusion methodology.

---

## Source Grounding

This spec is grounded in the cloned repo, Drive docs, Notion pages, and the user's current clarification.

### Repo Sources

- `AGENTS.md`
- `NLT-DEV-OTOI.md`
- `CLAUDE.md`
- `README.md`
- `QUICKSTART.md`
- `docs/architecture.md`
- `docs/active-threads.md`
- `src/avatars/base_avatar.py`
- `src/aides/base_aide.py`
- `src/simulation/session_orchestrator.py`

### Drive Sources

- `neurolift-ai-components.md`
- `architecture.md`
- `implementation_summary.md`
- `ADHD Executive Functions and Life Impacts`
- `NeuroLift RRT Advocate - Persona Fusion Mechanism`

### Notion Sources

- `Avatar -> Aide -> Advocate Architecture (Canonical)`
- `AI Avatar Simulation Framework - Real-World Testing Environment`
- `19 Advocates System - Complete Specification` (Notion page title; predates the 20-pair README roster, which is now canonical)
- `NeuroLift AI Fusion - Repository Project`
- `PROPRIETARY: AI-Fusion Framework - Revolutionary Neurodivergent AI Training`

---

## Recommended Game Track

**Recommendation:** Build the first game-engine slice as a 2D browser simulation using Phaser, TypeScript, and Vite, with a DOM-based monitoring interface layered beside or over the canvas.

This is a recommendation, not an autonomous architecture decision. Formal engine selection remains a human-governed architecture decision under `NLT-DEV-OTOI.md`.

### Why Phaser for the first slice

- The first experience is closer to a top-down Sims-like simulation than a 3D game.
- Phaser handles 2D scenes, sprites, cameras, timing, input, and asset loading well.
- A 2D slice is easier to make inspectable for observers with ADHD.
- The existing repo already has a React/Vite web app that can host or sit beside a Phaser canvas.
- The simulation rules can stay outside Phaser, preserving the Python/domain model concepts already present in `src/`.

### Architecture Rule

The game renderer must not become the source of truth.

```text
Simulation state -> renderer projection -> observer UI
```

Simulation owns the Avatar, Aide, scenario state, learning metrics, event timeline, task outcomes, and fusion readiness.

Phaser owns the visual world, sprites, camera, animation, tile layers, and input projection.

The DOM UI owns monitoring, accessibility controls, observer filters, event explanation, and scenario playback tools.

---

## First Vertical Slice

### Slice Name

`StayAlert: Apartment Morning Routine`

### Executive Function Challenge

Sustained attention with distractibility, cognitive fatigue, and task drift.

### Avatar

`StayAlert Avatar`

The Avatar attempts a morning preparation routine with multiple small tasks, realistic interruptions, and attention drains.

### Aide

`Focus Aide`

The Aide provides attention-specific support such as task chunking, environmental simplification, time-boxing, reset prompts, and recovery breaks.

### Scenario

The Avatar needs to get ready for a work meeting from an apartment environment.

Required tasks:

- Find and review meeting notes
- Prepare breakfast
- Pack work items
- Respond to one important message
- Leave on time

Stressors:

- Phone notification
- Misplaced item
- Background noise
- Ambiguous next step
- Time pressure
- Optional distracting side task

Consequences:

- Late departure
- Missed meeting prep
- Increased stress
- Reduced confidence
- Opportunity for Aide intervention
- Opportunity for independent recovery

### Target Outcome

The Avatar should eventually complete the scenario with reduced Aide intervention and stable self-recovery behaviors.

---

## Core Loop

```text
1. Scenario starts
2. Avatar receives task goal
3. World introduces realistic task demands and stressors
4. Avatar attempts task using current skill state
5. Simulation detects struggle signals
6. Aide chooses whether and how to intervene
7. Avatar retries or self-recovers
8. Consequences and learning are recorded
9. Independence score updates
10. Scenario repeats with variation until fusion gate criteria are met
```

The loop should support both real-time and step-through playback so observers can understand what happened without being overwhelmed.

---

## Simulation Entities

### Avatar State

- `id`
- `name`
- `executiveFunctionChallenge`
- `attentionEnergy`
- `stressLevel`
- `confidence`
- `cognitiveLoad`
- `currentGoal`
- `currentTask`
- `struggleSignals`
- `learnedStrategies`
- `independenceScore`
- `supportNeedLevel`

### Aide State

- `id`
- `name`
- `expertiseArea`
- `availableStrategies`
- `interventionHistory`
- `effectivenessByStrategy`
- `dependencyRisk`
- `supportFadeLevel`

### Scenario State

- `id`
- `name`
- `environment`
- `tasks`
- `stressors`
- `npcEvents`
- `timePressure`
- `successCriteria`
- `consequences`
- `repeatVariationSeed`

### Training State

- `sessionId`
- `attemptNumber`
- `eventTimeline`
- `interventions`
- `taskResults`
- `independenceTrend`
- `fusionReadiness`

---

## Observer Experience

People with ADHD struggles should be able to watch and understand the simulation without needing to parse a dense analytics dashboard.

### Observer Principles

- Keep the default view calm and low clutter.
- Explain events in plain language.
- Show only the most important state by default.
- Let deeper analysis unfold through tabs, filters, and playback.
- Prioritize cause-and-effect: what happened, why it mattered, what helped, and whether independence improved.

### Required Monitoring Panels

`World View`

The Phaser canvas showing the apartment, Avatar, task objects, stressors, and visible consequences.

`Avatar State`

Shows current task, stress, cognitive load, attention energy, confidence, and support need.

`Aide Intervention Log`

Shows when the Aide intervened, which strategy was used, why it was chosen, and whether it helped.

`Learning Timeline`

Shows scenario attempts over time with progress markers and repeated struggle patterns.

`Independence Meter`

Shows whether support need is decreasing across attempts.

`Fusion Gate`

Shows the current status of the criteria required before this pair can become an Advocate.

### Accessibility Requirements

- Pause, resume, step-forward, and replay controls
- Adjustable simulation speed
- Reduced motion mode
- Clear visual hierarchy
- Color-safe status indicators
- Plain-language event summaries
- Minimal flashing or surprise animation
- Optional detail levels: `Simple`, `Coach`, `Technical`

---

## Fusion Readiness Gates

The first slice should not implement final fusion, but it must model the gate.

A pair is not ready for fusion until the Avatar and Aide both satisfy measurable criteria.

### Avatar Criteria

- Completes target scenario without direct Aide intervention across repeated attempts
- Demonstrates self-recovery after attention drift
- Maintains tolerable stress level under realistic pressure
- Uses learned strategies without prompting
- Preserves task outcome quality, not just completion speed

### Aide Criteria

- Selects effective interventions when support is needed
- Reduces intervention frequency over time
- Avoids creating dependency
- Recognizes when silence is more appropriate than help
- Tracks which strategies improved independence

### Pair Criteria

- Independence trend is stable
- Support need decreases
- Scenario success generalizes across variations
- The event timeline contains enough struggle and support history for post-fusion reasoning

---

## 20-Pair System Alignment

The first slice should use `StayAlert`, but the engine must be built so the same loop can support all 20 Avatar-Aide pairs.

Canonical set for implementation planning (the README roster; 14 Executive Function, 6 Non-Executive Function):

| # | Pair | Target Challenge |
|---|---|---|
| 1 | StayAlert | Sustained attention |
| 2 | ImpulseGuard | Impulsivity control |
| 3 | FocusFlow | Hyperfocus management |
| 4 | Timely | Time blindness |
| 5 | MemoryMate | Working memory |
| 6 | MoodEase | Emotional regulation |
| 7 | TaskKickstart | Task initiation |
| 8 | CalmCore | Low frustration tolerance |
| 9 | Planner Pro | Prioritization and planning |
| 10 | SmoothSwitch | Transition difficulties |
| 11 | AwareMate | Self-monitoring |
| 12 | SteadyMind | Poor impulse control |
| 13 | FocusRecharge | Effortful focus fatigue |
| 14 | EffortAlign | Effort vs. productivity perception |
| 15 | StressShield | Stress sensitivity |
| 16 | SensoryBalance | Sensory sensitivity |
| 17 | SocialSync | Social challenges |
| 18 | SensorySeeker | Sensory-seeking behavior |
| 19 | ConfidenceCoach | Self-esteem and identity |
| 20 | RSDShield | Rejection sensitivity dysphoria |

Names and order come from the top-level `README.md`, which is canonical. Older Repo, Drive, and Notion sources use overlapping or superseded labels; where they disagree with the README, the README wins.

---

## Implementation Boundaries

### Recommended Frontend Shape

```text
apps/web/
  src/
    game/
      engine/
      scenes/
      systems/
      data/
      adapters/
    simulation/
      avatar/
      aide/
      scenarios/
      training/
    pages/
      SimulationLab.tsx
    components/
      monitor/
```

### Simulation Boundary

Keep deterministic simulation logic in plain TypeScript modules that can run without Phaser.

Phaser scenes should adapt state into visuals and route user controls back into the simulation.

### Python Core Boundary

The current Python core remains the conceptual and test-backed source for Avatar/Aide/session behavior. The web game slice can initially mirror the concepts in TypeScript for fast iteration, then integrate with the backend once the API contract is stable.

### Backend Boundary

Do not require Supabase, Cloudflare, or external LLM providers for the first slice. The first milestone should run locally with fixture data and deterministic scenario rules.

---

## Milestones

### Milestone 1: Static Simulation Lab

- Add a `SimulationLab` route in the web app
- Render the monitoring layout with fixture state
- Show the first scenario definition and Avatar/Aide state
- No game canvas required yet

Implementation note, 2026-04-29: Milestone 1 is implemented locally at `/simulation-lab`
with fixture state in `apps/web/src/simulation/lab/stayAlertMorningRoutine.ts`.
Frontend lint/build verification is pending because local dependency installation ran out
of disk space.

### Milestone 2: Playable 2D Room

- Add Phaser to the web app
- Render apartment room, Avatar marker, task objects, and simple movement
- Trigger scripted stressors and task state changes
- Keep all gameplay state outside Phaser scenes

### Milestone 3: Training Loop

- Implement attempt/retry loop
- Add struggle detection and Aide intervention selection
- Record event timeline and task outcomes
- Update independence score after each attempt

### Milestone 4: Observer Playback

- Add pause, step, speed, replay, and timeline filters
- Add plain-language event explanations
- Add simple/deep view modes

### Milestone 5: Fusion Gate Prototype

- Show readiness criteria
- Track Avatar, Aide, and pair-level readiness
- Keep fusion as a simulated gate, not a final Advocate creation process

---

## Team Handoff Packets

These are ready to pass to other agents when useful.

### Claude Code

Task: Review `docs/game-engine-vertical-slice.md` against the current Python architecture in `src/avatars`, `src/aides`, and `src/simulation`. Identify mismatches between the spec and the existing runtime contracts, especially `BaseAvatar`, `BaseAide`, and `SessionOrchestrator`.

Expected output: concise architecture review with proposed interface alignment changes.

### GitHub Copilot

Task: Prepare a TypeScript scaffold proposal for `apps/web/src/game` and `apps/web/src/simulation` that keeps Phaser scenes thin and simulation state renderer-independent.

Expected output: file tree plus minimal type definitions, no large implementation yet.

### Gemini

Task: Compare the 20-pair roster in the top-level `README.md` ("The 20 Avatar-Aide-Advocate Pairs") against the executive-function research corpus and recommend the cleanest canonical naming map for product, code, and docs.

Expected output: naming map, duplicate/overlap notes, and recommended final labels.

### ChatGPT or Claude

Task: Expand the `StayAlert: Apartment Morning Routine` scenario into a detailed scenario script with stressors, task graph, event triggers, consequence rules, and observer-facing explanations.

Expected output: scenario JSON draft plus human-readable scenario notes.

---

## Open Decisions

- Formal engine selection: Phaser 2D is recommended for the first slice, but final approval remains with Joshua.
- Canonical naming: repo, Drive, and Notion use overlapping names for several tracks.
- Data ownership: decide when the browser slice should integrate with the Python core or backend API.
- Fusion criteria thresholds: define numeric gates for independence, support reduction, generalization, and Aide effectiveness.
- Observer audience: decide whether the first observer UI is for internal team review, community validation, or eventual end users.

---

## Next Implementation Step

Implement Milestone 1 as a local web-app route with fixture data:

```text
/simulation-lab
```

The route should show a calm monitoring interface for the `StayAlert: Apartment Morning Routine` slice before adding Phaser. This lets the team validate information architecture, terminology, and accessibility before game rendering complexity arrives.
