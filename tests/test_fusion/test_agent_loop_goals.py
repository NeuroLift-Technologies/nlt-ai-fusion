"""Tests for the agent's goal and recent-history context in the agent loop (AGENT-LOOP-003 F2)."""

import json

import pytest
from fastapi.testclient import TestClient

from src.avatars.base_avatar import AvatarState
from src.fusion import LlamaCppAgentLoopDecision, PROTOCOL_VERSION
from src.fusion.agent_loop_choices import SYSTEM_PROMPT, model_input
from src.fusion.agent_loop_goals import (
    RECENT_WINDOW,
    AgentGoal,
    decision_context,
    derive_goal,
    with_goal,
)
from src.fusion.agent_loop_http import create_app
from src.fusion.agent_loop_memory import DecisionOutcome, DecisionRecord, StatefulAgentLoopDecision
from src.fusion.agent_loop_registry import UnknownAgentError, build_default_registry


def perception(tick=1, agent_id="stay_alert_001", x=0.0):
    return {
        "protocolVersion": PROTOCOL_VERSION,
        "messageType": "perception",
        "messageId": f"obs-{tick}",
        "agentId": agent_id,
        "tick": tick,
        "scene": {"id": "open_world", "kind": "open_world"},
        "self": {
            "position": {"x": x, "y": 0.0, "z": 0.0},
            "velocity": {"x": 0.0, "y": 0.0, "z": 0.0},
        },
        "visibleEntities": [
            {
                "id": "door_5_home",
                "kind": "place",
                "position": {"x": 20.0, "y": 0.0, "z": 0.0},
                "affordances": ["use", "approach", "look_at"],
                "occupied": False,
            }
        ],
    }


def record(verb, target=None, changed=False, tick=1):
    return DecisionRecord(
        tick=tick,
        scene_id="open_world",
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


class FakeLlama:
    def __init__(self, content='{"verb":"approach","targetId":"door_5_home"}'):
        self.content = content
        self.calls = []

    def create_chat_completion(self, **kwargs):
        self.calls.append(kwargs)
        return {"choices": [{"message": {"content": self.content}}]}

    def user_message(self, index=-1):
        return json.loads(self.calls[index]["messages"][1]["content"])


@pytest.fixture
def avatar():
    return build_default_registry().get("stay_alert_001").avatar


def test_stay_alert_with_nothing_pressing_gets_its_trait_goal(avatar):
    goal = derive_goal(avatar)
    assert goal == AgentGoal(
        goal="start the task you have been putting off: get to your desk and sit down to work",
        needs=("focus",),
    )


@pytest.mark.parametrize(
    "change",
    [
        lambda a: setattr(a, "stress_level", 0.8),
        lambda a: setattr(a, "burnout_risk_level", 0.65),
        lambda a: setattr(a, "current_state", AvatarState.BURNOUT_RISK),
    ],
)
def test_strain_turns_the_goal_to_recovery(avatar, change):
    change(avatar)
    goal = derive_goal(avatar)
    assert goal.goal.startswith("recover after stress")
    assert goal.needs == ("rest", "quiet")


def test_high_cognitive_load_asks_for_a_break(avatar):
    avatar.cognitive_load = 0.75
    assert derive_goal(avatar).needs == ("rest",)


def test_unknown_trait_gets_the_default_goal(avatar):
    avatar.trait_name = "SomethingElse"
    assert derive_goal(avatar).goal == "get going on today's task"


def test_deriving_a_goal_changes_nothing_on_the_avatar(avatar):
    before = avatar.get_state_summary()
    derive_goal(avatar)
    after = avatar.get_state_summary()
    before.pop("last_activity")
    after.pop("last_activity")
    assert before == after


def test_context_shows_goal_needs_and_the_recent_window():
    history = [record("look_at", "plaza", tick=t) for t in range(1, 7)]
    history.append(record("wait", changed=True, tick=7))
    context = decision_context(AgentGoal("g", ("rest",)), history)

    assert context["goal"] == "g"
    assert context["needs"] == ["rest"]
    assert len(context["recent"]) == RECENT_WINDOW
    assert context["recent"][-2] == {"did": "look_at plaza", "changed": False}
    assert context["recent"][-1] == {"did": "wait", "changed": True}


def test_context_with_no_history_has_an_empty_window():
    assert decision_context(AgentGoal("g", ()), [])["recent"] == []


def test_model_input_adds_context_only_when_given():
    observation = perception()
    assert "context" not in model_input(observation)
    assert model_input(observation, {"goal": "g"})["context"] == {"goal": "g"}


def test_system_prompt_tells_the_model_how_to_use_the_context():
    assert "goal" in SYSTEM_PROMPT and "changed nothing" in SYSTEM_PROMPT


def test_gguf_prompt_carries_the_registered_avatars_goal_and_history():
    registry = build_default_registry()
    fake = FakeLlama()
    model = LlamaCppAgentLoopDecision("unused.gguf", model=fake)
    decide = StatefulAgentLoopDecision(with_goal(model, registry))

    decide(perception(tick=1, x=0.0))
    decide(perception(tick=2, x=3.0))

    first, second = fake.user_message(0), fake.user_message(1)
    assert first["context"]["goal"].startswith("start the task you have been putting off")
    assert first["context"]["recent"] == []
    assert second["context"]["recent"] == [{"did": "approach door_5_home", "changed": True}]


def test_goal_follows_the_avatars_state_between_decisions():
    registry = build_default_registry()
    fake = FakeLlama()
    decide = StatefulAgentLoopDecision(
        with_goal(LlamaCppAgentLoopDecision("unused.gguf", model=fake), registry)
    )

    decide(perception(tick=1))
    registry.get("stay_alert_001").avatar.stress_level = 0.9
    # The agent moved, so F3 still allows the fake model's repeated approach.
    decide(perception(tick=2, x=3.0))

    assert fake.user_message(1)["context"]["needs"] == ["rest", "quiet"]


def test_unregistered_agent_has_no_goal():
    decide = with_goal(lambda observation, context: {}, build_default_registry())
    with pytest.raises(UnknownAgentError):
        decide(perception(agent_id="__local_avatar__"), ())


def test_endpoint_sends_only_verb_and_target_to_the_engine():
    registry = build_default_registry()
    fake = FakeLlama()
    decide = StatefulAgentLoopDecision(
        with_goal(LlamaCppAgentLoopDecision("unused.gguf", model=fake), registry)
    )
    client = TestClient(create_app(decide=decide, registry=registry))

    response = client.post("/agent-loop/perception", json=perception())

    assert response.status_code == 200
    body = response.json()
    assert body["verb"] == "approach" and body["targetId"] == "door_5_home"
    assert not {"context", "goal", "needs", "recent"} & set(body)
    assert "context" in fake.user_message()
