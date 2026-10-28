"""Focused contract assertions for the async loopback HTTP endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.fusion.agent_loop import AgentLoopProtocolError
from src.fusion.agent_loop_http import _fallback_decide, create_app
from src.fusion.agent_loop_registry import AgentRegistry


def _perception(tick: int = 42, agent_id: str = "stay_alert_001") -> dict:
    return {
        "protocolVersion": "nlt.agent-loop.v1",
        "messageType": "perception",
        "messageId": f"obs-{tick}-{agent_id}",
        "agentId": agent_id,
        "tick": tick,
        "scene": {"id": "workplace_1", "kind": "interior"},
        "self": {
            "position": {"x": 1.0, "y": 0.0, "z": 2.0},
            "velocity": {"x": 0.0, "y": 0.0, "z": 0.0},
        },
        "visibleEntities": [
            {
                "id": "desk_1",
                "kind": "place",
                "position": {"x": 2.0, "y": 0.0, "z": 2.0},
                "affordances": ["approach", "use", "sit"],
                "occupied": False,
            }
        ],
    }


def _intent_decide(observation):
    """Correlated intent targeting the only visible entity."""
    return {
        "protocolVersion": "nlt.agent-loop.v1",
        "messageType": "intent",
        "messageId": "intent-42-stay-alert-001",
        "agentId": observation["agentId"],
        "observedTick": observation["tick"],
        "verb": "approach",
        "targetId": "desk_1",
    }


def test_valid_perception_returns_correlated_intent():
    client = TestClient(create_app(decide=_intent_decide))
    response = client.post("/agent-loop/perception", json=_perception())
    assert response.status_code == 200
    intent = response.json()
    assert intent["agentId"] == "stay_alert_001"
    assert intent["observedTick"] == 42
    assert intent["verb"] == "approach"
    assert intent["targetId"] == "desk_1"
    # Intent carries no physical-write field.
    assert "position" not in intent and "velocity" not in intent


def test_malformed_perception_fails_closed_with_reason():
    client = TestClient(create_app(decide=_intent_decide))
    response = client.post(
        "/agent-loop/perception",
        json={"protocolVersion": "nlt.agent-loop.v1", "messageType": "perception"},
    )
    assert response.status_code == 422
    assert "error" in response.json()


def test_invalid_json_fails_closed():
    client = TestClient(create_app(decide=_intent_decide))
    response = client.post(
        "/agent-loop/perception",
        content=b"not json at all",
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 400


def test_decision_source_error_fails_closed():
    def exploding(observation):
        raise RuntimeError("model exploded")

    client = TestClient(create_app(decide=exploding))
    response = client.post("/agent-loop/perception", json=_perception())
    assert response.status_code == 503
    assert response.json()["error"] == "decision source unavailable"
    assert "model exploded" not in response.text


def test_stale_or_mismatched_intent_rejected_by_seam():
    """The injected decide returns a stale tick → validate_intent raises → 422."""

    def stale_decide(observation):
        intent = _intent_decide(observation)
        intent["observedTick"] = observation["tick"] - 7
        return intent

    client = TestClient(create_app(decide=stale_decide))
    response = client.post("/agent-loop/perception", json=_perception())
    assert response.status_code == 422
    assert response.json()["error"] == "decision did not satisfy the agent-loop contract"


def test_target_outside_perception_rejected_by_seam():
    def hidden_target_decide(observation):
        intent = _intent_decide(observation)
        intent["targetId"] = "hidden_object"
        return intent

    client = TestClient(create_app(decide=hidden_target_decide))
    response = client.post("/agent-loop/perception", json=_perception())
    assert response.status_code == 422
    assert response.json()["error"] == "decision did not satisfy the agent-loop contract"
    assert "hidden_object" not in response.text


def test_protocol_error_type_used_by_seam():
    """Guard the import the endpoint relies on."""
    assert issubclass(AgentLoopProtocolError, ValueError)


def test_fallback_only_approaches_an_available_target_with_affordance():
    observation = _perception()
    intent = _fallback_decide(observation)
    assert intent["verb"] == "approach"
    assert intent["targetId"] == "desk_1"

    observation["visibleEntities"][0]["affordances"] = ["use", "sit"]
    intent = _fallback_decide(observation)
    assert intent["verb"] == "wait"


def test_unregistered_agent_fails_closed_before_any_decision():
    calls = []

    def recording_decide(observation):
        calls.append(observation)
        return _intent_decide(observation)

    client = TestClient(create_app(decide=recording_decide))
    # The engine's internal key for its local avatar is not a roster id.
    response = client.post(
        "/agent-loop/perception", json=_perception(agent_id="__local_avatar__")
    )
    assert response.status_code == 404
    assert response.json()["error"] == "agent is not registered"
    assert calls == []


def test_injected_registry_decides_which_agents_are_served():
    client = TestClient(create_app(decide=_intent_decide, registry=AgentRegistry()))
    response = client.post("/agent-loop/perception", json=_perception())
    assert response.status_code == 404
