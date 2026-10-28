"""Tests for goal-relevance ranking and anti-repeat in the agent loop (AGENT-LOOP-003 F3)."""

import json

import pytest

from src.fusion import LlamaCppAgentLoopDecision, PROTOCOL_VERSION
from src.fusion.agent_loop_choices import (
    decision_schemas,
    grounded_choices,
    model_input,
    parse_decision,
)
from src.fusion.agent_loop_goals import with_goal
from src.fusion.agent_loop_memory import DecisionOutcome, DecisionRecord, StatefulAgentLoopDecision
from src.fusion.agent_loop_ranking import ARRIVAL_RADIUS, guide, is_goal_relevant
from src.fusion.agent_loop_registry import build_default_registry

FOCUS = ("focus",)


def entity(entity_id, x, z=0.0, affordances=("approach", "use", "look_at"), occupied=False):
    return {
        "id": entity_id,
        "kind": "place",
        "position": {"x": x, "y": 0.0, "z": z},
        "affordances": list(affordances),
        "occupied": occupied,
    }


def perception(entities, tick=1, x=0.0, scene="open_world"):
    return {
        "protocolVersion": PROTOCOL_VERSION,
        "messageType": "perception",
        "messageId": f"obs-{tick}",
        "agentId": "stay_alert_001",
        "tick": tick,
        "scene": {"id": scene, "kind": "open_world" if scene == "open_world" else "interior"},
        "self": {
            "position": {"x": x, "y": 0.0, "z": 0.0},
            "velocity": {"x": 0.0, "y": 0.0, "z": 0.0},
        },
        "visibleEntities": entities,
    }


