"""Tests for goal-relevance ranking and anti-repeat in the agent loop (AGENT-LOOP-003 F3)."""

import json
from dataclasses import replace

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
    # No coordinates or velocity reach the model, and the perception itself is not modified.
    assert "self" not in message and "position" not in first
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

    def options(self, index):
        """(verb, target) pairs the grammar offers, in order; wait has no target."""
        pairs = []
        for schema in self.calls[index]["response_format"]["schema"]["oneOf"]:
            target = schema["properties"].get("targetId", {})
            pairs.append((schema["properties"]["verb"]["const"], target.get("const")))
        return pairs

    def look_at_targets(self, index):
        return [target for verb, target in self.options(index) if verb == "look_at"]


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


SPAWN_VIEW = [entity("plaza", 0.5), entity("well", 6.0)]


def test_at_the_spawn_the_first_option_approaches_the_nearest_unvisited_target():
    # plaza is within the arrival radius, so approaching it is excluded; well is unvisited.
    assert guide(perception(SPAWN_VIEW), FOCUS, ()).options[0] == ("approach", "well")


def test_after_visiting_a_target_the_next_unvisited_one_comes_first():
    observation = perception([entity("plaza", 6.0), entity("well", 0.5)], x=0.0)
    history = (record("approach", "well", changed=True),)
    assert guide(observation, FOCUS, history).options[0] == ("approach", "plaza")


def test_a_goal_relevant_target_comes_before_any_unvisited_one():
    options = guide(perception(PLAZA_VIEW), FOCUS, ()).options
    assert options[0] == ("use", "door_1_office")
    assert options[1] == ("approach", "door_1_office")
    assert options[2] == ("approach", "well")


def test_inside_the_office_sitting_at_the_desk_comes_first():
    view = [
        entity("desk_1", 2.0, affordances=("use", "approach", "look_at")),
        entity("desk_chair_1", 2.5, affordances=("sit", "approach", "look_at")),
        entity("sofa_1", 1.5, affordances=("sit", "rest", "approach", "look_at")),
    ]
    options = guide(perception(view, scene="office_1"), FOCUS, ()).options
    assert options[:2] == (("sit", "desk_chair_1"), ("use", "desk_1"))


def test_a_need_for_rest_puts_rest_first():
    view = [entity("sofa_1", 2.0, affordances=("sit", "rest", "approach", "look_at"))]
    options = guide(perception(view, scene="home_1"), ("rest", "quiet"), ()).options
    assert options[0] == ("rest", "sofa_1")


def test_visits_from_another_scene_do_not_count():
    history = (
        record("approach", "well", changed=True),
        record("sit", "chair_1", changed=True, scene="home_1"),
    )
    assert guide(perception(SPAWN_VIEW), FOCUS, history).options[0] == ("approach", "well")


def test_input_and_grammar_offer_the_ranked_options_with_wait_last():
    fake = FakeLlama(content='{"verb":"approach","targetId":"well"}')
    decide = StatefulAgentLoopDecision(
        with_goal(LlamaCppAgentLoopDecision("unused.gguf", model=fake), build_default_registry())
    )
    decide(perception(SPAWN_VIEW))

    offered = fake.options(0)
    message = json.loads(fake.calls[0]["messages"][1]["content"])
    listed = [(o["verb"], o.get("targetId")) for o in message["options"]]
    assert offered == listed
    assert offered[0] == ("approach", "well")
    assert offered[-1] == ("wait", None)


def test_staying_seated_at_a_goal_relevant_chair_is_not_dropped():
    view = [
        entity("desk_chair_1", 0.4, affordances=("sit", "approach", "look_at")),
        entity("desk_chair_2", 3.0, affordances=("sit", "approach", "look_at")),
    ]
    history = (record("sit", "desk_chair_1", changed=False, scene="office_1"),)
    options = guide(perception(view, scene="office_1"), FOCUS, history).options
    assert options[0] == ("sit", "desk_chair_1")


