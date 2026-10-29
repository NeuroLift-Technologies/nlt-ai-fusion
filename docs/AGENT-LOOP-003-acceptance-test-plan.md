# AGENT-LOOP-003 — Model-Driven Acceptance Test Plan

**Repository:** `NeuroLift-Technologies/neurolift-ai-fusion`  
**Branch:** `kilo/agent-loop-003-acceptance-tests`  
**Thread:** TH-028 (AGENT-LOOP-003)  
**Status:** proposed (tests written, not yet run — see Blocker below)

## Scope and constraints

- Tests are isolated, faked unit tests: no real GGUF/Transformers model, no Godot runtime, no network.
- No production decision logic, prompts, ranking policy, Godot behavior, governance rules, or the agent-loop contract (`nlt.agent-loop.v1`) was modified.
- New file: `tests/test_fusion/test_agent_loop_acceptance.py`. No production files changed.
- Tests that need a live model or Godot runtime are listed as live-only and are **not** substituted with mocks and called end-to-end.

## Coverage map (8 required areas)

| # | Acceptance area | Covered by | Status |
|---|-----------------|------------|--------|
| A | Repeated identical actions without measurable progress | `test_agent_loop_acceptance.py` + `test_agent_loop_ranking.py` | new + existing |
| B | Goals not represented in the current perception | `test_agent_loop_acceptance.py` | new |
| C | Goals visible but not reachable | `test_agent_loop_acceptance.py` | new |
| D | Action ranking and repeated/completed-action filtering | `test_agent_loop_ranking.py` | existing |
| E | Context: Avatar identity, goals, needs, recent outcomes | `test_agent_loop_goals.py` + `test_agent_loop_acceptance.py` | existing + new |
| F | Inference timeout, unavailable model, malformed output | `test_agent_loop_acceptance.py` + `test_gguf_agent_decision.py` | new + existing |
| G | Governance rejection vs model/service failure | `test_agent_loop_http.py` | existing |
| H | Regression protection for the working F4 baseline | `test_agent_loop_baseline.py` + `test_agent_loop_acceptance.py` | existing + new |

Existing suites already pin D, E, G and most of H; the new file adds A, B, C, F and two H regression pins.

---

## Test plan details

### A. Repeated identical actions without measurable progress

| | |
|---|---|
| **Test** | `test_repeated_unchanged_pair_is_excluded_from_grammar_on_next_decision` |
| **Setup** | StayAlert registry; perception with `well` (6 m) visible, agent at `x=-5`; fake model returns `use well` then `wait`. |
| **Stimulus** | First decision → `use well`. Second perception: avatar did not move (same position), `well` still visible → outcome `changed=False`. |
| **Expected behavior** | `("use","well")` is dropped by F3 rule 1 and absent from the grammar offered on the second call; the intent is `wait`, not the repeat. |
| **Pass/fail** | Pass: intent2 verb == `wait` and `("use","well") not in fake.offered`. Fail: repeat offered or repeated. |
| **Layer responsible** | F3 ranking/anti-repeat (`agent_loop_ranking.excluded_pairs`); F1 memory supplies the outcome. |

| | |
|---|---|
| **Test** | `test_model_cannot_stall_forever_on_a_repeated_noop` |
| **Setup** | Same as above; fake model insists on `use well` three times then `wait`. |
| **Stimulus** | Four sequential decisions, each with `changed=False` (no movement). |
| **Expected behavior** | First decision may be `use well`; decisions 2–4 must not repeat `("use","well")`; final decision is `wait`. |
| **Pass/fail** | Pass: `intents[0]==("use","well")` and no later intent repeats it and last is `wait`. Fail: endless repetition (the spawn-loop failure mode). |
| **Layer responsible** | F1 memory + F3 anti-repeat. |

Existing rule-1 coverage: `test_agent_loop_ranking.py::test_last_pair_that_changed_nothing_is_dropped`, `test_only_the_last_unchanged_pair_is_dropped`, `test_staying_seated_at_a_goal_relevant_chair_is_not_dropped`, `test_an_unchanged_door_use_at_the_door_is_still_dropped`.

---

### B. Goals not represented in the current perception

| | |
|---|---|
| **Test** | `test_goal_relevant_entity_absent_from_perception_is_not_invented` |
| **Setup** | Spawn perception: only `plaza` (0.5 m) and `well` (6 m) visible; goal needs `focus` (desk/office/study/whiteboard). |
| **Stimulus** | `guide(perception, needs=("focus",), history=())`. |
| **Expected behavior** | `goal_relevant` is empty; no goal door is in `order`; first option is exploration within view (`approach well`), not a hallucinated goal target. |
| **Pass/fail** | Pass: `goal_relevant == frozenset()` and `options[0] == ("approach","well")`. Fail: a goal-relevant door is offered/invented. |
| **Layer responsible** | F3 ranking (`guide`) + F2 context (`derive_goal` needs). |

