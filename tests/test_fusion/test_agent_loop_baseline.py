"""Tests for the deterministic goal-driven decision source (AGENT-LOOP-003 F4)."""

from src.fusion import PROTOCOL_VERSION
from src.fusion.agent_loop import validate_intent
from src.fusion.agent_loop_baseline import goal_baseline
from src.fusion.agent_loop_memory import StatefulAgentLoopDecision
from src.fusion.agent_loop_registry import build_default_registry


def entity(entity_id, x, affordances=("approach", "use", "look_at")):
    return {
        "id": entity_id,
        "kind": "place",
        "position": {"x": x, "y": 0.0, "z": 0.0},
        "affordances": list(affordances),
        "occupied": False,
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


def baseline():
    return StatefulAgentLoopDecision(goal_baseline(build_default_registry()))


def test_goes_through_the_goal_relevant_door_when_it_is_in_view():
    observation = perception([entity("plaza", 0.5), entity("door_6_office", 20.0)])
    intent = baseline()(observation)
    assert (intent["verb"], intent["targetId"]) == ("use", "door_6_office")
    validate_intent(intent, observation)


def test_explores_unvisited_targets_when_the_goal_is_not_in_view():
    decide = baseline()
    first = decide(perception([entity("plaza", 0.5), entity("well", 6.0)], tick=1))
    # Now standing at the well; the plaza has not been visited.
    second = decide(perception([entity("plaza", 6.0), entity("well", 0.5)], tick=2, x=0.0))
    assert (first["verb"], first["targetId"]) == ("approach", "well")
    assert (second["verb"], second["targetId"]) == ("approach", "plaza")


def test_sits_at_the_desk_inside_the_office():
    view = [
        entity("desk_1", 2.0),
        entity("desk_chair_1", 2.5, affordances=("sit", "approach", "look_at")),
    ]
    intent = baseline()(perception(view, scene="office_6"))
    assert (intent["verb"], intent["targetId"]) == ("sit", "desk_chair_1")


def test_waits_when_nothing_is_in_view():
    intent = baseline()(perception([]))
    assert intent["verb"] == "wait" and "targetId" not in intent


def test_intent_carries_only_verb_and_target():
    intent = baseline()(perception([entity("well", 6.0)]))
    assert set(intent) == {
        "protocolVersion",
        "messageType",
        "messageId",
        "agentId",
        "observedTick",
        "verb",
        "targetId",
    }


def test_stays_seated_across_decisions_once_at_the_desk():
    decide = baseline()
    view = [entity("desk_chair_1", 0.4, affordances=("sit", "approach", "look_at"))]
    first = decide(perception(view, tick=1, scene="office_6"))
    second = decide(perception(view, tick=2, scene="office_6"))
    assert (first["verb"], first["targetId"]) == ("sit", "desk_chair_1")
    assert (second["verb"], second["targetId"]) == ("sit", "desk_chair_1")


def test_waits_when_every_pair_is_excluded_or_occupied():
    taken = entity("sofa_1", 0.5, affordances=("sit", "rest", "approach"))
    taken["occupied"] = True
    intent = baseline()(perception([taken]))
    assert intent["verb"] == "wait"


def test_with_no_goal_in_view_the_baseline_explores_instead_of_using_what_is_near():
    decide = baseline()
    intent = decide(perception([entity("plaza", 6.0), entity("well", 0.5)], tick=1))
    assert (intent["verb"], intent["targetId"]) == ("approach", "plaza")
