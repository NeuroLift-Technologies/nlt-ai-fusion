"""Tests for the bounded decision time and model quarantine (AGENT-LOOP-003 P0)."""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from src.fusion import PROTOCOL_VERSION, LlamaCppAgentLoopDecision, TransformersAgentLoopDecision
from src.fusion.agent_loop_deadline import (
    Abandonable,
    DecisionAbandoned,
    abandonable,
    decision_timeout,
    restore,
)
from src.fusion.agent_loop_http import build_decision_source, create_app, selected_model
from src.fusion.agent_loop_memory import StatefulAgentLoopDecision

AGENTS = frozenset({"avatar_1", "avatar_2"})


def perception(agent_id="avatar_1", tick=1):
    return {
        "protocolVersion": PROTOCOL_VERSION,
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
                "kind": "object",
                "position": {"x": 2.0, "y": 0.0, "z": 2.0},
                "affordances": ["approach", "use"],
                "occupied": False,
            }
        ],
    }


def approach(observation, history=()):
    return {
        "protocolVersion": PROTOCOL_VERSION,
        "messageType": "intent",
        "messageId": f"intent-{observation['tick']}",
        "agentId": observation["agentId"],
        "observedTick": observation["tick"],
        "verb": "approach",
        "targetId": "desk_1",
    }


class StuckSource:
    """A decision source whose first call blocks until released; later calls answer at once."""

    def __init__(self):
        self.release = threading.Event()
        self.returned = threading.Event()
        self.calls = 0

    def __call__(self, observation, history):
        self.calls += 1
        if self.calls == 1:
            self.release.wait(timeout=10)
            self.returned.set()
        return approach(observation)


@pytest.fixture
def short_timeout(monkeypatch):
    monkeypatch.setenv("FUSION_AGENT_LOOP_TIMEOUT", "0.2")


def post_until_served(client, body, seconds=5.0):
    """POST until the quarantine has lifted (the stuck call's release is seen by the server's
    event loop a moment after the call returns)."""
    deadline = time.monotonic() + seconds
    while True:
        response = client.post("/agent-loop/perception", json=body)
        if response.status_code != 503 or time.monotonic() > deadline:
            return response
        time.sleep(0.05)


@pytest.fixture
def stuck_app(short_timeout):
    # One event loop for the whole test (the `with` block): without it each request's loop
    # waits for the stuck worker thread when it shuts down.
    source = StuckSource()
    memory = StatefulAgentLoopDecision(source)
    app = create_app(decide=memory, registry=AGENTS)  # type: ignore[arg-type]
    with TestClient(app) as client:
        yield client, source, memory
        source.release.set()


def test_a_decision_that_outlives_the_timeout_gets_503_and_writes_no_memory(stuck_app):
    client, source, memory = stuck_app
    response = client.post("/agent-loop/perception", json=perception(tick=1))
    assert response.status_code == 503
    assert "quarantined" in response.json()["error"]

    source.release.set()
    assert source.returned.wait(timeout=5)
    # The intent was never received by Godot: no pending decision, so the next perception
    # resolves nothing into history.
    assert post_until_served(client, perception(tick=2)).status_code == 200
    assert memory.history("avatar_1") == ()


def test_every_agent_gets_503_at_once_while_the_model_is_quarantined(stuck_app):
    client, source, _ = stuck_app
    assert client.post("/agent-loop/perception", json=perception("avatar_1")).status_code == 503

    started = time.monotonic()
    response = client.post("/agent-loop/perception", json=perception("avatar_2"))
    assert response.status_code == 503
    assert "still running" in response.json()["error"]
    assert time.monotonic() - started < 2  # answered, not queued behind the 10 s stuck call
    assert source.calls == 1  # no new decision started on the quarantined model
    source.release.set()


def test_the_quarantine_ends_when_the_stuck_call_returns(stuck_app):
    client, source, _ = stuck_app
    assert client.post("/agent-loop/perception", json=perception("avatar_1")).status_code == 503
    source.release.set()
    assert source.returned.wait(timeout=5)

    response = post_until_served(client, perception("avatar_2"))
    assert response.status_code == 200
    assert response.json()["agentId"] == "avatar_2"


def test_a_decision_within_the_timeout_is_answered(monkeypatch):
    monkeypatch.setenv("FUSION_AGENT_LOOP_TIMEOUT", "5")
    client = TestClient(create_app(decide=StatefulAgentLoopDecision(approach), registry=AGENTS))
    assert client.post("/agent-loop/perception", json=perception()).status_code == 200


@pytest.mark.parametrize(
    ("raw", "seconds"), [("", 15.0), ("2.5", 2.5), ("29.9", 29.9)]
)
def test_the_timeout_defaults_to_15_seconds_and_stays_below_godots(monkeypatch, raw, seconds):
    monkeypatch.setenv("FUSION_AGENT_LOOP_TIMEOUT", raw)
    assert decision_timeout() == seconds


@pytest.mark.parametrize("raw", ["0", "-1", "30", "45", "soon"])
def test_a_timeout_godot_would_hit_first_fails_at_startup(monkeypatch, raw):
    monkeypatch.setenv("FUSION_AGENT_LOOP_TIMEOUT", raw)
    with pytest.raises(ValueError, match="FUSION_AGENT_LOOP_TIMEOUT"):
        create_app(decide=approach, registry=AGENTS)  # type: ignore[arg-type]


