"""
Tests for the extended WorldEngine: WorldEngineConfig, time_manager,
relationship_manager, save/load_state, and Registry additions.
"""
import json
from datetime import datetime, timedelta

import pytest

from src.simulation.environment import (
    WorldEngine, WorldEngineConfig, SimulationState,
    TimeManager, RelationshipManager,
    Entity, Position, Interactable, AgentController,
    FurnitureComponent, FurnitureType, RoomComponent,
    NeedsComponent, NeedType, ScheduleComponent,
)


class TestWorldEngineConfig:
    def test_defaults(self):
        config = WorldEngineConfig()
        assert config.grid_width == 100
        assert config.grid_height == 100
        assert config.seconds_per_tick == 1.0
        assert config.time_speed_multiplier == 1.0

    def test_custom(self):
        config = WorldEngineConfig(grid_width=30, grid_height=40, seconds_per_tick=0.5, time_speed_multiplier=5.0)
        assert config.grid_width == 30
        assert config.grid_height == 40
        assert config.seconds_per_tick == 0.5
        assert config.time_speed_multiplier == 5.0


class TestWorldEngineInit:
    def test_no_args(self):
        engine = WorldEngine()
        assert engine.current_state == SimulationState.RUNNING
        assert engine.config.grid_width == 100
        assert engine.time_manager is not None
        assert engine.relationship_manager is not None

    def test_dict_config(self):
        engine = WorldEngine(config={"grid_width": 50, "grid_height": 50, "seconds_per_tick": 0.5})
        assert engine.config.grid_width == 50
        assert engine.config.grid_height == 50
        assert engine.config.seconds_per_tick == 0.5

    def test_dataclass_config(self):
        config = WorldEngineConfig(grid_width=30, seconds_per_tick=2.0)
        engine = WorldEngine(config=config)
        assert engine.config.grid_width == 30
        assert engine.config.seconds_per_tick == 2.0

    def test_custom_time_manager(self):
        tm = TimeManager(start_day=5, start_hour=14, speed_multiplier=5.0)
        engine = WorldEngine(time_manager=tm)
        assert engine.time_manager is tm
        assert engine.time_manager.day == 5

    def test_invalid_config_type_raises(self):
        with pytest.raises(TypeError):
            WorldEngine(config="not a config")


class TestWorldEngineTickWithTimeManager:
    def test_run_step_advances_time_manager(self):
        tm = TimeManager(start_day=1, start_hour=10, start_minute=0, speed_multiplier=1.0)
        engine = WorldEngine(config={"seconds_per_tick": 1.0}, time_manager=tm)
        engine.run_simulation_step()
        # 1 tick = 1 second real time * 1.0 speed = 1 game minute
        assert engine.time_manager.minute == 1

    def test_run_step_advances_time_fast_speed(self):
        tm = TimeManager(start_day=1, start_hour=10, start_minute=0, speed_multiplier=5.0)
        engine = WorldEngine(config={"seconds_per_tick": 1.0}, time_manager=tm)
        engine.run_simulation_step()
        # 1 tick = 1 second * 5.0 speed = 5 game minutes
        assert engine.time_manager.minute == 5

    def test_run_step_advances_time_ultra_speed(self):
        tm = TimeManager(start_day=1, start_hour=10, start_minute=0, speed_multiplier=20.0)
        engine = WorldEngine(config={"seconds_per_tick": 1.0}, time_manager=tm)
        engine.run_simulation_step()
        # 1 tick = 1 second * 20.0 speed = 20 game minutes
        assert engine.time_manager.hour == 10
        assert engine.time_manager.minute == 20

    def test_paused_engine_does_not_advance(self):
        tm = TimeManager(start_hour=10)
        engine = WorldEngine(time_manager=tm)
        engine.current_state = SimulationState.PAUSED
        result = engine.run_simulation_step()
        assert result is False
        assert engine.tick_count == 0