def test_an_unchanged_sit_away_from_the_target_is_still_dropped():
    view = [entity("desk_chair_1", 3.0, affordances=("sit", "approach", "look_at"))]
    history = (record("sit", "desk_chair_1", changed=False, scene="office_1"),)
    guidance = guide(perception(view, scene="office_1"), FOCUS, history)
    assert ("sit", "desk_chair_1") in guidance.excluded


def test_an_unchanged_door_use_at_the_door_is_still_dropped():
    # Using a door is a transition; one that changed nothing failed and must not repeat forever.
    observation = perception([entity("door_1_office", 0.5), entity("well", 6.0)])
    history = (record("use", "door_1_office", changed=False),)
    assert ("use", "door_1_office") in guide(observation, FOCUS, history).excluded


def test_staying_at_a_chair_that_does_not_serve_the_goal_is_dropped():
    view = [entity("chair_1", 0.4, affordances=("sit", "approach", "look_at"))]
    history = (record("sit", "chair_1", changed=False, scene="home_1"),)
    assert ("sit", "chair_1") in guide(perception(view, scene="home_1"), FOCUS, history).excluded


@pytest.mark.parametrize("verb", ["approach", "look_at"])
def test_only_holding_verbs_are_exempt(verb):
    view = [entity("desk_1", 3.0, affordances=("use", "approach", "look_at"))]
    history = (record(verb, "desk_1", changed=False, scene="office_1"),)
    assert (verb, "desk_1") in guide(perception(view, scene="office_1"), FOCUS, history).excluded


def test_third_tier_puts_approaches_before_holding_verbs_and_look_at_last():
    view = [entity("well", 6.0), entity("plaza", 3.0), entity("door_1_office", 20.0)]
    history = (record("approach", "well", changed=True), record("approach", "plaza", changed=True))
    options = guide(perception(view, x=0.0), FOCUS, history).options
    assert options[:2] == (("use", "door_1_office"), ("approach", "door_1_office"))
    assert options[2:] == (
        ("approach", "plaza"),
        ("approach", "well"),
        ("use", "plaza"),
        ("use", "well"),
        ("look_at", "door_1_office"),
        ("look_at", "plaza"),
        ("look_at", "well"),
    )


def test_visited_targets_are_approached_least_recently_visited_first_then_farthest():
    view = [entity("plaza", 3.0), entity("well", 6.0), entity("door_2_shop", 9.0)]
    history = (
        record("approach", "plaza", changed=True),
        record("approach", "door_2_shop", changed=True),
        record("approach", "well", changed=True),
        record("look_at", "well", changed=False),
    )
    options = guide(perception(view), FOCUS, history).options
    approaches = [target for verb, target in options if verb == "approach"]
    assert approaches == ["plaza", "door_2_shop", "well"]
    history = (
        record("use", "plaza", changed=True),
        record("use", "well", changed=True),
        record("look_at", "well", changed=False),
    )
    # Visited equally long ago: none of these approaches was chosen, so the most recent visit
    # decides, then distance.
    options = guide(perception(view), FOCUS, history).options
    assert options[0] == ("approach", "door_2_shop")


def test_alternating_between_two_holding_pairs_is_broken_up():
    # The use well / use plaza loop from the #135 engine run: neither use moved the agent.
    view = [entity("well", 6.0), entity("plaza", 8.0), entity("bench", 4.0)]
    history = (record("use", "well"), record("use", "plaza"))
    options = guide(perception(view), FOCUS, history).options
    holding = [pair for pair in options if pair[0] == "use"]
    # use plaza was the last pair and changed nothing (rule 1); use well was chosen before and
    # now ranks below the bench, which was not, and below every approach.
    assert holding == [("use", "bench"), ("use", "well")]
    assert all(options.index(("use", "well")) > options.index(pair)
               for pair in options if pair[0] == "approach")