| | |
|---|---|
| **Test** | `test_model_input_marks_no_entity_goal_relevant_when_goal_is_out_of_view` |
| **Setup** | Same spawn perception. |
| **Stimulus** | `model_input(observation, guidance=guidance)`. |
| **Expected behavior** | No visible entity is marked `goalRelevant: true`; `options` ends with `wait`. |
| **Pass/fail** | Pass: all `goalRelevant` are false; an option has `verb == "wait"`. Fail: an out-of-view goal entity is marked relevant. |
| **Layer responsible** | F3 ranking + `model_input` (agent_loop_choices). |

---

### C. Goals visible but not reachable

| | |
|---|---|
| **Test** | `test_occupied_goal_target_is_not_offered_for_occupying_verbs` |
| **Setup** | `door_6_office` (20 m) visible, `occupied=True`, affords `use/approach/look_at`; goal needs `focus` (door is goal-relevant). |
| **Stimulus** | `grounded_choices(observation, guidance)`. |
| **Expected behavior** | Occupancy trumps relevance: the door is not offered for `use`/`sit`/`rest`; `look_at` and `approach` (outside the 1 m radius) remain allowed. |
| **Pass/fail** | Pass: door absent from `use`/`sit`/`rest` choices, present in `look_at`/`approach`. Fail: an occupied goal target is offered for an occupying verb (repeated failed use). |
| **Layer responsible** | Grounded choices / occupancy (`agent_loop_choices.grounded_choices`); exclusion via `excluded_pairs`. |

| | |
|---|---|
| **Test** | `test_baseline_waits_when_goal_target_is_occupied_and_unaffordable` |
| **Setup** | Only entity: `door_6_office` (0.5 m), `occupied=True`, affords `use/sit/rest` only (no look_at/approach). |
| **Stimulus** | F4 baseline `goal_baseline(registry)`. |
| **Expected behavior** | No pair is allowed (occupied blocks occupying verbs; within radius blocks approach; no look_at affordance) → `wait`. |
| **Pass/fail** | Pass: `verb == "wait"` and no `targetId`. Fail: baseline tries an occupying verb on an occupied target. |
| **Layer responsible** | F4 baseline + F3 exclusions + grounded choices. |

---

### D. Action ranking and repeated/completed-action filtering

Pinned by existing `tests/test_fusion/test_agent_loop_ranking.py`:
- `test_entities_rank_goal_relevant_first_then_nearest`
- `test_a_goal_relevant_target_comes_before_any_unvisited_one` (`options[0] == ("use","door_1_office")`)
- `test_inside_the_office_sitting_at_the_desk_comes_first`
- `test_a_need_for_rest_puts_rest_first`
- `test_last_pair_that_changed_nothing_is_dropped` (rule 1)
- `test_approach_is_dropped_within_the_arrival_radius` (rule 2)
- `test_looking_again_at_something_already_looked_at_is_dropped` (rule 3)
- `test_a_new_scene_resets_anti_repeat`
- `test_wait_stays_allowed_when_every_pair_is_dropped`
- `test_options_are_exactly_the_allowed_pairs_and_each_parses`
- `test_input_and_grammar_offer_the_ranked_options_with_wait_last`

Representative new pin: `test_agent_loop_acceptance.py::test_options_ordered_goal_relevant_first_unvisited_then_look_at_wait_last` (asserts `options[0] == ("use","door_1_office")`, non-wait options before wait, `options[-1] == ("wait", None)`).

| | |
|---|---|
| **Layer responsible** | F3 ranking (`agent_loop_ranking.guide`/`rank_options`/`excluded_pairs`). |
| **Measurable criterion** | Options are a permutation of exactly the allowed pairs; `wait` last; goal-relevant acting pairs first; `look_at` on already-looked entities dropped; `approach` within 1 m dropped. |

---

### E. Context: Avatar identity, goals, needs, recent outcomes

| | |
|---|---|
| **Test** | `test_context_contains_goal_needs_and_what_changed_after_each_decision` |
| **Setup** | History of 3 decisions with mixed `changed` outcomes across scenes. |
| **Stimulus** | `decision_context(AgentGoal("g",("focus",)), history)`. |
| **Expected behavior** | `context` carries `goal`, `needs`, and `recent` list of `{"did","changed"}` entries, newest last, capped at `RECENT_WINDOW` (4). |
| **Pass/fail** | Pass: `recent` equals the expected list of did/changed dicts. Fail: missing goal/needs/recent or wrong changed flags. |
| **Layer responsible** | F2 goals (`agent_loop_goals.decision_context`); F1 memory supplies records. |

