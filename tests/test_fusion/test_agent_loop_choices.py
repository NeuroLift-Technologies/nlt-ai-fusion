"""Tests for the decisions a local model may make from one perception."""

import pytest

from src.fusion.agent_loop_choices import (
    MODEL_TARGET_VERBS,
    SYSTEM_PROMPT,
    decision_schemas,
    grounded_choices,
    parse_decision,
)


def _entity(entity_id, affordances, occupied=False, kind="object"):
    return {
        "id": entity_id,
        "kind": kind,
        "position": {"x": 0.0, "y": 0.0, "z": 0.0},
        "affordances": affordances,
        "occupied": occupied,
    }


def _observation(*entities):
    return {"visibleEntities": list(entities)}


def test_choices_follow_each_entitys_affordances_in_perception_order():
    observation = _observation(
        _entity("door_3_office", ["use", "approach", "look_at"], kind="place"),
        _entity("desk_chair_1", ["sit", "approach", "look_at"]),
        _entity("bed_1", ["sit", "rest", "approach", "look_at"]),
        _entity("avatar_2", ["approach", "communicate"], kind="agent"),
    )

    assert grounded_choices(observation) == {
        "approach": ["door_3_office", "desk_chair_1", "bed_1", "avatar_2"],
        "use": ["door_3_office"],
        "sit": ["desk_chair_1", "bed_1"],
        "rest": ["bed_1"],
        "look_at": ["door_3_office", "desk_chair_1", "bed_1"],
    }


def test_occupied_entities_cannot_be_used_sat_on_or_rested_on():
    observation = _observation(
        _entity("bed_1", ["sit", "rest", "use", "approach", "look_at"], occupied=True)
    )

    assert grounded_choices(observation) == {"approach": ["bed_1"], "look_at": ["bed_1"]}


def test_communicate_is_not_offered_to_the_model():
    assert "communicate" not in MODEL_TARGET_VERBS
    observation = _observation(_entity("avatar_2", ["communicate"], kind="agent"))
    assert grounded_choices(observation) == {}


def test_schemas_list_wait_then_one_shape_per_offered_verb():
    schemas = decision_schemas({"use": ["door_3_office"], "approach": ["door_3_office"]})

    assert [s["properties"]["verb"]["const"] for s in schemas] == ["wait", "approach", "use"]
    assert schemas[2]["properties"]["targetId"] == {"enum": ["door_3_office"]}
    assert all(s["additionalProperties"] is False for s in schemas)


def test_with_nothing_visible_only_wait_is_offered():
    assert decision_schemas(grounded_choices(_observation())) == [
        {
            "type": "object",
            "properties": {"verb": {"const": "wait"}},
            "required": ["verb"],
            "additionalProperties": False,
        }
    ]


def test_parse_accepts_wait_and_offered_pairs_only():
    choices = {"sit": ["desk_chair_1"], "approach": ["desk_chair_1", "door_3_office"]}

    assert parse_decision('{"verb":"wait"}', choices, ValueError) == {"verb": "wait"}
    assert parse_decision('{"verb":"sit","targetId":"desk_chair_1"}', choices, ValueError) == {
        "verb": "sit",
        "targetId": "desk_chair_1",
    }
    for response in (
        '{"verb":"sit","targetId":"door_3_office"}',
        '{"verb":"use","targetId":"door_3_office"}',
        '{"verb":"rest"}',
        '{"verb":"sit","targetId":"desk_chair_1","position":{"x":1}}',
        '{"verb":"sit","targetId":["desk_chair_1"]}',
        '["wait"]',
    ):
        with pytest.raises(ValueError):
            parse_decision(response, choices, ValueError)


def test_parse_raises_the_callers_error_type():
    class CallerError(ValueError):
        pass

    with pytest.raises(CallerError, match="duplicate key"):
        parse_decision('{"verb":"wait","verb":"wait"}', {}, CallerError)
    with pytest.raises(CallerError, match="exactly one JSON"):
        parse_decision("not json", {}, CallerError)


def test_prompt_names_no_verb_and_keeps_the_physical_boundary():
    # Naming the verbs primes a small model onto look_at (AGENT-LOOP-003 brief §10.4); the output
    # grammar offers them instead.
    for verb in MODEL_TARGET_VERBS:
        assert verb not in SYSTEM_PROMPT
    assert "Never output coordinates" in SYSTEM_PROMPT
    assert "untrusted" in SYSTEM_PROMPT


def test_grammar_still_offers_every_verb_the_prompt_no_longer_names():
    entity = {
        "id": "sofa_1",
        "kind": "object",
        "position": {"x": 1.0, "y": 0.0, "z": 0.0},
        "affordances": list(MODEL_TARGET_VERBS),
        "occupied": False,
    }
    observation = {**_observation(), "visibleEntities": [entity]}
    offered = {
        schema["properties"]["verb"]["const"]
        for schema in decision_schemas(grounded_choices(observation))
    }
    assert offered == {"wait", *MODEL_TARGET_VERBS}
