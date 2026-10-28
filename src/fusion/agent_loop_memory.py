"""Per-agent decision memory for the agent loop (AGENT-LOOP-003 F1).

A decision source on its own is stateless: it answers every perception as if it were the first.
`StatefulAgentLoopDecision` wraps one and keeps, per agent, a bounded history of what it chose and
what the world looked like afterwards, then hands that history to the wrapped source with each new
perception.

Outcomes come from the next perception, not from engine result messages. Over the current HTTP
transport the engine's accepted/rejected results never reach Fusion: Godot logs them locally
(`FusionHttpLink.cs`) and Fusion exposes only `POST /agent-loop/perception`. Contract §4 already
names the next perception as the physical source of truth for whether anything happened. An
outcome records what changed between the two snapshots; it does not claim the intent caused it.

The history is Fusion-owned semantic state. It lives in process memory only, is never persisted,
and is never sent to the world engine.
"""

from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass
from math import hypot
from typing import Any, Callable, Mapping, Sequence

from .agent_loop import validate_intent, validate_perception

# Where outcomes come from (see module docstring). Recorded so a later transport that does deliver
# results can be told apart.
OUTCOME_SOURCE = "next_perception"

DEFAULT_HISTORY_SIZE = 8

# Horizontal displacement, in metres, below which the agent counts as not having moved.
MOVE_EPSILON = 0.25


@dataclass(frozen=True)
class DecisionOutcome:
    """What changed between the perception a decision answered and the agent's next perception."""

    ticks_elapsed: int
    moved_distance: float
    scene_changed: bool
    # None when the decision had no target.
    target_visible: bool | None
    target_distance_before: float | None
    target_distance_after: float | None
    # The target was free and is now held by someone else. The engine never reports an anchor as
    # occupied for the agent holding it, so an agent's own sit or use does not show up here.
    target_taken: bool

    @property
    def changed(self) -> bool:
        """True when the next perception differs in any way this outcome tracks."""
        target_moved = (
            self.target_distance_before is not None
            and self.target_distance_after is not None
            and abs(self.target_distance_after - self.target_distance_before) >= MOVE_EPSILON
        )
        return (
            self.scene_changed
            or self.moved_distance >= MOVE_EPSILON
            or target_moved
            or self.target_taken
            or self.target_visible is False
        )


@dataclass(frozen=True)
class DecisionRecord:
    """One decision an agent made and, once its next perception arrived, what followed."""

    tick: int
    scene_id: str
    verb: str
    target_id: str | None
    outcome: DecisionOutcome


DecisionWithHistory = Callable[
    [Mapping[str, Any], Sequence[DecisionRecord]], Mapping[str, Any]
]


def ignore_history(
    decide: Callable[[Mapping[str, Any]], Mapping[str, Any]],
) -> DecisionWithHistory:
    """Adapt a stateless decision source to the `(observation, history)` signature."""

    def decide_with_history(
        observation: Mapping[str, Any], history: Sequence[DecisionRecord]
    ) -> Mapping[str, Any]:
        return decide(observation)

    return decide_with_history


@dataclass(frozen=True)
class _Pending:
    tick: int
    scene_id: str
    verb: str
    target_id: str | None
    self_position: Mapping[str, float]
    target: Mapping[str, Any] | None


class _AgentMemory:
    def __init__(self, size: int) -> None:
        self.lock = threading.Lock()
        self.records: deque[DecisionRecord] = deque(maxlen=size)
        self.pending: _Pending | None = None
        self.last_tick: int | None = None


def _horizontal_distance(a: Mapping[str, float], b: Mapping[str, float]) -> float:
    # The engine is Y-up; height changes (steps, sitting) are not movement through the world.
    return hypot(a["x"] - b["x"], a["z"] - b["z"])