| | |
|---|---|
| **Test** | `test_context_flows_into_model_prompt_but_not_into_engine_intent` |
| **Setup** | `with_goal(model, registry)` + fake model; endpoint perception. |
| **Stimulus** | Two decisions. |
| **Expected behavior** | Model prompt `context` contains the avatar's goal ("start the task you have been putting off…"), needs `["focus"]`, and recent decisions; the correlated intent sent to the engine carries only verb + target (no `context`/`goal`/`needs`/`recent`). |
| **Pass/fail** | Pass: prompt context populated; intent keys exactly `{protocolVersion,messageType,messageId,agentId,observedTick,verb}`. Fail: context leaks into the engine intent. |
| **Layer responsible** | F2 (`with_goal`/`decision_context`); contract seam (`FusionAgentLoop.handle_observation`/`validate_intent`). |

Existing: `test_agent_loop_goals.py::test_gguf_prompt_carries_the_registered_avatars_goal_and_history`, `test_goal_follows_the_avatars_state_between_decisions`, `test_endpoint_sends_only_verb_and_target_to_the_engine`, `test_unregistered_agent_has_no_goal`.

---

### F. Inference timeout, unavailable model, malformed output

| | |
|---|---|
| **Test** | `test_unavailable_model_file_raises_at_construction` |
| **Setup** | `LlamaCppAgentLoopDecision("/nonexistent/model.gguf")`. |
| **Stimulus** | Construct the adapter. |
| **Expected behavior** | `FileNotFoundError` raised at construction; no silent fallback intent. |
| **Pass/fail** | Pass: `FileNotFoundError` (match "does not exist"). Fail: adapter constructed or fallback substituted. |
| **Layer responsible** | Model adapter (`gguf_agent_decision.LlamaCppAgentLoopDecision.__init__`). |

| | |
|---|---|
| **Test** | `test_malformed_or_ungrounded_model_output_is_rejected` (parametrized) |
| **Setup** | Perception with `desk_1` visible; fake model returns malformed/ungrounded content (`not json`, `teleport`, target `hidden_entity`, `wait` with targetId, extra `position` field). |
| **Stimulus** | `adapter(observation)`. |
| **Expected behavior** | `GgufAgentLoopModelOutputError` raised before any intent leaves Fusion. |
| **Pass/fail** | Pass: exception raised for every case. Fail: a malformed intent is returned. |
| **Layer responsible** | Model adapter `parse_decision` + `FusionAgentLoop.validate_intent` seam. Existing: `test_gguf_agent_decision.py::test_gguf_adapter_rejects_malformed_or_ungrounded_output`. |

| | |
|---|---|
| **Test** | `test_decision_source_exception_is_fail_closed_by_http_endpoint` |
| **Setup** | HTTP endpoint with a decide that raises `RuntimeError("cuda out of memory")`. |
| **Stimulus** | POST `/agent-loop/perception`. |
| **Expected behavior** | HTTP 503 `decision source unavailable`, no intent, exception text not leaked. |
| **Pass/fail** | Pass: status 503, error message match, no leak. Fail: intent returned or internals leaked. |
| **Layer responsible** | HTTP transport boundary (`agent_loop_http`). Distinct from governance rejection (G). |

| | |
|---|---|
| **Test** | `test_protocol_violating_intent_from_source_is_422_not_503` |
| **Setup** | Decide returns a stale `observedTick`. |
| **Stimulus** | POST `/agent-loop/perception`. |
| **Expected behavior** | HTTP 422 `decision did not satisfy the agent-loop contract` (contract violation), not 503. |
| **Pass/fail** | Pass: 422 with contract error. Fail: 503 or intent accepted. |
| **Layer responsible** | FusionAgentLoop seam validation (`validate_intent`). |

**Inference timeout (live):** The Fusion boundary fails closed on exceptions but does not enforce a wall-clock inference timeout. A hanging llama.cpp process (the 4–5 s / 120–400 s Qwen behavior in brief §6/§9) is only observable with a live model + Godot. **Flagged live-only; not a mocked end-to-end test.** See section "Live-model / Godot tests".

---

### G. Governance rejection vs model/service failure

