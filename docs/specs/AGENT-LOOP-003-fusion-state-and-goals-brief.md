# AGENT-LOOP-003 — Give the Fusion decision source state, goals and memory: agent brief

**Author:** Claude (spec only; no code changed, nothing built or run) · **Date:** 2026-10-28 · **For:** coding agents (Codex, OpenCode, Cline, Hermes, CC) · **Authority:** Joshua W. Dorsey, Sr.
**Repos read:** `nlt-world-engine` @ `8d3b712` and `nlt-ai-fusion` (renamed from `neurolift-ai-fusion` on 2026-10-28) @ `2af2778`, both `main` as of 2026-10-22. Shallow clones. Every "risk" below is a prediction until an agent measures it.
**Proposed thread IDs (Joshua assigns):** `AGENT-LOOP-003` in world-engine, `TH-028` in Fusion. **Do not mark T6 acceptance 4 met until F5 passes.**

---

## 0. Why this brief exists

AGENT-LOOP-002 T6 acceptance 4 (model-driven run) failed twice (2026-10-21, 2026-10-22). The Fusion adapter was fixed to offer every verb (Fusion#126), and the model still did not behave. The cause is not the engine and not the model size alone:

**The local model has no memory, no goal and no need.** Each decision is a stateless call. The input is one system prompt (`SYSTEM_PROMPT` in `src/fusion/agent_loop_choices.py`: mechanics only, nothing about who the agent is or what it wants) plus the current perception (`tick`, `scene`, `self`, `visibleEntities`). Generation is grammar-constrained, `temperature=0.0`, `max_tokens=48` (`src/fusion/gguf_agent_decision.py`).

Result: with nothing to choose by, a 0.6B model at temperature 0 takes the first listed option. Observed: 18 of 18 perceptions returned `look_at <first entity>`, in every ordering. In-engine: 1 `look_at`, then 33 `wait`, then the avatar froze (see §5, dead end).

## 1. Where state belongs (this resolves an apparent conflict)

`docs/contracts/agent-loop-v1.md` §2 says semantic needs and coaching history are **not** copied into the perception, because Fusion already owns them. `FusionAgentLoop` (`src/fusion/agent_loop.py`) says the injected decision source "owns how Avatar/Aide state informs cognition."

So: **do not add goals or needs to the perception and do not change the schema.** The fix lives entirely on the Fusion side, inside the decision source. The engine keeps sending physical facts only.

## 2. Rules that apply to every task

- Fusion owns semantics, the engine owns physics. Intents stay semantic: no coordinates, velocity, teleports or state writes.
- Keep `nlt.agent-loop.v1` unchanged (no schema or version bump) unless Joshua decides otherwise (§5).
- Keep ingress fail-closed, the loop opt-in (`NLT_AGENT_LOOP_ENABLED=1`), ASFDK governance at ingress unchanged.
- Read `NLT-DEV-OTOI.md` first. Update `docs/active-threads.md` in each repo at start and end. New handoffs go in `docs/agent-log/handoffs/`.
- Work on a branch and open a PR per task. Do not push to `main`.

## 3. Tasks (Fusion repo unless noted). Order matters: F1 → F2 → F3 → F4 → F5.

### F1 — A stateful, per-agent decision source
Replace the stateless call with a decision source that is bound to an agent and remembers.
- Key state by `perception.agentId` (maps to `avatar_id`). One writer per agent; no cross-agent sharing.
- Keep a bounded history (ring buffer, N configurable, default ~8) of: tick, scene id, chosen intent, and the outcome.
- **Outcome source: verify first.** Check whether `nlt.agent-loop.v1` result messages (`accepted` / `rejected` + `reason`) actually reach the Fusion HTTP endpoint (`agent_loop_http.py`). If not, derive the outcome from the next perception (position delta, scene change, entity `occupied`). Record which one you used.
- Must satisfy: the stateful source plugs into `FusionAgentLoop(decide=...)` unchanged.

### F2 — A real goal, from the Avatar/Aide, not invented
Feed the decision with the avatar's actual current situation.
- Read from `BaseAvatar` (`src/avatars/base_avatar.py`): names to verify before use: `get_state_summary()`, `current_state` (`AvatarState`), `stress_level`, `get_adhd_trait_impact()`, `assess_burnout_risk()`, and the pair's current scenario / deficit.
- Turn that into a short semantic goal string and one or two needs (for example "start the task you have been avoiding", "recover after stress"). Keep it small: a 0.6B model will not use a long prompt.
- Put the goal, the needs and the recent-history window into the prompt. Do **not** put raw avatar internals into anything sent to Godot.

### F3 — Remove the positional bias in the decision itself
Prompt text alone will not fix "picks the first entity" on a 0.6B model, so enforce it structurally:
- Present entities with a computed distance and goal relevance, ordered by goal relevance (not engine order).
- **Anti-repeat in the grammar:** in `grounded_choices` / `decision_schemas`, drop a `(verb, target)` pair that was just chosen and whose outcome changed nothing. This directly prevents the 81-of-84 `look_at` loop.
- `look_at` should not be the default pick. Consider ranking `approach` and `use` ahead of it when a goal-relevant target exists.

### F4 — A deterministic goal-driven baseline decision source
Honest pushback: a 0.6B model may not exploit a goal even with F1–F3. Do not make the engine's acceptance depend on it.
- Add a rule-based decision source with the same interface that follows the F2 goal and the F3 ranking (go to the door, `use` it, `sit` at a desk, `rest` when stressed).
- Use it to verify the full loop and the engine's T6 behaviour without a model. Then run the Qwen source against the same scenarios and compare. Report both.
- This is also the natural stand-in until each Avatar's own RL model (`bind_model`) is the decision source; the GGUF adapter is a placeholder for it.

### F5 — Re-run T6 acceptance 4 (dev PC; world-engine coordination)
- Close the Godot editor first. With the editor open on the 7.8 GB dev PC, Windows pages out Qwen's weights and decisions take 120–400 s. Record free RAM.
- Run the baseline source and the Qwen source, each on the same scenario. Pass criteria: the avatar goes through a door with `use`, moves inside, and performs `sit`, `use` or `rest` on furniture, with the history window showing it is not repeating itself.
- Log decisions per source: verb counts, distinct targets, and whether the avatar ever stalls.

## 4. Out of scope

- Any change to the engine's physics, scenes or `nlt.agent-loop.v1` schema.
- `SessionOrchestrator` training integration beyond reading avatar state (separate thread; this brief only needs the read path).
- Choosing a larger model. Revisit only after F4 shows whether the bottleneck is the model or the input.

## 5. Needs Joshua (not an agent's call)

1. **Dead end with nothing in range.** Perception range is 25 m. From the plaza spawn no door is in range, so Fusion has no targeted verb to choose, and `wait` now freezes the avatar for good. Fusion cannot fix this alone. Options: (a) `wait` resumes the wander fallback only when nothing is visible (engine); (b) spawn or perceive so a door is always in range (engine); (c) add an `explore` verb (schema bump, both repos). (a) or (b) avoids a schema change; this brief assumes one of them lands in the engine.
2. Whether F4's rule-based source is acceptable as the acceptance baseline, or acceptance 4 must be model-driven only.
3. Contract §3 clarification wording (already open in AGENT-LOOP-002).

## 6. Risks (predictions, not measured)

- A 0.6B model at 4–5 s per decision (grammar sampling) may be too slow for a responsive loop regardless of input; F4 separates that question from the logic.
- Goal derivation from `BaseAvatar` may expose fewer usable fields than the names suggest; check before building F2 on them.
- Anti-repeat can wedge an agent that legitimately needs to repeat; give it a reset when state changes.

---

## 7. Addendum — verified against the code (2026-10-28)

**Author:** Claude (Claude Code session) · Read-only checks against the same commits as the brief (`nlt-ai-fusion` @ `2af2778`, `nlt-world-engine` @ `8d3b712`). Sections 0–6 above are unchanged. Where this addendum and a "names to verify" note above differ, this addendum is the checked state.

### 7.1 Confirmed as written
- `SYSTEM_PROMPT` (`src/fusion/agent_loop_choices.py`) covers mechanics only. `LlamaCppAgentLoopDecision` calls with `temperature=0.0`, `max_tokens=48` (`src/fusion/gguf_agent_decision.py`).
- `grounded_choices` lists targets **in perception order**, so the first-entity bias is structural. F3's reordering is the right lever, not prompt wording.
- `FusionAgentLoop(decide=...)` (`src/fusion/agent_loop.py`) validates the perception, calls `decide`, then validates the intent. F1–F4 can live entirely in the decision source.

### 7.2 F1 "outcome source": results do not reach Fusion
- Fusion's HTTP app exposes one route, `POST /agent-loop/perception` (`src/fusion/agent_loop_http.py`). There is no result endpoint.
- The engine receives the ingress result in `world-engine-godot/Agents/FusionHttpLink.cs` (`ingress.SubmitAsync(...)`) and only logs it locally.
- **So F1 derives the outcome from the next perception.** That is consistent with contract §4 ("the next perception snapshot is the physical source of truth"). Sending results to Fusion would be an engine transport change (not a schema change); it is not needed for F1.
- `world-engine-godot/AgentLoopEndpoint/Controllers/AgentLoopController.cs` references an `/agent-loop/intent` path. It appears to be a separate, earlier ASP.NET path, not the live Godot link. Not confirmed.
- **Engine detail that limits what an outcome can show:** `TaskAnchor.IsOccupiedFor` reports an anchor as occupied only when someone *else* holds it. An agent's own `sit` or `use` never flips `occupied` in its own perception. Usable signals: horizontal position change, scene change, target still visible, distance to target before/after, target taken by someone else.

### 7.3 F2: what `BaseAvatar` actually offers, and two gaps
- Present on `BaseAvatar` (`src/avatars/base_avatar.py`): `get_state_summary()`, `current_state` (property, `AvatarState`), `stress_level`, `emotional_state`, `cognitive_load`, `burnout_risk_level`, `assess_burnout_risk()`, `get_adhd_trait_impact(task_context)`.
- **Not on `BaseAvatar`:** the pair's current scenario or deficit. These live at the pair/session level.
- **Gap 1, binding.** The Fusion endpoint has no avatar registry. Nothing maps `perception.agentId` (e.g. `avatar_1`) to a `BaseAvatar` instance, and `build_decision_source()` creates no avatars. F2 needs an owner for "which avatars exist in this Fusion process and how they are bound by id". That edges toward `SessionOrchestrator`, which §4 puts out of scope. **Needs Joshua.**
- **Gap 2, the goal would never change.** `stress_level`, `emotional_state` and `cognitive_load` change only inside `attempt_task` / `receive_coaching`. Nothing in the world loop calls them, so a goal derived from avatar state would stay the same for the whole run unless world events feed back into the avatar.

### 7.4 §5.1 context: `wait` holds still by Joshua's decision
- `AvatarCharacter.ApplyIntent` holds the avatar still on `wait` with nothing under way. The comment records it as Joshua's decision of 2026-10-21: wandering on `wait` made a model-driven avatar look the same as one with no model. Option (a) in §5.1 partly revisits that decision, which is why it is Joshua's call.

### 7.5 F1 status
F1 is implemented in `src/fusion/agent_loop_memory.py` (`StatefulAgentLoopDecision`), with the outcome source recorded as `OUTCOME_SOURCE = "next_perception"`. The HTTP endpoint wraps its decision source in it (`FUSION_AGENT_LOOP_HISTORY`, default 8). Decisions are unchanged until F2/F3 use the history.

---

## 8. Joshua's decisions (2026-10-28) — these override §0–§7 where they differ

1. **Dead end (§5.1): narrow `wait`.** In the world engine, `wait` resumes the wander fallback **only when nothing is visible**. When something is visible, `wait` still holds still (the 2026-10-21 decision stands). No `explore` verb, no schema bump.
2. **Acceptance (§5.2): split T6 acceptance 4.**
   - **4a:** the engine and the loop behave correctly under a goal-driven Fusion source. The rule-based baseline (F4) may pass this.
   - **4b:** a model-driven run (Qwen, or the avatar's own RL model). Stays open until a model passes.
   - Do not mark T6 acceptance 4 met on 4a alone.
3. **New task F0 (before F1 and F2): agentId binding.** None existed.
   - Godot sent `agentId` `"__local_avatar__"` (hard-coded in `Main.cs`). Fusion avatars use roster ids like `"stay_alert_001"`. Nothing mapped one to the other.
   - Fusion creates and owns the Avatar/Aide pairs (`StayAlertAvatar` and its Aide, bound through `SessionOrchestrator`) and keeps an explicit `agentId` → pair registry.
   - An unknown `agentId` fails closed. Never create an avatar on the fly.
   - Godot sends the roster id as `agentId`, set by config (`NLT_AGENT_LOOP_AGENT_ID=stay_alert_001`). Only the perception's `agentId` changes; the internal `"__local_avatar__"` key stays.
   - First pair: StayAlert (the only fully implemented one).
   - F1 and F2 key their state by this registered `agentId`.

**Order:** F0 → F1 → F2 → F3 → F4 → F5. The engine-side `wait` change is a separate world-engine PR.

### 8.1 Status
- **F0, Fusion side:** `src/fusion/agent_loop_registry.py`. `build_default_registry()` creates the StayAlert pair from `src/avatars/avatar_configs/stay_alert.json` and `src/aides/aide_configs/stay_alert_aide.json` (`stay_alert_001` / `stay_alert_aide_001`), bound through `SessionOrchestrator`. The endpoint answers 404 with no intent for any other `agentId`, before the decision source is called.
- **F0, engine side and the `wait` change:** NeuroLift-Technologies/nlt-world-engine#117 (AgentHarness 151/151; not run in-engine).
- **F1:** implemented earlier on this branch (`src/fusion/agent_loop_memory.py`). It already keys by `agentId`; with F0, only registered ids reach it.
- **For F5:** in the 2026-10-22 run, after one `look_at plaza`, the wander fallback carried the avatar out of range of everything, and the next 33 decisions were `wait` with nothing visible. That is exactly the case decision 1 covers. What it does not cover (prediction, not measured): once something is back in view, a `wait` holds still again, so a model that keeps choosing `wait` with something in view can still stand still. F3's anti-repeat is the Fusion-side answer.

---

## 9. Headless run and Joshua's follow-up decisions (2026-10-28)

### 9.1 What the headless run showed
Godot 4.7.2 .NET, headless, in a Claude Code cloud session (no GPU), against `main` of both repos after #132 and nlt-world-engine#117. Frames render under Xvfb with Mesa llvmpipe (Compatibility renderer); screenshots from such runs are software-rendered.

| Check | Result |
|---|---|
| F0 roster id end to end | 57/57 perceptions sent as `stay_alert_001`, 57 × HTTP 200, 57 intents accepted |
| F0 unset id | startup warning; every perception refused (404, named correctly); decision source never called |
| `wait` with something visible | 0.0 m drift over 27 decisions |
| Rule-based fallback | `approach plaza` 42/42: the avatar spawns on the plaza, arrives at once, the wander fallback nudges it ~1 m, and the next approach pulls it back |
| Qwen3-0.6B Q8_0 (before F2) | `look_at` 11/11 (plaza, well, doors) |
| Qwen3-0.6B Q8_0 with F2 goal + history in the prompt | still `look_at` 11/11, over different targets |

### 9.2 Decisions (Joshua, 2026-10-28)
- **§5.1 is wrong for current `main`:** doors are in range from the spawn (`door_5_home`, `door_7_shop` in 19 of 42 perceptions, at the 25 m edge). Keep the narrowed-`wait` rule: the dead end still occurs after wandering out of range.
- **F3:** besides the no-change anti-repeat, also drop `approach X` when the avatar is already within X's arrival radius (use F1's recorded distance to the target).
- **F4:** the baseline is: approach a door, `use` it, then `sit` / `use` / `rest` inside. Verify acceptance 4a headless in the cloud session; tag software-rendered screenshots as such.
- **Open items (engine):** Godot hangs on shutdown after the stop signal (find out whether it is the agent-loop driver); rate-limit the missing-agent-id refusal warning, which repeats every 2 s.
- **Tooling:** add the headless run loop as a documented script (PID files, not `pkill` patterns), as a separate small PR.
- **Next:** F2.

### 9.3 F2 status
- `src/fusion/agent_loop_goals.py`: `derive_goal(avatar)` reads the registered Avatar's state without changing it and returns a short goal and one or two needs. Strain (stress ≥ 0.7, burnout risk ≥ 0.6, or a burnout/recovering state) → "recover after stress: find somewhere quiet to rest" (`rest`, `quiet`); cognitive load ≥ 0.7 → a short break (`rest`); otherwise the trait's goal. StayAlert: "start the task you have been putting off: get to your desk and sit down to work" (`focus`).
- `decision_context` adds the last 4 decisions as `{"did": "look_at plaza", "changed": false}`.
- Both local model adapters take an optional `context`; it is added to the prompt as `context`, and the system prompt says to serve the goal and not repeat an action that changed nothing. The endpoint gives the GGUF model the goal of the Avatar registered under each perception's `agentId`. The rule-based fallback is unchanged (F4 replaces it).
- Nothing new reaches Godot: intents still carry only a verb and a target.
- **Result:** with Qwen3-0.6B the context does not change the choice (§9.1). This is the outcome §6 predicted; F3's structural changes (ordering, anti-repeat, already-there) are the lever.
- **Gap 2 still holds:** the goal follows the Avatar's state, but nothing in the world loop updates that state yet, so in a world run the goal stays the StayAlert default.

## 10. F3: ranking and anti-repeat (2026-10-28)

### 10.1 What changed
- New `src/fusion/agent_loop_ranking.py`. `guide(observation, needs, history)` returns a `ChoiceGuidance`: entity ids ranked goal-relevant first, then nearest, then engine order; each entity's horizontal distance; which entities are goal-relevant; and the `(verb, target)` pairs the model may not output.
- **Relevance** matches words in entity ids against the F2 needs (`NEED_KEYWORDS`): `focus` → desk, office, study, whiteboard; `rest` → sofa, bed, home, shore; `quiet` → shore, home, bed. A door counts when its building serves the need (`door_6_office` for StayAlert).
- **Anti-repeat**, three rules:
  1. the last pair, when its outcome changed nothing (this brief, F3);
  2. `approach X` within the 1 m arrival radius (Joshua, §9.2). Measured from the current perception, which is fresher than F1's recorded distance;
  3. **`look_at X` once X was looked at since entering this scene, within the 8-decision history. This rule is not in the brief; it is an agent addition and needs Joshua's decision (§10.3).** Rule 1 cannot catch a look_at loop: the wander that follows every look always moves the agent, so every look "changed" something.
  - `wait` is never dropped. Rules 1 and 3 count only decisions made since the agent entered its current scene, so going through a door resets them; an engine restart clears the history (F1).
- `model_input` lists entities in ranked order with `distance` and `goalRelevant`; `grounded_choices` follows the ranking and leaves out excluded pairs, so the GGUF grammar cannot produce them. Both adapters take an optional `guidance`; `with_goal` supplies it. `SYSTEM_PROMPT` was later rewritten (§10.4).
- Unchanged: the rule-based fallback (F4 replaces it), the perception and intent schema, and what reaches Godot (verb and target only).

### 10.2 Measured (headless Godot 4.7.2 .NET, Claude Code cloud session, CPU only)
Same setup for each run: Fusion `main` plus the change named, Qwen3-0.6B Q8_0, `stay_alert_001`, 240 s, every exchange logged by a pass-through proxy. Every intent was accepted by the engine in every run.

| Fusion source | Decisions | Verb choices | p50 / p95 latency |
|---|---|---|---|
| Before F2 (`cb3ed63`) | 51 | `look_at` 51 | 3.24 / 4.94 s |
| F2 (`0eb0f5a`) | 41 | `look_at` 41 | 4.27 / 6.37 s |
| F3 rules 1 + 2 + ranking (rule 3 disabled for this run only) | 38 | `look_at` 38 | 4.81 / 6.30 s |
| **F3 as committed (rules 1–3 + ranking)** | 45 | `wait` 26, `look_at` 17, `approach door_6_office` 2 | 3.87 / 6.49 s |

- The ranking and rules 1–2 alone do not move Qwen off `look_at`.
- With rule 3, Qwen takes `wait` once everything in view has been looked at. With something in view, `wait` holds still (Joshua, 2026-10-21), so the avatar stands for several decisions. After about five waits, the old looks leave the 8-entry history and `look_at` is offered again.
- `door_6_office` was ranked first and marked `goalRelevant` throughout. Qwen chose `approach door_6_office` twice and never `use` on it. The goal action did not happen in 45 decisions. **4b is not met.**

### 10.3 Needs Joshua
1. **Keep rule 3?** It is the only F3 change that moved the model off `look_at`; it is beyond the brief's wording.
2. **`wait` as the new escape.** F3 drops repeats, and the model falls back to `wait`. Dropping `wait` while a goal-relevant targeted option exists would force a targeted choice. That changes what the model is allowed to say and would partly decide the action for it, so it is not done here.
3. **Whether the model or the input is the bottleneck** cannot be decided yet: F4 (the rule-based goal-driven baseline) is not started, so 4a has no result. Brief §4 says to choose a larger model only after F4 shows which one it is.

### 10.4 System prompt: name no verbs; trimmed model input (2026-10-28)
- **Offline, 20 real perceptions from the engine runs** (19 with a goal-relevant entity in view), F3 ranking and grammar, no history:

| Prompt and input | Qwen chose | Goal-directed |
|---|---|---|
| Previous prompt (names the verbs), full or trimmed input | `look_at` 20/20 | 0/20 |
| Step-by-step directive that names `look_at` ("only as a last resort"), full or trimmed | `look_at` 20/20 | 0/20 |
| Any prompt that names no verb (three wordings, full or trimmed input) | `use` on the goal-relevant door 19/20 | 19/20 |

  Naming the verbs is what primes `look_at`. Trimming coordinates does not change the choice; it halves decision time (about 2.2 s to 1.1 s).
- **Committed:** `SYSTEM_PROMPT` names no verb (the output grammar still offers every verb), and with F3 guidance the model input leaves out coordinates and velocity.
- **In-engine (240 s, same setup as §10.2): `use well` 67, `use plaza` 22, p50 1.76 s / p95 3.25 s.** From the spawn only `plaza` and `well` are in range, nothing goal-relevant ever came into view, and Qwen takes the first-listed entity, so `use` kept the avatar shuttling between well and plaza. The office door was never perceived. Under the previous prompt, `look_at` handed the avatar to the wander fallback, which carried it into door range: the `look_at` loop was the avatar's only exploration.
- **Reading:** the model is following list order, not reasoning about the goal: it acts on the first entity it is shown. F3's ranking makes that useful when a goal-relevant entity is visible; it cannot help when none is. Offline sampling from wandering runs missed the spawn case.
- **Needs Joshua:**
  1. Keep the new prompt? It is faster and goal-directed when the goal is in view, and it stalls the avatar at the spawn when the goal is not.
  2. How the agent explores when nothing goal-relevant is in view. Fusion has no verb for it (no `explore` verb, §8 decision 1). Options: in Fusion, offer only non-holding choices (`look_at`, `approach`) when nothing goal-relevant is visible, so the engine's wander resumes; or in the engine, a spawn or perception range that keeps a goal-relevant door in view (§5.1 option b).
  3. F4 faces the same question: its baseline starts with "approach a door", and from the spawn no office door is in range.