def test_holding_pairs_on_targets_that_do_not_serve_the_goal_stay_allowed():
    view = [entity("well", 0.5), entity("plaza", 6.0)]
    history = (record("approach", "plaza", changed=True), record("approach", "well", changed=True))
    options = guide(perception(view), FOCUS, history).options
    assert ("use", "well") in options and ("use", "plaza") in options
    assert options[0] == ("approach", "plaza")


def test_a_visited_goal_target_that_only_affords_approach_does_not_ping_pong():
    view = [
        entity("shore_0", 6.0, affordances=("approach", "look_at")),
        entity("shore_1", 9.0, affordances=("approach", "look_at")),
        entity("well", 12.0),
    ]
    history = (
        record("approach", "shore_0", changed=True),
        record("approach", "shore_1", changed=True),
    )
    options = guide(perception(view), ("rest", "quiet"), history).options
    assert options[0] == ("approach", "well")


@pytest.mark.parametrize(
    ("view", "history", "needs"),
    [
        (PLAZA_VIEW, (), FOCUS),
        (PLAZA_VIEW, (record("look_at", "well", changed=True),), FOCUS),
        (SPAWN_VIEW, (record("approach", "well", changed=False),), ("rest", "quiet")),
        ([entity("sofa_1", 0.5, affordances=("sit", "rest", "approach", "look_at"),
                 occupied=True)], (), ("rest",)),
    ],
)
def test_options_are_exactly_the_allowed_pairs_and_each_parses(view, history, needs):
    observation = perception(view)
    guidance = guide(observation, needs, history)
    choices = grounded_choices(observation, guidance)
    allowed = {(verb, target) for verb, targets in choices.items() for target in targets}
    assert set(guidance.options) == allowed
    assert len(guidance.options) == len(allowed)
    for verb, target in guidance.options:
        decision = json.dumps({"verb": verb, "targetId": target})
        assert parse_decision(decision, choices, ValueError) == {"verb": verb, "targetId": target}


def test_input_lists_at_most_the_best_options_while_the_grammar_offers_all():
    from src.fusion.agent_loop_choices import MAX_LISTED_OPTIONS

    seats = [
        entity(f"desk_chair_{i}", 2.0 + i, affordances=("sit", "approach", "look_at"))
        for i in range(10)
    ]
    fake = FakeLlama(content='{"verb":"sit","targetId":"desk_chair_0"}')
    decide = StatefulAgentLoopDecision(
        with_goal(LlamaCppAgentLoopDecision("unused.gguf", model=fake), build_default_registry())
    )
    decide(perception(seats, scene="cafe_1"))

    message = json.loads(fake.calls[0]["messages"][1]["content"])
    assert len(message["options"]) == MAX_LISTED_OPTIONS + 1
    assert message["options"][-1] == {"verb": "wait"}
    assert len(fake.options(0)) == 30 + 1


def test_with_no_goal_in_view_approaches_come_first_farthest_unvisited_first():
    observation = perception(
        [entity("plaza", 3.0), entity("well", 8.0), entity("door_2_shop", 20.0)]
    )
    guidance = guide(observation, FOCUS, (record("approach", "door_2_shop", changed=True),))
    assert guidance.options[:3] == (
        ("approach", "well"),
        ("approach", "plaza"),
        ("approach", "door_2_shop"),
    )
    # Demoted, not forbidden (Josh, 2026-10-28).
    assert guidance.options[3:6] == (
        ("use", "plaza"),
        ("use", "well"),
        ("use", "door_2_shop"),
    )
    assert ("use", "well") not in guidance.excluded and ("look_at", "plaza") in guidance.options


def test_at_the_spawn_exploring_walks_to_the_other_landmark_instead_of_using_one():
    # Standing at the well with the plaza visited: the only move is back across to the plaza,
    # which is what brings the shop and office doors into view in the engine.
    observation = perception([entity("plaza", 6.0), entity("well", 0.5)])
    history = (record("approach", "plaza", changed=True), record("approach", "well", changed=True))
    assert guide(observation, FOCUS, history).options[0] == ("approach", "plaza")