Pinned by existing `tests/test_fusion/test_agent_loop_http.py`:
- `test_unregistered_agent_fails_closed_before_any_decision` — unknown `agentId` → HTTP 404 `agent is not registered`, decision source never called (governance rejection, F0 fail-closed).
- `test_decision_source_error_fails_closed` — source raises → HTTP 503 `decision source unavailable` (service failure).
- `test_stale_or_mismatched_intent_rejected_by_seam` / `test_target_outside_perception_rejected_by_seam` — contract violation → 422.

| | |
|---|---|
| **Distinction** | 404 unknown agent = governance rejection (F0 registry, fail closed before decide). 503 source exception = model/service failure. 422 bad intent = contract violation. |
| **Layer responsible** | F0 registry (`agent_loop_registry`); HTTP transport (`agent_loop_http`). |

---

### H. Regression protection for the working F4 baseline

Pinned by existing `tests/test_fusion/test_agent_loop_baseline.py`:
- `test_goes_through_the_goal_relevant_door_when_it_is_in_view` → `("use","door_6_office")`
- `test_explores_unvisited_targets_when_the_goal_is_not_in_view`
- `test_sits_at_the_desk_inside_the_office`
- `test_waits_when_nothing_is_in_view`
- `test_intent_carries_only_verb_and_target`
- `test_stays_seated_across_decisions_once_at_the_desk`
- `test_waits_when_every_pair_is_excluded_or_occupied`

New pins in `test_agent_loop_acceptance.py`:
- `test_baseline_regression_goes_to_the_goal_door_when_in_view`
- `test_baseline_regression_stays_seated_without_oscillation` — 6 decisions, always `("sit","desk_chair_1")` (pins the no-oscillation fix for acceptance 4a).
- `test_baseline_regression_waits_when_nothing_in_view`

| | |
|---|---|
| **Expected behavior (4a)** | Baseline approaches a door, `use`s it, transits inside, `sit`s at a desk and stays seated with no oscillation; waits when nothing is in view. |
| **Pass/fail** | Pass: all baseline assertions hold. Fail: any regression in the deterministic goal-driven control. |
| **Layer responsible** | F4 baseline (`agent_loop_baseline.goal_baseline`) + F3 ranking (`guide`/`rank_options`). |

---

## Commands executed / results

No tests were executed: Python is not installed in this sandbox (`python`/`python3` not found), so `pytest` cannot run here.

Planned commands (to run in an environment with Python 3.11 + the repo's dependencies):

```bash
# From /workspace/app
pytest tests/test_fusion/test_agent_loop_acceptance.py -q
pytest tests/test_fusion/ -q                    # full fusion suite (regression)
pytest tests/test_fusion/test_agent_loop_baseline.py tests/test_fusion/test_agent_loop_ranking.py -q  # F4 + F3 regression
```

Coverage gate used by CI: `pytest --cov=src --cov-report=term-missing --cov-fail-under=40` (40% gate; see `pytest.ini`). New tests are additive and do not reduce coverage.

---

## Live-model / Godot tests (flagged, not run as end-to-end)

The following are **not** implemented as mocked end-to-end tests and require the stated runtime:

1. **Live Qwen3-0.6B GGUF smoke test** — `tests/test_fusion/test_agent_loop_acceptance.py::test_local_qwen_gguf_smoke_skips_without_model` (skipped unless `NLT_AGENT_LOOP_GGUF_PATH` set; requires `llama-cpp-python` and a real GGUF file). Exercises the real model through `FusionAgentLoop`.
2. **F5 in-engine run** (brief §11.4 / §9): baseline source vs Qwen source on the same scenario, headless Godot 4.7.2 .NET, 240–300 s; pass criteria: avatar goes through a door with `use`, moves inside, performs `sit`/`use`/`rest` on furniture, no stalls; log verb counts, distinct targets, stalls per source. Requires Godot runtime, the world engine, Qwen weights, and GPU/RAM headroom (brief §5).
3. **Inference timeout** — a hanging model process is only observable live; not enforced at the Fusion boundary.

These are acceptance evidence, not a substitute for the mocked unit tests above.

---

## Deliverables

- `tests/test_fusion/test_agent_loop_acceptance.py` — new isolated acceptance tests (A, B, C, F, H pins).
- `docs/AGENT-LOOP-003-acceptance-test-plan.md` — this plan.

No production files were modified. Branch: `kilo/agent-loop-003-acceptance-tests` (working tree clean except the new test file and this doc).

---

## Blocker

Python interpreter and `pytest` are not installed in this sandbox, so the new and existing tests could not be executed. Results (pass/fail, durations) are pending execution in an environment with Python 3.11 and the repo's Python dependencies (`src/` importable, `fastapi`/`starlette` for `TestClient`).
