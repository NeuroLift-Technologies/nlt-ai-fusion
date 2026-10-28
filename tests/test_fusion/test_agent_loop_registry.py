"""Tests for the agent-loop agentId -> Avatar/Aide pair registry (AGENT-LOOP-003 F0)."""

import pytest

from src.aides.coaching.stay_alert_aide import StayAlertAide
from src.avatars.adhd_traits.stay_alert_avatar import StayAlertAvatar
from src.fusion.agent_loop_registry import (
    AgentRegistry,
    UnknownAgentError,
    build_default_registry,
)


def test_default_registry_serves_the_stay_alert_pair_only():
    registry = build_default_registry()

    assert registry.agent_ids == ("stay_alert_001",)
    pair = registry.get("stay_alert_001")
    assert isinstance(pair.avatar, StayAlertAvatar)
    assert isinstance(pair.aide, StayAlertAide)
    assert pair.agent_id == pair.avatar.avatar_id == "stay_alert_001"
    assert pair.aide.aide_id == "stay_alert_aide_001"


def test_pair_is_bound_through_its_session_orchestrator():
    pair = build_default_registry().get("stay_alert_001")

    assert pair.orchestrator.avatar is pair.avatar
    assert pair.orchestrator.aide is pair.aide
    assert pair.avatar.channel is pair.orchestrator.channel


def test_each_registry_owns_its_own_pairs():
    first = build_default_registry().get("stay_alert_001")
    second = build_default_registry().get("stay_alert_001")
    assert first.avatar is not second.avatar


def test_unknown_agent_fails_closed_without_creating_one():
    registry = build_default_registry()

    with pytest.raises(UnknownAgentError):
        registry.get("__local_avatar__")
    assert "__local_avatar__" not in registry
    assert registry.agent_ids == ("stay_alert_001",)


def test_duplicate_and_empty_ids_are_refused():
    registry = AgentRegistry()
    registry.register(StayAlertAvatar("stay_alert_001", {}), StayAlertAide("aide_a", {}))

    with pytest.raises(ValueError):
        registry.register(StayAlertAvatar("stay_alert_001", {}), StayAlertAide("aide_b", {}))
    with pytest.raises(ValueError):
        registry.register(StayAlertAvatar(" ", {}), StayAlertAide("aide_c", {}))
    assert registry.agent_ids == ("stay_alert_001",)