def _outcome(pending: _Pending, observation: Mapping[str, Any]) -> DecisionOutcome:
    position = observation["self"]["position"]
    target_visible: bool | None = None
    distance_before: float | None = None
    distance_after: float | None = None
    taken = False
    if pending.target is not None:
        distance_before = _horizontal_distance(
            pending.self_position, pending.target["position"]
        )
        after = next(
            (
                entity
                for entity in observation["visibleEntities"]
                if entity["id"] == pending.target_id
            ),
            None,
        )
        target_visible = after is not None
        if after is not None:
            distance_after = _horizontal_distance(position, after["position"])
            taken = after["occupied"] and not pending.target["occupied"]
    return DecisionOutcome(
        ticks_elapsed=observation["tick"] - pending.tick,
        moved_distance=_horizontal_distance(pending.self_position, position),
        scene_changed=observation["scene"]["id"] != pending.scene_id,
        target_visible=target_visible,
        target_distance_before=distance_before,
        target_distance_after=distance_after,
        target_taken=taken,
    )


class StatefulAgentLoopDecision:
    """Decision source that remembers each agent's recent decisions and their outcomes.

    Plugs into `FusionAgentLoop(decide=...)` like any other source. State is keyed by the
    perception's `agentId`; agents never see each other's history. Calls for the same agent are
    serialized, so each agent has one writer; calls for different agents run concurrently.
    """

    def __init__(
        self,
        decide: DecisionWithHistory,
        *,
        history_size: int = DEFAULT_HISTORY_SIZE,
    ) -> None:
        if isinstance(history_size, bool) or not isinstance(history_size, int):
            raise TypeError("history_size must be an integer")
        if history_size < 1:
            raise ValueError("history_size must be at least 1")
        self._decide = decide
        self.history_size = history_size
        self._agents: dict[str, _AgentMemory] = {}
        self._agents_lock = threading.Lock()

    def __call__(self, observation: Mapping[str, Any]) -> Mapping[str, Any]:
        validate_perception(observation)
        memory = self._memory_for(observation["agentId"])
        with memory.lock:
            self._resolve_pending(memory, observation)
            intent = self._decide(observation, tuple(memory.records))
            # Validate before remembering: an intent the loop will refuse never reached the engine.
            validate_intent(intent, observation)
            target_id = intent.get("targetId")
            target = None
            if target_id is not None:
                target = next(
                    entity
                    for entity in observation["visibleEntities"]
                    if entity["id"] == target_id
                )
            memory.pending = _Pending(
                tick=observation["tick"],
                scene_id=observation["scene"]["id"],
                verb=intent["verb"],
                target_id=target_id,
                self_position=dict(observation["self"]["position"]),
                target=(
                    {
                        "position": dict(target["position"]),
                        "occupied": target["occupied"],
                    }
                    if target is not None
                    else None
                ),
            )
            memory.last_tick = observation["tick"]
        return intent

    def history(self, agent_id: str) -> tuple[DecisionRecord, ...]:
        """Resolved decisions for `agent_id`, oldest first. The latest is pending until the next
        perception and is not included."""
        with self._agents_lock:
            memory = self._agents.get(agent_id)
        if memory is None:
            return ()
        with memory.lock:
            return tuple(memory.records)

    def reset(self, agent_id: str | None = None) -> None:
        """Forget one agent's history, or every agent's."""
        with self._agents_lock:
            if agent_id is None:
                self._agents.clear()
            else:
                self._agents.pop(agent_id, None)

    def _memory_for(self, agent_id: str) -> _AgentMemory:
        with self._agents_lock:
            memory = self._agents.get(agent_id)
            if memory is None:
                memory = _AgentMemory(self.history_size)
                self._agents[agent_id] = memory
            return memory

    @staticmethod
    def _resolve_pending(memory: _AgentMemory, observation: Mapping[str, Any]) -> None:
        tick = observation["tick"]
        if memory.last_tick is not None and tick < memory.last_tick:
            # Time went backwards: the engine restarted. The history describes another world.
            memory.records.clear()
            memory.pending = None
        elif memory.last_tick is not None and tick == memory.last_tick:
            # The same snapshot again (the engine never received the intent and retried). Nothing
            # has happened since, so the pending decision has no outcome to record.
            memory.pending = None
        if memory.pending is not None:
            pending = memory.pending
            memory.records.append(
                DecisionRecord(
                    tick=pending.tick,
                    scene_id=pending.scene_id,
                    verb=pending.verb,
                    target_id=pending.target_id,
                    outcome=_outcome(pending, observation),
                )
            )
            memory.pending = None
