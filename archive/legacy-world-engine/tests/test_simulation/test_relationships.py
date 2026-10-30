"""
Tests for the relationship system: RelationshipComponent and
RelationshipManager.
"""
import pytest
from src.simulation.environment.relationships import (
    RelationshipComponent, RelationshipManager,
)


class TestRelationshipComponent:
    def test_init(self):
        comp = RelationshipComponent("sim_a", "sim_b")
        assert comp.sim_a == "sim_a"
        assert comp.sim_b == "sim_b"
        assert comp.friendship == 0.0
        assert comp.romance == 0.0
        assert comp.familiarity == 0.0
        assert comp.interaction_count == 0

    def test_other_sim_returns_partner(self):
        comp = RelationshipComponent("sim_a", "sim_b")
        assert comp.other_sim("sim_a") == "sim_b"
        assert comp.other_sim("sim_b") == "sim_a"

    def test_other_sim_unknown_returns_none(self):
        comp = RelationshipComponent("sim_a", "sim_b")
        assert comp.other_sim("sim_c") is None

    def test_involves(self):
        comp = RelationshipComponent("sim_a", "sim_b")
        assert comp.involves("sim_a") is True
        assert comp.involves("sim_b") is True
        assert comp.involves("sim_c") is False

    def test_interact_increases_metrics(self):
        comp = RelationshipComponent("sim_a", "sim_b")
        comp.interact()
        assert comp.interaction_count == 1
        assert comp.familiarity == 8.0
        assert comp.friendship == 5.0

    def test_interact_romantic(self):
        comp = RelationshipComponent("sim_a", "sim_b")
        comp.interact("romantic")
        assert comp.romance == 6.0
        assert comp.friendship == 5.0
        assert comp.familiarity == 8.0

    def test_interact_caps_metrics(self):
        comp = RelationshipComponent("sim_a", "sim_b")
        for _ in range(100):
            comp.interact()
        assert comp.friendship == 100.0
        assert comp.familiarity == 100.0

    def test_to_dict_from_dict_roundtrip(self):
        comp = RelationshipComponent("sim_a", "sim_b")
        comp.interact()
        comp.interact("romantic")
        d = comp.to_dict()
        comp2 = RelationshipComponent.from_dict(d)
        assert comp2.sim_a == "sim_a"
        assert comp2.sim_b == "sim_b"
        assert comp2.friendship == comp.friendship
        assert comp2.romance == comp.romance
        assert comp2.familiarity == comp.familiarity
        assert comp2.interaction_count == comp.interaction_count


class TestRelationshipManager:
    def test_get_or_create_new(self):
        rm = RelationshipManager()
        comp = rm.get_or_create("a", "b")
        assert isinstance(comp, RelationshipComponent)
        assert comp.friendship == 0.0

    def test_get_or_create_existing(self):
        rm = RelationshipManager()
        comp1 = rm.get_or_create("a", "b")
        comp2 = rm.get_or_create("a", "b")
        assert comp1 is comp2

    def test_get_or_create_reversed_key(self):
        """Key order shouldn't matter."""
        rm = RelationshipManager()
        comp1 = rm.get_or_create("a", "b")
        comp2 = rm.get_or_create("b", "a")
        assert comp1 is comp2

    def test_get_or_create_self_raises(self):
        rm = RelationshipManager()
        with pytest.raises(ValueError):
            rm.get_or_create("a", "a")

    def test_get_existing(self):
        rm = RelationshipManager()
        rm.get_or_create("a", "b")
        comp = rm.get("a", "b")
        assert comp is not None
        assert comp.other_sim("a") == "b"

    def test_get_nonexistent(self):
        rm = RelationshipManager()
        assert rm.get("a", "b") is None

    def test_get_all_for_sim(self):
        rm = RelationshipManager()
        rm.get_or_create("a", "b")
        rm.get_or_create("a", "c")
        rm.get_or_create("b", "c")
        comps = rm.get_all_for_sim("a")
        assert len(comps) == 2
        ids = {comp.other_sim("a") for comp in comps}
        assert ids == {"b", "c"}

    def test_get_all_for_sim_no_relationships(self):
        rm = RelationshipManager()
        assert rm.get_all_for_sim("a") == []

    def test_all_relationships(self):
        rm = RelationshipManager()
        rm.get_or_create("a", "b")
        rm.get_or_create("a", "c")
        assert len(rm.all_relationships()) == 2

    def test_to_dict_from_dict_roundtrip(self):
        rm = RelationshipManager()
        rm.get_or_create("a", "b").interact()
        rm.get_or_create("a", "c").interact("romantic")
        d = rm.to_dict()
        rm2 = RelationshipManager()
        rm2.from_dict(d)
        comps = rm2.get_all_for_sim("a")
        assert len(comps) == 2
        names = {c.other_sim("a") for c in comps}
        assert names == {"b", "c"}
