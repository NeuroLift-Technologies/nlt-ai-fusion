"""AGENT-LOOP-003 acceptance tests for the model-driven agent loop.

Isolated unit tests with fakes: no real GGUF/Transformers model, no Godot runtime, no network.
Each test pins one acceptance behavior and names the layer responsible if it fails.

See docs/AGENT-LOOP-003-acceptance-test-plan.md for the full plan (setup, stimulus, expected
behavior, measurable pass/fail criteria, responsible layer) mapped to each test below.

Coverage map:
  A. Repeated identical actions without measurable progress  -> test_*_stall* / anti-repeat
  B. Goals not represented in the current perception          -> test_*_goal_absent*
  C. Goals visible but not reachable                          -> test_*_occupied_unreachable*
  D. Action ranking and repeated/completed-action filtering   -> (existing test_agent_loop_ranking.py)
  E. Context carries identity, goals, needs, recent outcomes  -> (existing test_agent_loop_goals.py)
  F. Inference timeout, unavailable model, malformed output   -> test_*_model_* / malformed
  G. Governance rejection vs model/service failure            -> (existing test_agent_loop_http.py)
  H. Regression protection for the working F4 baseline        -> test_*_baseline_* + existing suite

Tests that need a live model or Godot runtime are documented in the plan, not substituted
with mocks and called end-to-end.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from src.fusion import PROTOCOL_VERSION
from src.fusion.agent_loop import FusionAgentLoop
from src.fusion.agent_loop_baseline import goal_baseline
from src.fusion.agent_loop_choices import (
    grounded_choices,
    model_input,
)
from src.fusion.agent_loop_goals import AgentGoal, decision_context, with_goal
from src.fusion.agent_loop_http import create_app
from src.fusion.agent_loop_memory import (
    DecisionOutcome,
    DecisionRecord,
    StatefulAgentLoopDecision,
)
from src.fusion.agent_loop_ranking import (
    guide,
)
from src.fusion.agent_loop_registry import build_default_registry
from src.fusion.gguf_agent_decision import (
    GgufAgentLoopModelOutputError,
    LlamaCppAgentLoopDecision,
)

AGENT_ID = "stay_alert_001"


def entity(entity_id, x, z=0.0, affordances=("approach", "use", "look_at"), occupied=False):
    return {
        "id": entity_id,
        "kind": "place",
        "position": {"x": x, "y": 0.0, "z": z},
        "affordances": list(affordances),
        "occupied": occupied,
    }


# A goal-relevant target kept in view by the rule-1 and rule-3 tests, so they test the
# anti-repeat rules with a goal in view rather than explore ranking.
OFFICE_DOOR = entity("door_6_office", 20.0)


def perception(entities, tick=1, x=0.0, z=0.0, scene="open_world", agent_id=AGENT_ID):
    return {
        "protocolVersion": PROTOCOL_VERSION,
        "messageType": "perception",
        "messageId": f"obs-{tick}-{agent_id}",
        "agentId": agent_id,
        "tick": tick,
        "scene": {"id": scene, "kind": "open_world" if scene == "open_world" else "interior"},
        "self": {
            "position": {"x": x, "y": 0.0, "z": z},
            "velocity": {"x": 0.0, "y": 0.0, "z": 0.0},
        },
        "visibleEntities": entities,
    }


def record(verb, target=None, changed=False, tick=1, scene="open_world"):
    return DecisionRecord(
        tick=tick,
        scene_id=scene,
        verb=verb,
        target_id=target,
        outcome=DecisionOutcome(
            ticks_elapsed=1,
            moved_distance=1.0 if changed else 0.0,
            scene_changed=False,
            target_visible=None if target is None else True,
            target_distance_before=None,
            target_distance_after=None,
            target_taken=False,
        ),
    )


class SequenceFakeLlama:
    """Returns a different content per call and records the grammar offered each time."""

    def __init__(self, contents):
        self._contents = list(contents)
        self.calls = []

    def create_chat_completion(self, **kwargs):
        self.calls.append(kwargs)
        index = len(self.calls) - 1
        content = self._contents[index] if index < len(self._contents) else '{"verb":"wait"}'
        return {"choices": [{"message": {"content": content}}]}

    @property
    def offered(self):
        """(verb, target) pairs the grammar offers on the last call, in order."""
        pairs = []
        for schema in self.calls[-1]["response_format"]["schema"]["oneOf"]:
            target = schema["properties"].get("targetId", {})
            pairs.append((schema["properties"]["verb"]["const"], target.get("const")))
        return pairs


def model_with(registry, contents):
    fake = SequenceFakeLlama(contents)
    model = LlamaCppAgentLoopDecision("unused.gguf", model=fake)
    decide = StatefulAgentLoopDecision(with_goal(model, registry))
    return decide, fake


# ---------------------------------------------------------------------------
# A. Repeated identical actions without measurable progress (F1 + F3)
# ---------------------------------------------------------------------------


def test_repeated_unchanged_pair_is_excluded_from_grammar_on_next_decision():
    """A (verb, target) that changed nothing must not be offered again (F3 rule 1).

    Layer: F3 ranking/anti-repeat (agent_loop_ranking.excluded_pairs).
    """
    registry = build_default_registry()
    decide, fake = model_with(
        registry,
        ['{"verb":"use","targetId":"well"}', '{"verb":"wait"}'],
    )
    obs1 = perception(
        [entity("well", 6.0, affordances=("approach", "use", "look_at")), OFFICE_DOOR],
        tick=1,
        x=-5.0,
    )
    intent1 = decide(obs1)
    assert (intent1["verb"], intent1["targetId"]) == ("use", "well")

    # obs2: the avatar did not move, so "use well" changed nothing and must be dropped.
    obs2 = perception(
        [entity("well", 6.0, affordances=("approach", "use", "look_at")), OFFICE_DOOR],
        tick=2,
        x=-5.0,
    )
    intent2 = decide(obs2)
    assert intent2["verb"] == "wait"
    assert ("use", "well") not in fake.offered


def test_last_unchanged_pair_is_excluded_on_the_next_decision():
    """Rule 1 drops only the last unchanged (verb, target) on the next decision.

    The source answers `use well` once; with no movement the outcome is unchanged,
    so `("use","well")` is excluded from the grammar on the following decision and
    the intent falls back to `wait`. This test passes because the fake cooperatively
    answers `wait`; once the pair is no longer the last decision it is re-offered
    (rule 1 only drops the last pair), demoted — see the alternation test below.

    Layer: F1 memory (outcome from next perception) + F3 anti-repeat rule 1.
    """
    registry = build_default_registry()
    decide, fake = model_with(
        registry,
        [
            '{"verb":"use","targetId":"well"}',
            '{"verb":"wait"}',
        ],
    )
    obs1 = perception(
        [entity("well", 6.0, affordances=("approach", "use", "look_at")), OFFICE_DOOR],
        tick=1,
        x=-5.0,
    )
    intent1 = decide(obs1)
    assert (intent1["verb"], intent1.get("targetId")) == ("use", "well")

    obs2 = perception(
        [entity("well", 6.0, affordances=("approach", "use", "look_at")), OFFICE_DOOR],
        tick=2,
        x=-5.0,
    )
    intent2 = decide(obs2)
    assert intent2["verb"] == "wait"
    assert ("use", "well") not in fake.offered


def test_an_unchanged_pair_is_demoted_below_pairs_not_yet_chosen():
    """Alternating use well / use plaza with no movement (the #135 engine loop) is broken up by
    ranking, not by exclusion: once chosen in this scene, `use well` ranks below every pair in
    its group not yet chosen and below every approach, but stays allowed (Josh, 2026-10-28:
    "demote them; never forbid them").

    Layer: F3 ranking (tier 3 novelty demotion).
    """
    registry = build_default_registry()
    decide, fake = model_with(
        registry,
        [
            '{"verb":"use","targetId":"well"}',
            '{"verb":"use","targetId":"plaza"}',
            '{"verb":"use","targetId":"well"}',
        ],
    )
    # All three within the hold radius, so standing still is not a blocked target either.
    base = perception(
        [entity("well", 1.2), entity("plaza", -1.2), entity("bench", 0.0, z=1.4), OFFICE_DOOR],
        tick=1,
        x=0.0,
    )
    intents = [decide({**base, "tick": tick}) for tick in range(1, 4)]

    verbs = [(i["verb"], i.get("targetId")) for i in intents]
    assert verbs == [("use", "well"), ("use", "plaza"), ("use", "well")]
    offered = fake.offered
    assert ("use", "plaza") not in offered  # rule 1: the last pair, unchanged
    assert offered.index(("use", "bench")) < offered.index(("use", "well"))
    assert all(
        offered.index(pair) < offered.index(("use", "well"))
        for pair in offered
        if pair[0] == "approach"
    )


# ---------------------------------------------------------------------------
# B. Goals not represented in the current perception (F2 + F3)
# ---------------------------------------------------------------------------


def test_goal_relevant_entity_absent_from_perception_is_not_invented():
    """When nothing in view serves the goal (spawn: only plaza/well, goal is focus),
    no entity is marked goalRelevant and the model is not handed a goal door it cannot see.

    Layer: F3 ranking (guide) + F2 context (goal/needs).
    """
    guidance = guide(perception([entity("plaza", 0.5), entity("well", 6.0)]), ("focus",), ())
    assert guidance.goal_relevant == frozenset()
    assert "door_1_office" not in guidance.order
    # The first option is exploration within view, not a hallucinated goal target.
    assert guidance.options[0] == ("approach", "well")


def test_model_input_marks_no_entity_goal_relevant_when_goal_is_out_of_view():
    obs = perception([entity("plaza", 0.5), entity("well", 6.0)])
    guidance = guide(obs, ("focus",), ())
    message = model_input(obs, guidance=guidance)
    assert all(not e["goalRelevant"] for e in message["visibleEntities"])
    assert any(o["verb"] == "wait" for o in message["options"])


# ---------------------------------------------------------------------------
# C. Goals visible but not reachable (occupied / blocked)
# ---------------------------------------------------------------------------


def test_occupied_goal_target_is_not_offered_for_occupying_verbs():
    """An occupied goal door must not be offered for use/sit/rest even though it serves
    the goal and is visible. Reachability (occupancy) trumps relevance.

    Layer: grounded choices / occupancy (agent_loop_choices.grounded_choices).
    """
    obs = perception(
        [entity("door_6_office", 20.0, affordances=("use", "approach", "look_at"), occupied=True)],
        tick=1,
    )
    guidance = guide(obs, ("focus",), ())
    choices = grounded_choices(obs, guidance)
    assert "door_6_office" not in choices.get("use", [])
    assert "door_6_office" not in choices.get("sit", [])
    assert "door_6_office" not in choices.get("rest", [])
    # Looking and approaching (outside the arrival radius) remain allowed.
    assert "door_6_office" in choices.get("look_at", [])
    assert "door_6_office" in choices.get("approach", [])


def test_baseline_waits_when_goal_target_is_occupied_and_unaffordable():
    decide = StatefulAgentLoopDecision(goal_baseline(build_default_registry()))
    obs = perception(
        [entity("door_6_office", 0.5, affordances=("use", "sit", "rest"), occupied=True)],
        tick=1,
    )
    intent = decide(obs)
    assert intent["verb"] == "wait" and "targetId" not in intent


# ---------------------------------------------------------------------------
# D. Action ranking and repeated/completed-action filtering
# ---------------------------------------------------------------------------


def test_options_ordered_goal_relevant_first_unvisited_then_look_at_wait_last():
    obs = perception(
        [entity("well", 6.0), entity("door_1_office", 20.0), entity("plaza", 0.5)],
        tick=1,
    )
    guidance = guide(obs, ("focus",), ())
    options = guidance.options
    assert options[0] == ("use", "door_1_office")
    # `wait` is appended by model_input, not part of guidance.options.
    assert all(verb != "wait" for verb, _ in options)
    message = model_input(obs, guidance=guidance)
    assert message["options"][-1] == {"verb": "wait"}


def test_looked_at_entity_is_not_offered_for_look_again_this_scene():
    obs = perception(
        [entity("plaza", 0.5), entity("well", 6.0), OFFICE_DOOR], tick=1, x=-5.0
    )
    history = (record("look_at", "plaza", changed=True, tick=1),)
    choices = grounded_choices(obs, guide(obs, ("focus",), history))
    assert "plaza" not in choices.get("look_at", [])
    assert "well" in choices.get("look_at", [])


# ---------------------------------------------------------------------------
# E. Context carries identity, goals, needs, recent outcomes (referenced)
# ---------------------------------------------------------------------------


def test_context_contains_goal_needs_and_what_changed_after_each_decision():
    history = [
        record("approach", "well", changed=True, tick=1),
        record("use", "door_1_office", changed=False, tick=2),
        record("sit", "desk_chair_1", changed=True, tick=3, scene="office_1"),
    ]
    context = decision_context(AgentGoal("g", ("focus",)), history)
    assert context["goal"] == "g"
    assert context["needs"] == ["focus"]
    assert context["recent"] == [
        {"did": "approach well", "changed": True},
        {"did": "use door_1_office", "changed": False},
        {"did": "sit desk_chair_1", "changed": True},
    ]


def test_context_flows_into_model_prompt_but_not_into_engine_intent():
    registry = build_default_registry()
    decide, fake = model_with(registry, ['{"verb":"wait"}'])
    obs = perception([], tick=1)
    decide(obs)
    message = json.loads(fake.calls[0]["messages"][1]["content"])
    assert message["context"]["goal"].startswith("start the task you have been putting off")
    assert message["context"]["needs"] == ["focus"]
    assert isinstance(message["context"]["recent"], list)

    # The correlated intent the engine receives carries only verb + target.
    intent = decide(obs)
    assert not {"context", "goal", "needs", "recent"} & set(intent)
    assert set(intent) == {
        "protocolVersion",
        "messageType",
        "messageId",
        "agentId",
        "observedTick",
        "verb",
    }


# ---------------------------------------------------------------------------
# F. Inference timeout, unavailable model, malformed output
# ---------------------------------------------------------------------------


def test_unavailable_model_file_raises_at_construction():
    """A missing GGUF model fails fast at adapter construction; it is not silently
    substituted by a fallback intent.

    Layer: model adapter (gguf_agent_decision.LlamaCppAgentLoopDecision).
    """
    with pytest.raises(FileNotFoundError, match="does not exist"):
        LlamaCppAgentLoopDecision("/nonexistent/model.gguf")


@pytest.mark.parametrize(
    "content",
    [
        "not json",
        '{"verb":"teleport"}',
        '{"verb":"approach","targetId":"hidden_entity"}',
        '{"verb":"wait","targetId":"desk_1"}',
        '{"verb":"use","targetId":"desk_1","position":{"x":9}}',
    ],
)
def test_malformed_or_ungrounded_model_output_is_rejected(content):
    """Malformed model output is rejected before any intent reaches the engine.

    Layer: model adapter parse + FusionAgentLoop seam validation.
    """
    obs = perception([entity("desk_1", 2.0, affordances=("use", "sit"))], tick=1)
    adapter = LlamaCppAgentLoopDecision("unused.gguf", model=FakeLlama(content))
    with pytest.raises(GgufAgentLoopModelOutputError):
        adapter(obs)


class FakeLlama:
    def __init__(self, content='{"verb":"wait"}'):
        self.content = content
        self.calls = []

    def create_chat_completion(self, **kwargs):
        self.calls.append(kwargs)
        return {"choices": [{"message": {"content": self.content}}]}


def test_decision_source_exception_is_fail_closed_by_http_endpoint():
    """A decision source that raises (e.g. model crashed / inference timed out and
    surfaced as an exception) yields 503 with no intent and no leaked internals.

    Layer: HTTP transport boundary (agent_loop_http).
    Real inference timeout (a hanging model process) requires a live model and is
    not enforced at this boundary; it is flagged in the plan.

    Responsible layer on failure: HTTP transport (service failure), distinct from
    governance rejection (404, tested in test_agent_loop_http.py).
    """

    def exploding(observation):
        raise RuntimeError("cuda out of memory")

    client = TestClient(create_app(decide=exploding))
    response = client.post("/agent-loop/perception", json=perception([], tick=1))
    assert response.status_code == 503
    assert response.json()["error"] == "decision source unavailable"
    assert "cuda out of memory" not in response.text


def test_protocol_violating_intent_from_source_is_422_not_503():
    """A source that returns a contract-violating intent (stale tick, hidden target)
    is a 422 contract failure, not a 503 service failure.

    Layer: FusionAgentLoop seam validation (agent_loop.validate_intent).
    """

    def stale_decide(observation):
        intent = {
            "protocolVersion": PROTOCOL_VERSION,
            "messageType": "intent",
            "messageId": "intent-1",
            "agentId": observation["agentId"],
            "observedTick": observation["tick"] - 7,
            "verb": "wait",
        }
        return intent

    client = TestClient(create_app(decide=stale_decide))
    response = client.post("/agent-loop/perception", json=perception([], tick=42))
    assert response.status_code == 422
    assert response.json()["error"] == "decision did not satisfy the agent-loop contract"


# ---------------------------------------------------------------------------
# H. Regression protection for the working F4 baseline
# ---------------------------------------------------------------------------


def test_baseline_regression_goes_to_the_goal_door_when_in_view():
    decide = StatefulAgentLoopDecision(goal_baseline(build_default_registry()))
    obs = perception([entity("plaza", 0.5), entity("door_6_office", 20.0)], tick=1)
    intent = decide(obs)
    assert (intent["verb"], intent["targetId"]) == ("use", "door_6_office")


def test_baseline_regression_stays_seated_without_oscillation():
    """Once seated at a goal-relevant desk chair, the baseline must keep sitting
    rather than oscillating between chairs (the bug the door-exemption fix removed).

    Pins acceptance 4a behavior: stay seated for the remainder of the run.
    """
    decide = StatefulAgentLoopDecision(goal_baseline(build_default_registry()))
    view = [
        entity("desk_chair_1", 0.4, affordances=("sit", "approach", "look_at")),
        entity("desk_chair_2", 3.0, affordances=("sit", "approach", "look_at")),
    ]
    obs = {**perception(view, scene="office_6"), "tick": 1}
    intents = []
    for tick in range(1, 7):
        obs = {**obs, "tick": tick}
        intents.append(decide(obs))
    assert all((i["verb"], i["targetId"]) == ("sit", "desk_chair_1") for i in intents)


def test_baseline_regression_waits_when_nothing_in_view():
    decide = StatefulAgentLoopDecision(goal_baseline(build_default_registry()))
    intent = decide(perception([], tick=1))
    assert intent["verb"] == "wait" and "targetId" not in intent


# ---------------------------------------------------------------------------
# Slow / live-model hooks (documented, not substituted as end-to-end)
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_local_qwen_gguf_smoke_skips_without_model():
    """Placeholder for the live Qwen3-0.6B GGUF smoke test.

    Requires NLT_AGENT_LOOP_GGUF_PATH pointing at a real Qwen3-0.6B GGUF file and the
    llama-cpp-python runtime. Not run here; flagged in the plan as live-model-only.
    """
    import os

    model_path = os.environ.get("NLT_AGENT_LOOP_GGUF_PATH")
    if not model_path:
        pytest.skip("Set NLT_AGENT_LOOP_GGUF_PATH to run the live GGUF smoke test")
    from pathlib import Path

    adapter = LlamaCppAgentLoopDecision(Path(model_path), context_size=2048, threads=2)
    obs = perception([entity("desk_1", 2.0, affordances=("use", "sit"))], tick=1)
    intent = FusionAgentLoop(adapter).handle_observation(obs)
    # desk_1 affords use/sit; any grounded verb (or wait) is acceptable.
    assert intent["verb"] in {"approach", "use", "sit", "look_at", "wait"}