class SlowLlama:
    """Fake llama.cpp model that records how many calls run at once."""

    def __init__(self, seconds=0.05):
        self.seconds = seconds
        self.active = 0
        self.max_active = 0
        self.calls = 0
        self._lock = threading.Lock()

    def create_chat_completion(self, **kwargs):
        with self._lock:
            self.calls += 1
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        time.sleep(self.seconds)
        with self._lock:
            self.active -= 1
        return {"choices": [{"message": {"content": '{"verb":"wait"}'}}]}


def test_a_queued_call_whose_request_timed_out_never_starts_inference():
    model = SlowLlama()
    adapter = LlamaCppAgentLoopDecision("unused.gguf", model=model)
    flag, token = abandonable()
    try:
        flag.abandon()
        with pytest.raises(DecisionAbandoned):
            adapter(perception())
    finally:
        restore(token)
    assert model.calls == 0


class SlowTensor:
    def __init__(self, tokens):
        self.tokens = list(tokens)

    @property
    def shape(self):
        return (1, len(self.tokens))

    def to(self, device):
        return self

    def __getitem__(self, index):
        return self.tokens


class WaitTokenizer:
    eos_token_id = 0

    def apply_chat_template(self, messages, **kwargs):
        return SlowTensor([1, 2, 3])

    def decode(self, tokens, *, skip_special_tokens):
        return '{"verb":"wait"}'


class ConcurrentFakeModel:
    """Fake Transformers model that records how many generate() calls overlap."""

    def __init__(self):
        self.active = 0
        self.max_active = 0
        self._lock = threading.Lock()

    def to(self, device):
        return self

    def eval(self):
        return self

    def generate(self, input_ids, **kwargs):
        with self._lock:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        time.sleep(0.05)
        with self._lock:
            self.active -= 1
        return SlowTensor(input_ids.tokens + [99])


def test_transformers_adapter_serializes_shared_model_generation():
    model = ConcurrentFakeModel()
    adapter = TransformersAgentLoopDecision(
        "unused-injected-model", tokenizer=WaitTokenizer(), model=model
    )
    with ThreadPoolExecutor(max_workers=3) as executor:
        intents = list(
            executor.map(adapter, [perception(f"avatar_{n}") for n in range(1, 4)])
        )
    assert [intent["agentId"] for intent in intents] == ["avatar_1", "avatar_2", "avatar_3"]
    assert model.max_active == 1


@pytest.mark.parametrize(
    ("env", "kind"),
    [
        ({}, "baseline"),
        ({"FUSION_GGUF_MODEL": "/models/q.gguf"}, "gguf"),
        ({"FUSION_AGENT_LOOP_MODEL": "Baseline", "FUSION_GGUF_MODEL": "/models/q.gguf"},
         "baseline"),
        ({"FUSION_AGENT_LOOP_MODEL": "transformers"}, "transformers"),
    ],
)
def test_the_model_is_selected_by_fusion_agent_loop_model(monkeypatch, env, kind):
    for variable in ("FUSION_AGENT_LOOP_MODEL", "FUSION_GGUF_MODEL"):
        monkeypatch.delenv(variable, raising=False)
    for variable, value in env.items():
        monkeypatch.setenv(variable, value)
    assert selected_model() == kind


@pytest.mark.parametrize(
    "env",
    [
        {"FUSION_AGENT_LOOP_MODEL": "gpt"},
        {"FUSION_AGENT_LOOP_MODEL": "gguf"},
        {"FUSION_AGENT_LOOP_MODEL": "gguf", "FUSION_GGUF_MODEL": "/does/not/exist.gguf"},
        {"FUSION_AGENT_LOOP_MODEL": "transformers"},
        {"FUSION_AGENT_LOOP_MODEL": "transformers", "FUSION_TRANSFORMERS_MODEL": "/does/not/exist"},
    ],
)
def test_an_unknown_or_unavailable_model_fails_at_startup(monkeypatch, env):
    for variable in ("FUSION_AGENT_LOOP_MODEL", "FUSION_GGUF_MODEL", "FUSION_TRANSFORMERS_MODEL"):
        monkeypatch.delenv(variable, raising=False)
    for variable, value in env.items():
        monkeypatch.setenv(variable, value)
    with pytest.raises((ValueError, FileNotFoundError, ImportError)):
        build_decision_source()


def test_a_decision_committed_as_the_time_runs_out_is_not_abandoned():
    handle = Abandonable()
    handle.commit()
    assert handle.abandon() is False


def test_an_abandoned_decision_cannot_be_committed():
    handle = Abandonable()
    assert handle.abandon() is True
    with pytest.raises(DecisionAbandoned):
        handle.commit()


def test_an_abandoned_decision_is_not_remembered():
    memory = StatefulAgentLoopDecision(approach)
    handle, token = abandonable()
    try:
        handle.abandon()
        with pytest.raises(DecisionAbandoned):
            memory(perception(tick=1))
    finally:
        restore(token)
    memory(perception(tick=2))
    assert memory.history("avatar_1") == ()
