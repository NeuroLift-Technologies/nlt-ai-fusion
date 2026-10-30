"""
Tests for Scenario and ScenarioLibrary (src/simulation/environment/scenarios.py).

Covers the 13 pre-defined scenarios and the library query helpers.
"""

from datetime import timedelta

import pytest

from src.simulation.environment.scenarios import (
    Scenario,
    ScenarioCategory,
    ScenarioLibrary,
)


class TestScenario:
    """Tests for Scenario construction and serialization."""

    def test_to_dict_roundtrip(self) -> None:
        """to_dict() serializes all fields, converting duration to seconds."""
        s = Scenario(
            scenario_id="test_1",
            name="Test Scenario",
            description="A test",
            category=ScenarioCategory.WORKPLACE,
            task_type="test_task",
            expected_duration=timedelta(minutes=30),
            complexity="medium",
            aversiveness=0.5,
            requires_sustained_focus=True,
            cognitive_demand=0.6,
            base_success_rate=0.7,
            context={"key": "value"},
        )
        d = s.to_dict()
        assert d["scenario_id"] == "test_1"
        assert d["name"] == "Test Scenario"
        assert d["category"] == "workplace"
        assert d["task_type"] == "test_task"
        assert d["expected_duration"] == 1800.0
        assert d["complexity"] == "medium"
        assert d["aversiveness"] == 0.5
        assert d["requires_sustained_focus"] is True
        assert d["cognitive_demand"] == 0.6
        assert d["base_success_rate"] == 0.7
        assert d["context"]["key"] == "value"

    def test_category_enum(self) -> None:
        """Category enum values match the documented category strings."""
        assert ScenarioCategory.WORKPLACE.value == "workplace"
        assert ScenarioCategory.PERSONAL.value == "personal"
        assert ScenarioCategory.SOCIAL.value == "social"
        assert ScenarioCategory.ACADEMIC.value == "academic"


class TestScenarioLibraryWorkplace:
    """Tests for the workplace scenario set (5 scenarios)."""

    def test_workplace_count_and_ids(self) -> None:
        """Workplace library returns exactly the five wp_* scenario IDs."""
        scenarios = ScenarioLibrary.get_workplace_scenarios()
        assert len(scenarios) == 5
        ids = {s.scenario_id for s in scenarios}
        assert ids == {"wp_1", "wp_2", "wp_3", "wp_4", "wp_5"}

    def test_workplace_fields(self) -> None:
        """Every workplace scenario is categorized and within valid ranges."""
        scenarios = ScenarioLibrary.get_workplace_scenarios()
        for s in scenarios:
            assert s.category == ScenarioCategory.WORKPLACE
            assert s.task_type
            assert s.expected_duration.total_seconds() > 0
            assert 0.0 <= s.cognitive_demand <= 1.0
            assert 0.0 <= s.base_success_rate <= 1.0
            assert isinstance(s.context, dict)

    def test_workplace_specific_context(self) -> None:
        """Scenario-specific context keys carry their expected values."""
        by_id = {s.scenario_id: s for s in ScenarioLibrary.get_workplace_scenarios()}
        assert by_id["wp_1"].context["email_count"] == 20
        assert by_id["wp_2"].context["word_count"] == 2000
        assert by_id["wp_5"].context["urgency"] == "critical"


class TestScenarioLibraryPersonal:
    """Tests for the personal-life scenario set (4 scenarios)."""

    def test_personal_count_and_ids(self) -> None:
        """Personal library returns exactly the four pers_* scenario IDs."""
        scenarios = ScenarioLibrary.get_personal_scenarios()
        assert len(scenarios) == 4
        ids = {s.scenario_id for s in scenarios}
        assert ids == {"pers_1", "pers_2", "pers_3", "pers_4"}

    def test_personal_fields(self) -> None:
        """Every personal scenario is categorized with a positive duration."""
        for s in ScenarioLibrary.get_personal_scenarios():
            assert s.category == ScenarioCategory.PERSONAL
            assert s.task_type
            assert s.expected_duration.total_seconds() > 0


class TestScenarioLibrarySocial:
    """Tests for the social interaction scenario set (2 scenarios)."""

    def test_social_count_and_ids(self) -> None:
        """Social library returns exactly the two soc_* scenario IDs."""
        scenarios = ScenarioLibrary.get_social_scenarios()
        assert len(scenarios) == 2
        ids = {s.scenario_id for s in scenarios}
        assert ids == {"soc_1", "soc_2"}

    def test_social_aversiveness(self) -> None:
        """Social scenarios keep aversiveness within the 0-1 range."""
        scenarios = ScenarioLibrary.get_social_scenarios()
        for s in scenarios:
            assert 0.0 <= s.aversiveness <= 1.0


