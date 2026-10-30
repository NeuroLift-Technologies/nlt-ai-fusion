"""
Tests for BaseNPC and NPCReaction

Covers src/simulation/npcs/base_npc.py and the npcs __init__ re-export.
Uses a minimal concrete subclass to exercise abstract BaseNPC.
"""

import pytest
from src.simulation.npcs import BaseNPC, NPCDisposition, NPCReaction  # covers __init__.py
from src.simulation.npcs.base_npc import BaseNPC as _BaseNPCDirect


class _TestNPC(BaseNPC):
    """Minimal concrete NPC for testing."""

    def react_to_event(self, event_type: str, event_data: dict) -> NPCReaction:
        return NPCReaction(
            npc_id=self.npc_id,
            npc_name=self.name,
            reaction_type="verbal",
        )


class TestBaseNPCInit:
    def test_default_construction(self):
        npc = _TestNPC()
        assert npc.name == "NPC"
        assert npc.role == "bystander"
        assert npc.disposition == NPCDisposition.NEUTRAL
        assert npc.patience == pytest.approx(0.7)
        assert npc.relationship_score == pytest.approx(0.5)
        assert npc.interaction_history == []

    def test_custom_construction(self):
        npc = _TestNPC(
            npc_id="npc-001",
            name="Manager Bob",
            role="manager",
            config={"style": "strict"},
        )
        assert npc.npc_id == "npc-001"
        assert npc.name == "Manager Bob"
        assert npc.role == "manager"
        assert npc.config["style"] == "strict"

    def test_auto_generated_npc_id(self):
        npc1 = _TestNPC()
        npc2 = _TestNPC()
        assert npc1.npc_id != npc2.npc_id


class TestUpdateDisposition:
    def setup_method(self):
        self.npc = _TestNPC(name="Test NPC")

    def test_positive_action_increases_patience(self):
        before = self.npc.patience
        self.npc.update_disposition("task_completed")
        assert self.npc.patience > before

    def test_positive_action_increases_relationship(self):
        before = self.npc.relationship_score
        self.npc.update_disposition("on_time")
        assert self.npc.relationship_score > before

    def test_negative_action_decreases_patience(self):
        before = self.npc.patience
        self.npc.update_disposition("task_failed")
        assert self.npc.patience < before

    def test_negative_action_decreases_relationship(self):
        before = self.npc.relationship_score
        self.npc.update_disposition("missed_deadline")
        assert self.npc.relationship_score < before

    def test_unknown_action_no_change(self):
        before_patience = self.npc.patience
        before_relationship = self.npc.relationship_score
        self.npc.update_disposition("unknown_event")
        assert self.npc.patience == before_patience
        assert self.npc.relationship_score == before_relationship

    def test_patience_capped_at_one(self):
        self.npc.patience = 1.0
        self.npc.update_disposition("task_completed")
        assert self.npc.patience <= 1.0

    def test_patience_floored_at_zero(self):
        self.npc.patience = 0.0
        self.npc.update_disposition("task_failed")
        assert self.npc.patience >= 0.0

    def test_relationship_score_capped_at_one(self):
        self.npc.relationship_score = 1.0
        self.npc.update_disposition("on_time")
        assert self.npc.relationship_score <= 1.0

    def test_relationship_score_floored_at_zero(self):
        self.npc.relationship_score = 0.0
        self.npc.update_disposition("forgot")
        assert self.npc.relationship_score >= 0.0

    def test_disposition_becomes_frustrated_at_low_patience(self):
        self.npc.patience = 0.1
        self.npc.update_disposition("task_failed")
        assert self.npc.disposition == NPCDisposition.FRUSTRATED

    def test_disposition_becomes_impatient_at_medium_low_patience(self):
        self.npc.patience = 0.35
        self.npc.update_disposition("task_failed")
        assert self.npc.disposition == NPCDisposition.IMPATIENT

    def test_disposition_becomes_supportive_at_high_relationship(self):
        self.npc.patience = 0.8
        self.npc.relationship_score = 0.75
        self.npc.update_disposition("task_completed")
        assert self.npc.disposition == NPCDisposition.SUPPORTIVE

    def test_disposition_becomes_understanding_at_good_relationship(self):
        self.npc.patience = 0.8
        self.npc.relationship_score = 0.6
        self.npc.update_disposition("task_completed")
        assert self.npc.disposition == NPCDisposition.UNDERSTANDING

    def test_all_positive_actions_accepted(self):
        for action in ("task_completed", "on_time", "communicated_delay", "asked_for_help"):
            npc = _TestNPC()
            before = npc.patience
            npc.update_disposition(action)
            assert npc.patience >= before

    def test_all_negative_actions_accepted(self):
        for action in ("task_failed", "missed_deadline", "forgot", "no_show"):
            npc = _TestNPC()
            before = npc.patience
            npc.update_disposition(action)
            assert npc.patience <= before


class TestGetSummary:
    def test_summary_contains_expected_keys(self):
        npc = _TestNPC(npc_id="test-id", name="Sam", role="coworker")
        summary = npc.get_summary()
        assert summary["npc_id"] == "test-id"
        assert summary["name"] == "Sam"
        assert summary["role"] == "coworker"
        assert "disposition" in summary
        assert "patience" in summary
        assert "relationship_score" in summary
        assert "total_interactions" in summary

    def test_total_interactions_starts_at_zero(self):
        npc = _TestNPC()
        assert npc.get_summary()["total_interactions"] == 0

    def test_disposition_in_summary_is_string(self):
        npc = _TestNPC()
        summary = npc.get_summary()
        assert isinstance(summary["disposition"], str)


class TestNPCReaction:
    def test_default_reaction(self):
        reaction = NPCReaction()
        assert reaction.npc_id == ""
        assert reaction.reaction_type == ""
        assert reaction.disposition == NPCDisposition.NEUTRAL

    def test_custom_reaction(self):
        reaction = NPCReaction(
            npc_id="n1",
            npc_name="Alice",
            reaction_type="behavioral",
            message="Good job!",
            emotional_impact_on_avatar=0.5,
            stress_impact=-0.1,
        )
        assert reaction.npc_name == "Alice"
        assert reaction.message == "Good job!"
        assert reaction.emotional_impact_on_avatar == pytest.approx(0.5)

    def test_to_dict_keys(self):
        reaction = NPCReaction(
            npc_id="n1",
            npc_name="Bob",
            reaction_type="verbal",
            disposition=NPCDisposition.FRUSTRATED,
            message="You are late.",
        )
        d = reaction.to_dict()
        assert d["npc_id"] == "n1"
        assert d["npc_name"] == "Bob"
        assert d["reaction_type"] == "verbal"
        assert d["disposition"] == "FRUSTRATED"
        assert d["message"] == "You are late."
        assert "timestamp" in d
        assert isinstance(d["timestamp"], str)

    def test_to_dict_consequence_none_by_default(self):
        reaction = NPCReaction()
        assert reaction.to_dict()["consequence"] is None

    def test_to_dict_with_consequence(self):
        reaction = NPCReaction(consequence={"penalty": "demotion"})
        assert reaction.to_dict()["consequence"] == {"penalty": "demotion"}


class TestReactToEvent:
    def test_concrete_react_called(self):
        npc = _TestNPC(npc_id="n99", name="TestBot")
        result = npc.react_to_event("task_failed", {"task": "report"})
        assert isinstance(result, NPCReaction)
        assert result.npc_id == "n99"
        assert result.reaction_type == "verbal"
