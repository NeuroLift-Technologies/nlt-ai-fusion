"""
Tests for the world-state backend router.

Uses FastAPI's TestClient to exercise every endpoint end-to-end
against a freshly built WorldEngine.
"""
import json
import os
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Ensure project root and backend are importable
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "backend"))

from backend.app.main import app
from backend.app.routers import world


@pytest.fixture(scope="module")
def client():
    """A TestClient with the world engine initialised."""
    world.init_world_engine()
    with TestClient(app) as c:
        yield c


@pytest.fixture
def engine():
    """Direct access to the singleton WorldEngine."""
    return world.get_engine()


class TestWorldStateEndpoint:
    def test_get_world_state(self, client):
        resp = client.get("/api/world/state")
        assert resp.status_code == 200
        data = resp.json()
        assert "simulation_id" in data
        assert "tick_count" in data
        assert "state" in data
        assert "config" in data
        assert "time" in data
        assert "rooms" in data
        assert "sims" in data
        assert "entities" in data

    def test_world_state_has_five_rooms(self, client):
        resp = client.get("/api/world/state")
        rooms = resp.json()["rooms"]
        room_names = {r["name"] for r in rooms}
        assert {"bedroom", "kitchen", "living_room", "bathroom", "office"}.issubset(room_names)

    def test_world_state_has_two_sims(self, client):
        resp = client.get("/api/world/state")
        sims = resp.json()["sims"]
        assert len(sims) == 2
        names = {s["name"] for s in sims}
        assert {"Alex", "Jamie"}.issubset(names)

    def test_world_state_has_furniture(self, client):
        resp = client.get("/api/world/state")
        rooms = resp.json()["rooms"]
        total_furniture = sum(len(r["furniture"]) for r in rooms)
        assert total_furniture == 12

    def test_world_state_time_fields(self, client):
        resp = client.get("/api/world/state")
        time_data = resp.json()["time"]
        assert "day" in time_data
        assert "hour" in time_data
        assert "minute" in time_data
        assert "is_daytime" in time_data
        assert "day_of_week" in time_data
        assert "weekend" in time_data
        assert "total_minutes_elapsed" in time_data
        assert "speed_multiplier" in time_data
        assert "speed_label" in time_data


class TestSimsEndpoints:
    def test_list_sims(self, client):
        resp = client.get("/api/world/sims")
        assert resp.status_code == 200
        sims = resp.json()
        assert len(sims) == 2
        for s in sims:
            assert "sim_id" in s
            assert "name" in s
            assert "position" in s
            assert "room" in s
            assert "current_activity" in s
            assert "needs_summary" in s

    def test_get_sim_by_entity_id(self, client):
        sims = client.get("/api/world/sims").json()
        sim_id = sims[0]["sim_id"]
        resp = client.get(f"/api/world/sims/{sim_id}")
        assert resp.status_code == 200
        detail = resp.json()
        assert detail["sim_id"] == sim_id
        assert "needs" in detail
        assert "mood" in detail
        assert "relationships" in detail
        assert "schedule" in detail
        assert "weekend" in detail

    def test_get_sim_by_agent_id(self, client):
        resp = client.get("/api/world/sims/sim_alex")
        assert resp.status_code == 200
        detail = resp.json()
        assert detail["name"] == "Alex"

    def test_get_sim_not_found(self, client):
        resp = client.get("/api/world/sims/nonexistent-id")
        assert resp.status_code == 404


class TestRoomsEndpoint:
    def test_list_rooms(self, client):
        resp = client.get("/api/world/rooms")
        assert resp.status_code == 200
        rooms = resp.json()
        assert len(rooms) == 5
        for r in rooms:
            assert "name" in r
            assert "furniture" in r
            assert "occupants" in r

    def test_kitchen_has_furniture(self, client):
        resp = client.get("/api/world/rooms")
        kitchen = next(r for r in resp.json() if r["name"] == "kitchen")
        assert len(kitchen["furniture"]) == 4


class TestTimeControlEndpoints:
    def test_set_speed_fast(self, client):
        resp = client.post("/api/world/time/speed", json={"speed": "fast"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["new_speed"] == 5.0
        assert data["new_label"] == "fast"
        assert data["previous_speed"] == 1.0

    def test_set_speed_ultra(self, client):
        resp = client.post("/api/world/time/speed", json={"speed": "ultra"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["new_speed"] == 20.0

    def test_set_speed_realtime(self, client):
        resp = client.post("/api/world/time/speed", json={"speed": "realtime"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["new_speed"] == 1.0

    def test_set_speed_hyper(self, client):
        resp = client.post("/api/world/time/speed", json={"speed": "hyper"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["new_speed"] == 100.0

    def test_set_speed_invalid(self, client):
        resp = client.post("/api/world/time/speed", json={"speed": "invalid"})
        assert resp.status_code == 400

    def test_set_speed_case_insensitive(self, client):
        resp = client.post("/api/world/time/speed", json={"speed": "FAST"})
        assert resp.status_code == 200
        assert resp.json()["new_speed"] == 5.0

    def test_advance_time(self, client):
        # Set to known time first
        client.post("/api/world/time/speed", json={"speed": "realtime"})
        client.post("/api/world/time/set", json={"hour": 10, "minute": 0})
        resp = client.post("/api/world/time/advance", json={"minutes": 90})
        assert resp.status_code == 200
        data = resp.json()
        assert data["previous_time"]["hour"] == 10
        assert data["new_time"]["hour"] == 11
        assert data["new_time"]["minute"] == 30

    def test_advance_time_negative(self, client):
        resp = client.post("/api/world/time/advance", json={"minutes": -5})
        # Pydantic ge=0 validation rejects this with 422
        assert resp.status_code == 422

    def test_set_time(self, client):
        resp = client.post("/api/world/time/set", json={"hour": 14, "minute": 30})
        assert resp.status_code == 200
        data = resp.json()
        assert data["new_time"]["hour"] == 14
        assert data["new_time"]["minute"] == 30

    def test_set_time_invalid_hour(self, client):
        resp = client.post("/api/world/time/set", json={"hour": 25, "minute": 0})
        # Pydantic le=23 validation rejects this with 422
        assert resp.status_code == 422

    def test_set_time_invalid_minute(self, client):
        resp = client.post("/api/world/time/set", json={"hour": 10, "minute": 60})
        # Pydantic le=59 validation rejects this with 422
        assert resp.status_code == 422


class TestSaveLoadEndpoints:
    def test_save_world(self, client):
        resp = client.post("/api/world/save", json={"filename": "test-save-auto"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["saved"] is True
        assert "test-save-auto" in data["message"]

    def test_save_invalid_filename(self, client):
        resp = client.post("/api/world/save", json={"filename": "../evil"})
        assert resp.status_code == 400

    def test_save_filename_with_slash(self, client):
        resp = client.post("/api/world/save", json={"filename": "foo/bar"})
        assert resp.status_code == 400

    def test_load_world(self, client):
        client.post("/api/world/save", json={"filename": "auto-load-test"})
        resp = client.post("/api/world/load", json={"filename": "auto-load-test"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["loaded"] is True
        assert "time" in data

    def test_load_nonexistent(self, client):
        resp = client.post("/api/world/load", json={"filename": "does-not-exist-xyz"})
        assert resp.status_code == 404

    def test_load_invalid_filename(self, client):
        resp = client.post("/api/world/load", json={"filename": "../../etc/passwd"})
        assert resp.status_code == 400