def test_exploring_ends_as_soon_as_something_goal_relevant_is_in_view():
    observation = perception(
        [entity("plaza", 3.0), entity("well", 8.0), entity("door_1_office", 22.0)]
    )
    guidance = guide(observation, FOCUS, ())
    assert guidance.options[0] == ("use", "door_1_office")
    assert ("use", "well") in guidance.options


def test_with_no_approach_left_the_other_choices_are_kept():
    # Nothing to walk to: exploring cannot leave the agent with only wait if it can still act.
    observation = perception([entity("well", 0.5)])
    options = guide(observation, FOCUS, ()).options
    assert ("use", "well") in options and ("approach", "well") not in options


def test_exploring_finishes_the_walk_under_way_before_turning_back():
    # Halfway from the well to the plaza: both visited, the well is now farther, but the agent
    # keeps walking to the plaza instead of turning back.
    observation = perception([entity("plaza", 2.8), entity("well", 5.7)])
    history = (record("approach", "well", changed=True), record("approach", "plaza", changed=True))
    assert guide(observation, FOCUS, history).options[0] == ("approach", "plaza")


def test_a_new_unvisited_target_still_comes_before_the_walk_under_way():
    observation = perception(
        [entity("plaza", 2.8), entity("well", 5.7), entity("door_7_shop", 24.0)]
    )
    history = (record("approach", "plaza", changed=True),)
    assert guide(observation, FOCUS, history).options[0] == ("approach", "door_7_shop")


def test_a_target_that_moved_while_the_agent_stood_still_is_not_a_walk_under_way():
    # The outcome "changed" only because the target moved; the agent did not move.
    moved_target = DecisionRecord(
        tick=1,
        scene_id="open_world",
        verb="approach",
        target_id="plaza",
        outcome=DecisionOutcome(
            ticks_elapsed=1,
            moved_distance=0.0,
            scene_changed=False,
            target_visible=True,
            target_distance_before=2.0,
            target_distance_after=4.0,
            target_taken=False,
        ),
    )
    assert moved_target.outcome.changed
    observation = perception([entity("plaza", 4.0), entity("well", 9.0)])
    history = (record("approach", "well", changed=True), moved_target)
    # Without a walk under way, the least recently visited target comes first.
    assert guide(observation, FOCUS, history).options[0] == ("approach", "well")


def moving(observation, vx):
    observation["self"]["velocity"] = {"x": vx, "y": 0.0, "z": 0.0}
    return observation


def approach_record(target, before, after, scene="open_world"):
    return DecisionRecord(
        tick=1,
        scene_id=scene,
        verb="approach",
        target_id=target,
        outcome=DecisionOutcome(
            ticks_elapsed=1,
            moved_distance=0.5,
            scene_changed=False,
            target_visible=True,
            target_distance_before=before,
            target_distance_after=after,
            target_taken=False,
        ),
    )


def test_a_target_the_avatar_will_have_walked_out_of_reach_of_is_left_out():
    # Office door 24 m ahead (+x); the avatar walks away (-x) at 1.4 m/s; a 7 s decision puts
    # it 33.8 m away at execution, beyond the engine's 30 m reach.
    observation = moving(perception([entity("door_1_office", 24.0), entity("well", -3.0)]), -1.4)
    guidance = guide(observation, FOCUS, (), latency_seconds=7.0)
    assert not any(target == "door_1_office" for _, target in guidance.options)
    assert ("use", "door_1_office") in guidance.excluded


def test_the_same_target_stays_when_the_avatar_stands_still_or_walks_toward_it():
    for vx in (0.0, 1.4):
        observation = moving(perception([entity("door_1_office", 24.0)]), vx)
        assert guide(observation, FOCUS, (), latency_seconds=7.0).options[0] == (
            "use",
            "door_1_office",
        )


