"""Integration tests for the AI-Fusion Space runtime.

These run the composed app the Space actually serves — health, governance-gated
fusion routes and the mounted nlt.agent-loop.v1 seam — with no network and no
model files, which is the default deployment shape.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# The Space image lays the repository out as /app (src/ + app/); tests run from the
# repository root, so point sys.path at src/'s parent.
_SPACE_ROOT = Path(__file__).resolve().parents[1]
_REPO_ROOT = _SPACE_ROOT.parents[1]
for candidate in (_SPACE_ROOT, _REPO_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from app.main import create_runtime_app  # noqa: E402
from app.settings import Settings  # noqa: E402

CAPS = "fusion.read,fusion.fuse,fusion.session.run,runtime.info"


def _settings(tmp_path: Path, *, mode: str = "enforce") -> Settings:
    return Settings(
        environment="test",
        port=7860,
        allowed_origins=["https://app.neuroliftsolutions.com"],
        governance_mode=mode,
        governance_version="ORG-DEV-OTOI-1.0.3",
        artifacts_dir=tmp_path,
        models_dir=tmp_path / "models",
    )


def _headers(**overrides: str) -> dict[str, str]:
    base = {
        "X-NLT-Agent-Id": "api-platform",
        "X-NLT-Session-Id": "sess-1234",
        "X-NLT-Provenance": "nlt-api/1.0.0",
        "X-NLT-Governance-Version": "ORG-DEV-OTOI-1.0.3",
        "X-NLT-Capabilities": CAPS,
    }
    base.update(overrides)
    return base


@pytest.fixture
def client(tmp_path: Path):
    app = create_runtime_app(settings=_settings(tmp_path))
    with TestClient(app) as c:
        yield c


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


class TestHealth:
    def test_liveness_is_dependency_free(self, client):
        body = client.get("/health").json()
        assert body["status"] == "ok"
        assert body["service"] == "ai-fusion-runtime"

    def test_readiness_reports_loaded_runtime(self, client):
        response = client.get("/readyz")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["model_kind"] == "baseline"
        assert body["registered_agents"] == ["stay_alert_001"]
        assert body["protocol_version"].startswith("nlt.agent-loop.")

    def test_readiness_reports_unwritable_artifacts(self, tmp_path):
        settings = _settings(tmp_path)
        # A file where the directory should be: mkdir fails, readiness must say so.
        blocker = tmp_path / "blocked"
        blocker.write_text("not a directory", encoding="utf-8")
        settings = Settings(**{**settings.__dict__, "artifacts_dir": blocker})
        with TestClient(create_runtime_app(settings=settings)) as c:
            response = c.get("/readyz")
        assert response.status_code == 503
        assert any("not writable" in reason for reason in response.json()["reasons"])


class TestGovernance:
    def test_missing_context_is_denied_even_though_the_request_arrived(self, client):
        response = client.get("/v1/fusion/agents")
        assert response.status_code == 403
        assert response.json()["detail"]["error"] == "governance_context_missing"

    def test_identity_without_capability_is_denied(self, client):
        response = client.get(
            "/v1/fusion/agents",
            headers=_headers(**{"X-NLT-Capabilities": "runtime.info"}),
        )
        assert response.status_code == 403
        detail = response.json()["detail"]
        assert detail["error"] == "capability_not_granted"
        assert "fusion.read" in detail["reason"]

    def test_unsupported_governance_version_is_denied(self, client):
        response = client.get(
            "/v1/fusion/agents",
            headers=_headers(**{"X-NLT-Governance-Version": "ORG-DEV-OTOI-0.9.0"}),
        )
        assert response.status_code == 403
        assert response.json()["detail"]["error"] == "governance_version_unsupported"

    def test_granted_context_is_accepted_and_echoed(self, client):
        response = client.get("/v1/fusion/agents", headers=_headers())
        assert response.status_code == 200
        body = response.json()
        assert body["governance_enforced"] is True
        assert body["governance"]["session_id"] == "sess-1234"
        assert body["governance"]["capabilities"] == [
            "fusion.fuse",
            "fusion.read",
            "fusion.session.run",
            "runtime.info",
        ]

    def test_permissive_mode_never_claims_authorization(self, tmp_path):
        with TestClient(create_runtime_app(settings=_settings(tmp_path, mode="permissive"))) as c:
            body = c.get("/v1/fusion/agents").json()
        assert body["governance_enforced"] is False
        assert body["governance"]["agent_id"] == ""


class TestFusionRoutes:
    def test_lists_registered_pairs(self, client):
        body = client.get("/v1/fusion/agents", headers=_headers()).json()
        assert body["count"] == 1
        assert body["agents"][0]["agent_id"] == "stay_alert_001"

    def test_unknown_agent_fails_closed(self, client):
        response = client.post(
            "/v1/fusion/readiness", json={"agent_id": "ghost_999"}, headers=_headers()
        )
        assert response.status_code == 404
        assert response.json()["detail"]["error"] == "agent_not_registered"

    def test_readiness_returns_dimensions(self, client):
        response = client.post(
            "/v1/fusion/readiness", json={"agent_id": "stay_alert_001"}, headers=_headers()
        )
        assert response.status_code == 200
        readiness = response.json()["readiness"]
        assert 0.0 <= readiness["overall_score"] <= 1.0
        assert readiness["dimensions"]
        assert "ready" in readiness

    def test_fusion_attempt_is_gated_on_readiness(self, client):
        response = client.post(
            "/v1/fusion/attempt", json={"agent_id": "stay_alert_001"}, headers=_headers()
        )
        assert response.status_code == 200
        body = response.json()
        # A freshly constructed pair has no experience, so it must not fuse.
        assert body["success"] is False
        assert "Not ready" in (body["failure_reason"] or "")
        assert body["readiness"]["ready"] is False

    def test_state_feed_is_published_not_received(self, client):
        body = client.get(
            "/v1/fusion/state-feed/stay_alert_001", params={"tick": 5}, headers=_headers()
        ).json()
        feed = body["state_feed"]
        assert feed["tick"] == 5
        assert feed["schemaVersion"]
        assert feed["agents"]
        # Known boundary conflict, reported in docs/space-runtime/architecture-and-boundaries.md:
        # the state-feed contract still carries position/velocity placeholders that the
        # World Engine owns. The runtime publishes them exactly as src/fusion/state_feed.py
        # produces them and never accepts physical state from a caller.
        for agent in feed["agents"]:
            assert agent["position"] == {"x": 0.0, "y": 0.0, "z": 0.0}
            assert agent["velocity"] == {"x": 0.0, "y": 0.0, "z": 0.0}

    def test_runtime_info_reports_boundaries(self, client):
        body = client.get("/v1/runtime/info", headers=_headers()).json()
        assert body["governance_enforced"] is True
        assert "does_not_own" in body["boundaries"]
        assert any("physics" in item for item in body["boundaries"]["does_not_own"])


class TestAgentLoopSeam:
    """The mounted contract seam must behave exactly as the repository tests demand."""

    def test_perception_returns_correlated_intent(self, client):
        response = client.post("/agent-loop/perception", json=_perception(42))
        assert response.status_code == 200
        intent = response.json()
        assert intent["agentId"] == "stay_alert_001"
        assert intent["observedTick"] == 42
        assert intent["verb"] in {"approach", "look_at", "use", "sit", "rest", "wait"}
        for forbidden in ("position", "velocity"):
            assert forbidden not in intent

    def test_unregistered_agent_is_404(self, client):
        response = client.post("/agent-loop/perception", json=_perception(7, "ghost_999"))
        assert response.status_code == 404

    def test_malformed_envelope_is_rejected(self, client):
        response = client.post("/agent-loop/perception", json={"agentId": "stay_alert_001"})
        assert response.status_code == 422
        assert "error" in response.json()


class TestSessionOrchestration:
    """The Avatar/Aide training loop the Space exposes at /v1/sessions."""

    def test_session_run_returns_metrics(self, client):
        response = client.post(
            "/v1/sessions/run",
            json={
                "scenarios": [
                    {"name": "Focus drill", "task_type": "focus_task", "base_success_rate": 0.6}
                ]
            },
            headers=_headers(),
        )
        assert response.status_code == 200
        session = response.json()["session"]
        assert session["session_id"]
        assert session["total_attempts"] >= 1
        assert 0.0 <= session["success_rate"] <= 1.0
        assert "fusion_ready" in session

    def test_session_run_requires_its_own_capability(self, client):
        response = client.post(
            "/v1/sessions/run",
            json={"scenarios": [{"name": "Focus drill"}]},
            headers=_headers(**{"X-NLT-Capabilities": "fusion.read"}),
        )
        assert response.status_code == 403
        assert response.json()["detail"]["error"] == "capability_not_granted"

    def test_scenarios_are_validated_before_any_work_runs(self, client):
        bad = client.post(
            "/v1/sessions/run", json={"scenarios": [{}]}, headers=_headers()
        )
        assert bad.status_code == 422
        assert bad.json()["detail"]["error"] == "scenario_name_required"

        out_of_range = client.post(
            "/v1/sessions/run",
            json={"scenarios": [{"name": "x", "base_success_rate": 1.5}]},
            headers=_headers(),
        )
        assert out_of_range.status_code == 422
        assert out_of_range.json()["detail"]["error"] == "value_out_of_range"
