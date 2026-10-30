"""
Tests for schedule components: FurnitureComponent, RoomComponent,
NeedsComponent, ScheduleComponent.
"""
import pytest
from src.simulation.environment.ecs import Entity, Position
from src.simulation.environment.schedule import (
    FurnitureType, FurnitureComponent, NeedsComponent, NeedType,
    RoomComponent, ScheduleComponent,
)


class TestFurnitureType:
    def test_all_types_present(self):
        expected = {"bed", "fridge", "stove", "counter", "table", "couch", "computer", "toilet", "shower"}
        assert {ft.value for ft in FurnitureType} == expected

    def test_is_str_enum(self):
        assert isinstance(FurnitureType.BED, str)


class TestFurnitureComponent:
    def test_init(self):
        comp = FurnitureComponent(FurnitureType.BED)
        assert comp.furniture_type == FurnitureType.BED

    def test_to_dict(self):
        comp = FurnitureComponent(FurnitureType.COUCH)
        d = comp.to_dict()
        assert d["furniture_type"] == "couch"


class TestRoomComponent:
    def test_init(self):
        comp = RoomComponent("kitchen")
        assert comp.room_name == "kitchen"

    def test_to_dict(self):
        comp = RoomComponent("bedroom")
        d = comp.to_dict()
        assert d["room_name"] == "bedroom"


class TestNeedsComponent:
    def test_init_defaults(self):
        comp = NeedsComponent()
        assert len(comp.needs) == 5
        for need, val in comp.needs.items():
            assert val == 100.0

    def test_init_custom_value(self):
        comp = NeedsComponent(initial_value=50.0)
        for need, val in comp.needs.items():
            assert val == 50.0

    def test_init_clamps_above_100(self):
        comp = NeedsComponent(initial_value=150.0)
        for need, val in comp.needs.items():
            assert val == 100.0

    def test_init_clamps_below_0(self):
        comp = NeedsComponent(initial_value=-10.0)
        for need, val in comp.needs.items():
            assert val == 0.0

    def test_decay(self):
        comp = NeedsComponent(initial_value=100.0)
        comp.decay(1.0)
        for need, val in comp.needs.items():
            assert val < 100.0

    def test_decay_does_not_go_below_zero(self):
        comp = NeedsComponent(initial_value=0.0)
        comp.decay(100.0)
        for need, val in comp.needs.items():
            assert val == 0.0

    def test_recover(self):
        comp = NeedsComponent(initial_value=0.0)
        comp.recover("sleep")
        assert comp.needs[NeedType.ENERGY] == 8.0

    def test_recover_unknown_affordance_no_change(self):
        comp = NeedsComponent()
        comp.recover("unknown_thing")
        for need, val in comp.needs.items():
            assert val == 100.0

    def test_recover_caps_at_100(self):
        comp = NeedsComponent(initial_value=98.0)
        comp.recover("sleep")
        assert comp.needs[NeedType.ENERGY] == 100.0

    def test_as_dict(self):
        comp = NeedsComponent()
        d = comp.as_dict()
        assert len(d) == 5
        assert d["hunger"] == 100.0

    def test_to_dict_from_dict_roundtrip(self):
        comp = NeedsComponent(initial_value=50.0)
        comp.decay(2.0)
        d = comp.to_dict()
        comp2 = NeedsComponent.from_dict(d)
        assert comp2.as_dict() == comp.as_dict()


class TestScheduleComponent:
    def test_init_defaults(self):
        comp = ScheduleComponent()
        assert comp.current_activity is None
        assert comp.target_entity_id is None
        assert comp.intent_progress == 0.0
        assert comp.weekend is False

    def test_resolve_activity_weekday(self):
        comp = ScheduleComponent()
        assert comp.resolve_activity(10, False) == "work"

    def test_resolve_activity_weekend(self):
        comp = ScheduleComponent()
        assert comp.resolve_activity(10, True) == "free_time"

    def test_resolve_activity_unknown_hour(self):
        comp = ScheduleComponent()
        # All hours 0-23 are covered, so this should always return something
        result = comp.resolve_activity(23, False)
        assert result is not None

    def test_update_for_time_changes_activity(self):
        comp = ScheduleComponent()
        comp.update_for_time(10, False)
        assert comp.current_activity == "work"
        assert comp.weekend is False

    def test_update_for_time_weekend(self):
        comp = ScheduleComponent()
        comp.update_for_time(10, True)
        assert comp.current_activity == "free_time"
        assert comp.weekend is True

    def test_update_for_time_no_change_keeps_activity(self):
        comp = ScheduleComponent()
        comp.update_for_time(10, False)
        assert comp.current_activity == "work"
        comp.update_for_time(10, False)
        assert comp.current_activity == "work"

    def test_to_dict(self):
        comp = ScheduleComponent()
        comp.update_for_time(10, False)
        d = comp.to_dict()
        assert "current_activity" in d
        assert "weekend" in d
        assert "weekday_schedule" in d
        assert "weekend_schedule" in d

    def test_to_dict_from_dict_roundtrip(self):
        comp = ScheduleComponent()
        comp.update_for_time(14, False)
        d = comp.to_dict()
        comp2 = ScheduleComponent.from_dict(d)
        assert comp2.current_activity == comp.current_activity
        assert comp2.weekend == comp.weekend
