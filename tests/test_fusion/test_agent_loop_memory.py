"""Tests for per-agent decision memory in the agent loop (AGENT-LOOP-003 F1)."""

import pytest
from fastapi.testclient import TestClient

from src.fusion.agent_loop import AgentLoopProtocolError, FusionAgentLoop, PROTOCOL_VERSION
from src.fusion.agent_loop_http import build_decision_source, create_app
from src.fusion.agent_loop_memory import (
    DEFAULT_HISTORY_SIZE,
    OUTCOME_SOURCE,
    StatefulAgentLoopDecision,
    ignore_history,
)


def perception(
    tick=42,
    agent_id="avatar_1",
    scene_id="plaza",
    position=(0.0, 0.0),
    entities=None,
):
    x, z = position
    return {
        "protocolVersion": PROTOCOL_VERSION,
        "messageType": "perception",
        "messageId": f"obs-{tick}-{agent_id}",
        "agentId": agent_id,
        "tick": tick,
        "scene": {"id": scene_id, "kind": "open_world"},
        "self": {
            "position": {"x": x, "y": 0.0, "z": z},
            "velocity": {"x": 0.0, "y": 0.0, "z": 0.0},
        },
        "visibleEntities": (
            entities
            if entities is not None
            else [door(), bench()]
        ),
    }


def door(x=10.0, occupied=False):
    return {
        "id": "door_1",
        "kind": "place",
        "position": {"x": x, "y": 0.0, "z": 0.0},
        "affordances": ["approach", "use", "look_at"],
        "occupied": occupied,
    }


def bench(occupied=False):
    return {
        "id": "bench_1",
        "kind": "object",
        "position": {"x": 0.0, "y": 0.0, "z": 5.0},
        "affordances": ["approach", "sit", "look_at"],
        "occupied": occupied,
    }


def intent_for(observation, verb, target_id=None):
    message = {
        "protocolVersion": PROTOCOL_VERSION,
        "messageType": "intent",
        "messageId": f"intent-{observation['tick']}-{observation['agentId']}",
        "agentId": observation["agentId"],
        "observedTick": observation["tick"],
        "verb": verb,
    }
    if target_id is not None:
        message["targetId"] = target_id
    return message


class Scripted:
    """Decision source that returns a scripted verb/target and records the history it was given."""

    def __init__(self, *decisions):
        self.decisions = list(decisions)
        self.seen_histories = []

    def __call__(self, observation, history):
        self.seen_histories.append(history)
        verb, target = self.decisions.pop(0)
        return intent_for(observation, verb, target)


def test_outcomes_come_from_the_next_perception():
    assert OUTCOME_SOURCE == "next_perception"


def test_plugs_into_fusion_agent_loop_unchanged():
    source = Scripted(("approach", "door_1"))
    loop = FusionAgentLoop(decide=StatefulAgentLoopDecision(source))

    intent = loop.handle_observation(perception())

    assert intent["verb"] == "approach"
    assert intent["targetId"] == "door_1"
    assert source.seen_histories == [()]


def test_next_perception_resolves_the_previous_decision():
    source = Scripted(("approach", "door_1"), ("wait", None))
    decide = StatefulAgentLoopDecision(source)

    decide(perception(tick=42, position=(0.0, 0.0)))
    decide(perception(tick=44, position=(4.0, 0.0)))

    (record,) = source.seen_histories[1]
    assert (record.tick, record.scene_id, record.verb, record.target_id) == (
        42,
        "plaza",
        "approach",
        "door_1",
    )
    outcome = record.outcome
    assert outcome.ticks_elapsed == 2
    assert outcome.moved_distance == pytest.approx(4.0)
    assert outcome.target_visible is True
    assert outcome.target_distance_before == pytest.approx(10.0)
    assert outcome.target_distance_after == pytest.approx(6.0)
    assert outcome.changed is True


def test_look_at_that_changes_nothing_is_recorded_as_unchanged():
    # The 81-of-84 look_at loop: the agent turns, nothing in the perception moves.
    source = Scripted(("look_at", "door_1"), ("look_at", "door_1"))
    decide = StatefulAgentLoopDecision(source)

    decide(perception(tick=1))
    decide(perception(tick=2))

    (record,) = source.seen_histories[1]
    assert record.outcome.moved_distance == 0.0
    assert record.outcome.changed is False


def test_height_change_alone_is_not_movement():
    source = Scripted(("wait", None), ("wait", None))
    decide = StatefulAgentLoopDecision(source)
    first = perception(tick=1)
    second = perception(tick=2)
    second["self"]["position"]["y"] = 0.4

    decide(first)
    decide(second)

    assert decide.history("avatar_1")[0].outcome.moved_distance == 0.0


def test_scene_change_is_recorded():
    source = Scripted(("use", "door_1"), ("wait", None))
    decide = StatefulAgentLoopDecision(source)

    decide(perception(tick=1, position=(9.5, 0.0)))
    decide(perception(tick=3, scene_id="workplace_1", entities=[]))

    outcome = decide.history("avatar_1")[0].outcome
    assert outcome.scene_changed is True
    assert outcome.target_visible is False
    assert outcome.target_distance_after is None
    assert outcome.changed is True