class TestScenarioLibraryAcademic:
    """Tests for the academic/learning scenario set (2 scenarios)."""

    def test_academic_count_and_ids(self) -> None:
        """Academic library returns exactly the two acad_* scenario IDs."""
        scenarios = ScenarioLibrary.get_academic_scenarios()
        assert len(scenarios) == 2
        ids = {s.scenario_id for s in scenarios}
        assert ids == {"acad_1", "acad_2"}

    def test_academic_cognitive_demand_high(self) -> None:
        """Academic scenarios demand high cognitive load (>= 0.8)."""
        for s in ScenarioLibrary.get_academic_scenarios():
            assert s.cognitive_demand >= 0.8


class TestScenarioLibraryQueries:
    """Tests for ScenarioLibrary lookup and aggregate query helpers."""

    def test_get_all_scenarios(self) -> None:
        """get_all_scenarios() returns 13 scenarios with unique IDs."""
        all_scenarios = ScenarioLibrary.get_all_scenarios()
        assert len(all_scenarios) == 13
        # All have unique IDs
        ids = [s.scenario_id for s in all_scenarios]
        assert len(ids) == len(set(ids))

    def test_get_by_category(self) -> None:
        """Per-category counts match the library composition."""
        assert len(ScenarioLibrary.get_scenarios_by_category(ScenarioCategory.WORKPLACE)) == 5
        assert len(ScenarioLibrary.get_scenarios_by_category(ScenarioCategory.PERSONAL)) == 4
        assert len(ScenarioLibrary.get_scenarios_by_category(ScenarioCategory.SOCIAL)) == 2
        assert len(ScenarioLibrary.get_scenarios_by_category(ScenarioCategory.ACADEMIC)) == 2

    def test_get_scenario_by_id_success(self) -> None:
        """Known IDs resolve to their named scenarios across categories."""
        s = ScenarioLibrary.get_scenario_by_id("wp_3")
        assert s.name == "Meeting Participation"
        assert s.category == ScenarioCategory.WORKPLACE

        s2 = ScenarioLibrary.get_scenario_by_id("pers_2")
        assert s2.name == "Grocery Shopping"

        s3 = ScenarioLibrary.get_scenario_by_id("soc_1")
        assert s3.task_type == "phone_call"

        s4 = ScenarioLibrary.get_scenario_by_id("acad_1")
        assert s4.task_type == "studying"

    def test_get_scenario_by_id_failure(self) -> None:
        """Unknown IDs raise ValueError with a 'not found' message."""
        with pytest.raises(ValueError, match="not found"):
            ScenarioLibrary.get_scenario_by_id("nonexistent_id")

    def test_to_dict_all_scenarios(self) -> None:
        """to_dict() exposes required keys and a float duration for all."""
        for s in ScenarioLibrary.get_all_scenarios():
            d = s.to_dict()
            assert "scenario_id" in d
            assert "category" in d
            assert "base_success_rate" in d
            assert "context" in d
            assert isinstance(d["expected_duration"], float)

    def test_scenarios_have_varied_aversiveness(self) -> None:
        """Aversiveness spans the design range (>= 0.8 high, <= 0.3 low)."""
        all_scenarios = ScenarioLibrary.get_all_scenarios()
        aversiveness_values = [s.aversiveness for s in all_scenarios]
        # Should have range, not all same
        assert max(aversiveness_values) > min(aversiveness_values)
        assert max(aversiveness_values) >= 0.8
        assert min(aversiveness_values) <= 0.3

    def test_scenarios_cover_all_complexities(self) -> None:
        """The library collectively covers low, medium, and high complexity."""
        complexities = {s.complexity for s in ScenarioLibrary.get_all_scenarios()}
        assert complexities == {"low", "medium", "high"}

    def test_workplace_and_academic_require_focus(self) -> None:
        """All workplace and academic scenarios require sustained focus."""
        for s in ScenarioLibrary.get_workplace_scenarios():
            assert s.requires_sustained_focus is True
        for s in ScenarioLibrary.get_academic_scenarios():
            assert s.requires_sustained_focus is True

    def test_personal_mixed_focus(self) -> None:
        """Personal scenarios mix focus-required and non-focus tasks."""
        personal = ScenarioLibrary.get_personal_scenarios()
        focus_true = sum(1 for s in personal if s.requires_sustained_focus)
        focus_false = sum(1 for s in personal if not s.requires_sustained_focus)
        assert focus_true > 0
        assert focus_false > 0