def test_a_goal_out_of_reach_does_not_stop_the_agent_exploring():
    observation = moving(
        perception([entity("door_1_office", 24.0), entity("well", -3.0), entity("plaza", -8.0)]),
        -1.4,
    )
    options = guide(observation, FOCUS, (), latency_seconds=7.0).options
    assert options[:2] == (("approach", "plaza"), ("approach", "well"))
    assert not any(target == "door_1_office" for _, target in options)


def test_an_approach_that_made_no_progress_blocks_the_target():
    observation = perception([entity("door_4_home", 7.6), entity("well", 12.0)])
    history = (approach_record("door_4_home", before=7.6, after=7.6),)
    guidance = guide(observation, FOCUS, history)
    assert ("approach", "door_4_home") in guidance.excluded
    assert ("use", "door_4_home") in guidance.excluded
    assert guidance.options[0] == ("approach", "well")


def test_an_approach_that_got_closer_or_arrived_does_not_block():
    observation = perception([entity("door_4_home", 3.0), entity("well", 12.0)])
    for before, after in ((7.6, 3.0), (2.0, 0.5)):
        history = (approach_record("door_4_home", before=before, after=after),)
        assert ("approach", "door_4_home") not in guide(observation, FOCUS, history).excluded


def use_record(target, before, after):
    return replace(approach_record(target, before, after), verb="use")


def test_a_use_that_left_the_agent_short_of_the_target_blocks_it():
    # Measured with Qwen: `use door_4_home` chosen 9 times while the agent stood 7.61 m away.
    observation = perception([entity("door_4_home", 7.6), entity("well", 12.0)])
    guidance = guide(observation, FOCUS, (use_record("door_4_home", before=7.61, after=7.61),))
    assert ("use", "door_4_home") in guidance.excluded


def test_using_a_target_from_within_the_hold_radius_does_not_block_it():
    observation = perception([entity("well", 1.2)])
    guidance = guide(observation, FOCUS, (use_record("well", before=1.2, after=1.2),))
    assert ("use", "well") not in guidance.excluded


def test_an_approach_after_which_the_agent_ended_up_farther_away_does_not_block():
    # Measured at the spawn with Qwen: the wander after `look_at plaza` carried the agent from
    # 4.6 m to 5.2 m of the plaza while `approach plaza` was being decided.
    observation = perception([entity("plaza", 2.5), entity("well", 5.7)])
    history = (approach_record("plaza", before=4.6, after=5.2),)
    guidance = guide(observation, FOCUS, history)
    assert ("approach", "plaza") not in guidance.excluded
    assert ("use", "plaza") not in guidance.excluded


def test_a_blocked_target_is_retried_after_going_through_a_door():
    observation = perception([entity("door_4_home", 7.6)], scene="open_world")
    history = (
        approach_record("door_4_home", before=7.6, after=7.6),
        record("sit", "chair_1", changed=True, scene="home_4"),
    )
    assert ("approach", "door_4_home") not in guide(observation, FOCUS, history).excluded


def test_the_model_path_assumes_a_slow_first_decision_for_the_reach_guard():
    fake = FakeLlama(content='{"verb":"approach","targetId":"well"}')
    decide = StatefulAgentLoopDecision(
        with_goal(LlamaCppAgentLoopDecision("unused.gguf", model=fake), build_default_registry())
    )
    # 24 m away, walking away at 2 m/s: with the 5 s default the door is 34 m off at execution.
    decide(moving(perception([entity("door_1_office", 24.0), entity("well", -3.0)]), -2.0))
    assert not any(target == "door_1_office" for _, target in fake.options(0))


def test_a_seated_agent_that_drifts_just_past_the_arrival_radius_stays_seated():
    view = [
        entity("desk_chair_2", 1.05, affordances=("sit", "approach", "look_at")),
        entity("desk_chair_1", 4.3, affordances=("sit", "approach", "look_at")),
    ]
    history = (record("sit", "desk_chair_2", changed=False, scene="office_1"),)
    options = guide(perception(view, scene="office_1"), FOCUS, history).options
    assert options[0] == ("sit", "desk_chair_2")
