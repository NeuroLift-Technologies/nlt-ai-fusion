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