def record(verb, target=None, changed=False, scene="open_world"):
    return DecisionRecord(
        tick=1,
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


PLAZA_VIEW = [
    entity("plaza", 0.5),
    entity("well", 6.0),
    entity("door_2_shop", 12.0),
    entity("door_1_office", 20.0),
]


@pytest.mark.parametrize(
    ("entity_id", "needs", "relevant"),
    [
        ("door_1_office", FOCUS, True),
        ("desk_3", FOCUS, True),
        ("desk_chair_2", FOCUS, True),
        ("door_2_shop", FOCUS, False),
        ("chair_1", FOCUS, False),
        ("plaza", FOCUS, False),
        ("sofa_1", ("rest", "quiet"), True),
        ("shore_2", ("rest", "quiet"), True),
        ("desk_3", ("rest",), False),
    ],
)
def test_relevance_comes_from_the_needs_and_the_ids_words(entity_id, needs, relevant):
    assert is_goal_relevant(entity_id, needs) is relevant


def test_entities_rank_goal_relevant_first_then_nearest():
    guidance = guide(perception(PLAZA_VIEW), FOCUS, ())
    assert guidance.order == ("door_1_office", "plaza", "well", "door_2_shop")
    assert guidance.goal_relevant == frozenset({"door_1_office"})
    assert guidance.distances["well"] == pytest.approx(6.0)


def test_equal_ranks_keep_engine_order():
    view = [entity("well", 5.0), entity("plaza", 0.0, z=5.0)]
    assert guide(perception(view), FOCUS, ()).order == ("well", "plaza")


def test_model_input_lists_ranked_entities_with_distance_and_relevance():
    observation = perception(PLAZA_VIEW)
    message = model_input(observation, guidance=guide(observation, FOCUS, ()))
    first = message["visibleEntities"][0]
    assert [e["id"] for e in message["visibleEntities"]] == [
        "door_1_office",
        "plaza",
        "well",
        "door_2_shop",
    ]
    assert first["distance"] == 20.0 and first["goalRelevant"] is True
    # The perception itself is not modified.
    assert "distance" not in observation["visibleEntities"][0]


def test_grounded_choices_follow_the_ranking():
    observation = perception(PLAZA_VIEW)
    choices = grounded_choices(observation, guide(observation, FOCUS, ()))
    assert choices["use"] == ["door_1_office", "plaza", "well", "door_2_shop"]


def test_last_pair_that_changed_nothing_is_dropped():
    observation = perception(PLAZA_VIEW, x=-5.0)
    guidance = guide(observation, FOCUS, (record("use", "well", changed=False),))
    assert ("use", "well") in guidance.excluded
    assert "well" not in grounded_choices(observation, guidance)["use"]


def test_last_pair_that_changed_something_stays():
    observation = perception(PLAZA_VIEW, x=-5.0)
    guidance = guide(observation, FOCUS, (record("approach", "well", changed=True),))
    assert ("approach", "well") not in guidance.excluded


def test_only_the_last_unchanged_pair_is_dropped():
    observation = perception(PLAZA_VIEW, x=-5.0)
    history = (
        record("use", "well", changed=False),
        record("approach", "door_2_shop", changed=True),
    )
    assert ("use", "well") not in guide(observation, FOCUS, history).excluded


def test_approach_is_dropped_within_the_arrival_radius():
    observation = perception(PLAZA_VIEW)
    guidance = guide(observation, FOCUS, ())
    assert guidance.distances["plaza"] <= ARRIVAL_RADIUS
    assert ("approach", "plaza") in guidance.excluded
    choices = grounded_choices(observation, guidance)
    assert "plaza" not in choices["approach"]
    assert "plaza" in choices["use"]


def test_looking_again_at_something_already_looked_at_is_dropped():
    observation = perception(PLAZA_VIEW, x=-5.0)
    history = (record("look_at", "plaza", changed=True), record("approach", "well", changed=True))
    choices = grounded_choices(observation, guide(observation, FOCUS, history))
    assert "plaza" not in choices["look_at"]
    assert "well" in choices["look_at"]


def test_a_new_scene_resets_anti_repeat():
    observation = perception(PLAZA_VIEW, x=-5.0, scene="office_1")
    history = (record("look_at", "plaza", changed=True), record("use", "well", changed=False))
    assert guide(observation, FOCUS, history).excluded == frozenset()


def test_wait_stays_allowed_when_every_pair_is_dropped():
    observation = perception([entity("plaza", 0.0, affordances=("approach", "look_at"))])
    guidance = guide(observation, FOCUS, (record("look_at", "plaza", changed=True),))
    choices = grounded_choices(observation, guidance)
    assert choices == {}
    assert decision_schemas(choices) == [
        {
            "type": "object",
            "properties": {"verb": {"const": "wait"}},
            "required": ["verb"],
            "additionalProperties": False,
        }
    ]


def test_an_excluded_pair_is_refused_if_a_model_outputs_it():
    observation = perception(PLAZA_VIEW)
    choices = grounded_choices(observation, guide(observation, FOCUS, ()))
    with pytest.raises(ValueError):
        parse_decision('{"verb":"approach","targetId":"plaza"}', choices, ValueError)


class FakeLlama:
    def __init__(self, content='{"verb":"look_at","targetId":"well"}'):
        self.content = content
        self.calls = []

    def create_chat_completion(self, **kwargs):
        self.calls.append(kwargs)
        return {"choices": [{"message": {"content": self.content}}]}

    def look_at_targets(self, index):
        for schema in self.calls[index]["response_format"]["schema"]["oneOf"]:
            if schema["properties"]["verb"].get("const") == "look_at":
                return schema["properties"]["targetId"]["enum"]
        return []


def test_gguf_grammar_drops_a_look_already_taken():
    fake = FakeLlama()
    decide = StatefulAgentLoopDecision(
        with_goal(LlamaCppAgentLoopDecision("unused.gguf", model=fake), build_default_registry())
    )

    decide(perception(PLAZA_VIEW, tick=1, x=-5.0))
    fake.content = '{"verb":"use","targetId":"door_1_office"}'
    decide(perception(PLAZA_VIEW, tick=2, x=-4.0))

    assert "well" in fake.look_at_targets(0)
    assert "well" not in fake.look_at_targets(1)
    first_entity = json.loads(fake.calls[1]["messages"][1]["content"])["visibleEntities"][0]
    assert first_entity["id"] == "door_1_office" and first_entity["goalRelevant"] is True


def test_looks_from_before_a_trip_inside_do_not_count_after_coming_back():
    observation = perception(PLAZA_VIEW, x=-5.0)
    history = (
        record("look_at", "plaza", changed=True),
        record("use", "door_1_office", changed=True),
        record("sit", "desk_chair_1", changed=True, scene="office_1"),
    )
    assert ("look_at", "plaza") not in guide(observation, FOCUS, history).excluded
