"""Bounded decision time and model quarantine for the agent-loop endpoint (AGENT-LOOP-003 P0).

A decision that outlives `FUSION_AGENT_LOOP_TIMEOUT` is answered with 503, and the model enters
quarantine: every agent gets 503 until the stuck call returns or the process restarts, so no new
inference ever starts on a model that still has a call running. A Python thread cannot be
stopped, so the timed-out call is abandoned rather than cancelled: it runs to the end, and
nothing it produces is used.

An abandoned decision never writes memory: Godot never received its intent, so there is no
pending record to resolve. Code that would act on a decision checks `decision_abandoned()`
first: the model adapters before starting inference, `StatefulAgentLoopDecision` before
remembering the intent. The flag travels with the request's context into the worker thread
(`asyncio.to_thread` copies context variables).
"""

from __future__ import annotations

import os
import threading
from contextvars import ContextVar

# Godot's own wait for a decision, in seconds (FusionHttpLink). Fusion must give up first, so
# Godot always gets an answer instead of timing out itself.
GODOT_TIMEOUT_SECONDS = 30.0

# Fusion's wait for one decision, in seconds. Measured p95 was 3.25-6.49 s for Qwen3-0.6B
# (Josh, 2026-10-28: start at 15 s).
DEFAULT_TIMEOUT_SECONDS = 15.0

_ABANDONED: ContextVar[threading.Event | None] = ContextVar("agent_loop_abandoned", default=None)


class DecisionAbandoned(RuntimeError):
    """The request this decision was for has already been answered with a timeout."""


def decision_timeout() -> float:
    """FUSION_AGENT_LOOP_TIMEOUT in seconds, default 15. Must be above 0 and below Godot's 30 s;
    anything else fails at startup."""
    raw = os.environ.get("FUSION_AGENT_LOOP_TIMEOUT", "").strip()
    if not raw:
        return DEFAULT_TIMEOUT_SECONDS
    try:
        seconds = float(raw)
    except ValueError as exc:
        raise ValueError(f"FUSION_AGENT_LOOP_TIMEOUT must be a number of seconds: {raw!r}") from exc
    if not 0 < seconds < GODOT_TIMEOUT_SECONDS:
        raise ValueError(
            f"FUSION_AGENT_LOOP_TIMEOUT must be above 0 and below Godot's "
            f"{GODOT_TIMEOUT_SECONDS:g} s: {raw!r}"
        )
    return seconds


def abandonable() -> tuple[threading.Event, object]:
    """Mark the current context's decision as abandonable. Returns the flag to set on timeout
    and the token to pass to `restore`."""
    flag = threading.Event()
    return flag, _ABANDONED.set(flag)


def restore(token: object) -> None:
    """Undo `abandonable` for the current context."""
    _ABANDONED.reset(token)  # type: ignore[arg-type]


def decision_abandoned() -> bool:
    """True when the decision being made in this context has already timed out."""
    flag = _ABANDONED.get()
    return flag is not None and flag.is_set()


def raise_if_abandoned() -> None:
    """Stop a decision whose request has already been answered."""
    if decision_abandoned():
        raise DecisionAbandoned("the decision timed out before it started")


class ModelQuarantine:
    """Counts timed-out decisions still running. While any is, the model is quarantined."""

    def __init__(self) -> None:
        self._running = 0
        self._lock = threading.Lock()

    @property
    def active(self) -> bool:
        with self._lock:
            return self._running > 0

    def enter(self) -> None:
        """A decision timed out and is still running."""
        with self._lock:
            self._running += 1

    def leave(self) -> None:
        """A timed-out decision has returned."""
        with self._lock:
            self._running -= 1