class TestRegistryExtensions:
    def test_get_entities(self):
        engine = WorldEngine()
        e1 = engine.spawn_entity()
        e2 = engine.spawn_entity()
        entities = engine.registry.get_entities()
        assert e1 in entities
        assert e2 in entities
        assert len(entities) == 2

    def test_get_component_types(self):
        engine = WorldEngine()
        entity = engine.spawn_entity()
        engine.registry.add_component(entity, Position(1, 2))
        engine.registry.add_component(entity, Interactable(["examine"]))
        types = engine.registry.get_component_types()
        type_names = {t.__name__ for t in types}
        assert "Position" in type_names
        assert "Interactable" in type_names


class TestWorldEngineSaveLoad:
    def test_save_state_returns_valid_json(self):
        engine = WorldEngine()
        state_json = engine.save_state()
        state = json.loads(state_json)
        assert "simulation_id" in state
        assert "current_state" in state
        assert "simulation_time" in state
        assert "tick_count" in state
        assert "time_manager" in state
        assert "config" in state
        assert "entities" in state
        assert "relationships" in state

    def test_save_load_roundtrip(self):
        engine = WorldEngine()
        entity = engine.spawn_entity()
        engine.registry.add_component(entity, Position(5, 10, 0))
        engine.registry.add_component(entity, Interactable(["use"]))
        engine.run_simulation_step()
        saved_json = engine.save_state()

        engine2 = WorldEngine()
        engine2.load_state(saved_json)

        assert engine2.tick_count == engine.tick_count
        assert engine2.time_manager.day == engine.time_manager.day
        assert engine2.time_manager.hour == engine.time_manager.hour

        entities = engine2.registry.get_entities()
        assert len(entities) == len(engine.registry.get_entities())
        # Find the entity with Position
        pos = engine2.registry.get_component(entities[0], Position)
        if pos is not None:
            assert pos.x == 5
            assert pos.y == 10

    def test_save_load_preserves_relationships(self):
        engine = WorldEngine()
        rm = engine.relationship_manager
        comp = rm.get_or_create("sim_a", "sim_b")
        comp.interact("romantic")
        comp.interact()

        saved_json = engine.save_state()
        engine2 = WorldEngine()
        engine2.load_state(saved_json)

        comps = engine2.relationship_manager.get_all_for_sim("sim_a")
        assert len(comps) == 1
        assert comps[0].romance == comp.romance
        assert comps[0].interaction_count == comp.interaction_count

    def test_load_empty_state_raises(self):
        engine = WorldEngine()
        with pytest.raises(ValueError):
            engine.load_state("")

    def test_load_invalid_json_raises(self):
        engine = WorldEngine()
        with pytest.raises(ValueError):
            engine.load_state("not valid json")

    def test_save_load_preserves_schedule_needs(self):
        engine = WorldEngine()
        entity = engine.spawn_entity()
        engine.registry.add_component(entity, NeedsComponent(initial_value=50.0))
        sched = ScheduleComponent()
        sched.update_for_time(10, False)
        engine.registry.add_component(entity, sched)

        saved_json = engine.save_state()
        engine2 = WorldEngine()
        engine2.load_state(saved_json)

        entities = engine2.registry.get_entities()
        needs = engine2.registry.get_component(entities[0], NeedsComponent)
        assert needs is not None
        assert needs.needs[NeedType.HUNGER] == 50.0

        sched2 = engine2.registry.get_component(entities[0], ScheduleComponent)
        assert sched2 is not None
        assert sched2.current_activity == "work"


class TestWorldEngineRelationshipManager:
    def test_relationship_manager_exists(self):
        engine = WorldEngine()
        assert isinstance(engine.relationship_manager, RelationshipManager)

    def test_get_or_create_relationship(self):
        engine = WorldEngine()
        comp = engine.relationship_manager.get_or_create("a", "b")
        assert comp.other_sim("a") == "b"