def test_target_taken_by_someone_else_is_recorded():
    source = Scripted(("sit", "bench_1"), ("wait", None))
    decide = StatefulAgentLoopDecision(source)

    decide(perception(tick=1))
    decide(perception(tick=2, entities=[door(), bench(occupied=True)]))

    outcome = decide.history("avatar_1")[0].outcome
    assert outcome.target_taken is True
    assert outcome.changed is True


def test_targetless_decision_has_no_target_fields():
    source = Scripted(("wait", None), ("wait", None))
    decide = StatefulAgentLoopDecision(source)

    decide(perception(tick=1))
    decide(perception(tick=2))

    outcome = decide.history("avatar_1")[0].outcome
    assert outcome.target_visible is None
    assert outcome.target_distance_before is None
    assert outcome.target_taken is False
    assert outcome.changed is False


def test_agents_do_not_share_history():
    source = Scripted(("approach", "door_1"), ("wait", None), ("wait", None))
    decide = StatefulAgentLoopDecision(source)

    decide(perception(tick=1, agent_id="avatar_1"))
    decide(perception(tick=2, agent_id="avatar_2"))
    decide(perception(tick=3, agent_id="avatar_1"))

    assert source.seen_histories[1] == ()
    assert [r.verb for r in source.seen_histories[2]] == ["approach"]
    assert decide.history("avatar_2") == ()


def test_history_is_bounded():
    source = Scripted(*[("wait", None)] * 6)
    decide = StatefulAgentLoopDecision(source, history_size=3)

    for tick in range(1, 7):
        decide(perception(tick=tick))

    assert [record.tick for record in decide.history("avatar_1")] == [3, 4, 5]


def test_default_history_size():
    assert StatefulAgentLoopDecision(Scripted()).history_size == DEFAULT_HISTORY_SIZE == 8


def test_tick_going_backwards_clears_history():
    source = Scripted(("wait", None), ("wait", None), ("wait", None))
    decide = StatefulAgentLoopDecision(source)

    decide(perception(tick=10))
    decide(perception(tick=11))
    assert len(decide.history("avatar_1")) == 1

    decide(perception(tick=0))

    assert source.seen_histories[2] == ()
    assert decide.history("avatar_1") == ()


def test_repeated_tick_drops_the_pending_decision_without_an_outcome():
    source = Scripted(("approach", "door_1"), ("look_at", "door_1"), ("wait", None))
    decide = StatefulAgentLoopDecision(source)

    decide(perception(tick=5))
    decide(perception(tick=5))
    decide(perception(tick=6))

    assert source.seen_histories[1] == ()
    assert [r.verb for r in decide.history("avatar_1")] == ["look_at"]


def test_rejected_intent_is_not_remembered():
    def ungrounded(observation, history):
        return intent_for(observation, "sit", "missing_chair")

    decide = StatefulAgentLoopDecision(ungrounded)
    with pytest.raises(AgentLoopProtocolError):
        decide(perception(tick=1))

    follow_up = Scripted(("wait", None))
    decide._decide = follow_up
    decide(perception(tick=2))
    assert follow_up.seen_histories == [()]


def test_reset_forgets_one_agent_or_all():
    source = Scripted(*[("wait", None)] * 4)
    decide = StatefulAgentLoopDecision(source)
    for tick, agent in [(1, "a"), (2, "a"), (1, "b"), (2, "b")]:
        decide(perception(tick=tick, agent_id=agent))

    decide.reset("a")
    assert decide.history("a") == ()
    assert len(decide.history("b")) == 1

    decide.reset()
    assert decide.history("b") == ()


@pytest.mark.parametrize("size, error", [(0, ValueError), (True, TypeError), ("8", TypeError)])
def test_history_size_is_validated(size, error):
    with pytest.raises(error):
        StatefulAgentLoopDecision(Scripted(), history_size=size)


def test_ignore_history_adapts_a_stateless_source():
    def stateless(observation):
        return intent_for(observation, "wait")

    decide = StatefulAgentLoopDecision(ignore_history(stateless))
    assert decide(perception())["verb"] == "wait"


def test_endpoint_decision_source_remembers_per_agent(monkeypatch):
    monkeypatch.delenv("FUSION_GGUF_MODEL", raising=False)
    monkeypatch.setenv("FUSION_AGENT_LOOP_HISTORY", "2")
    decide = build_decision_source()
    assert isinstance(decide, StatefulAgentLoopDecision)
    assert decide.history_size == 2

    client = TestClient(create_app(decide=decide))
    for tick in (1, 2, 3):
        response = client.post("/agent-loop/perception", json=perception(tick=tick))
        assert response.status_code == 200

    history = decide.history("avatar_1")
    assert [record.tick for record in history] == [1, 2]
    # The fallback approaches the first free non-agent entity; memory does not change that yet.
    assert {record.verb for record in history} == {"approach"}
