"""Async loopback HTTP transport for the nlt.agent-loop.v1 contract.

Godot POSTs one perception per decision opportunity to this server; a Fusion
decision source (local GGUF model or the deterministic goal baseline) returns a correlated
intent. Transport-neutral contract unchanged — this module only adds the
listener the contract deliberately left undecided.

Boundaries (docs/contracts/agent-loop-v1.md):
  * Fusion returns intent only — never coordinates, velocity, or object state.
  * Stale/mismatched observedTick is rejected by validate_intent before the
    decision source ever sees it.
  * Inference runs off the event loop (asyncio.to_thread); uvicorn stays
    responsive while a 0.6B GGUF call takes seconds.
  * One in-flight request per agent (defense in depth — Godot also enforces it
    client-side); duplicates get 429 and Godot fails closed.
  * Only agents Fusion registered at startup are served (AGENT-LOOP-003 F0); any
    other agentId gets 404 and no intent. Fusion never creates an avatar on demand.
  * ASFDK governance, live-world validation, and physical execution remain
    Godot's job; this server never claims execution.
  * Every decision is bounded by FUSION_AGENT_LOOP_TIMEOUT (default 15 s, always
    below Godot's 30 s). A decision that outlives it gets 503 and quarantines the
    model: every new request gets 503 at once until the stuck call returns
    (agent_loop_deadline).

Run:
    python -m src.fusion.agent_loop_http      # deterministic goal baseline (F4)
    FUSION_AGENT_LOOP_MODEL=gguf FUSION_GGUF_MODEL=/path/model.gguf python -m src.fusion.agent_loop_http
    FUSION_AGENT_LOOP_MODEL=transformers FUSION_TRANSFORMERS_MODEL=/path/model_dir python -m ...
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, Callable, Mapping

from fastapi import FastAPI, Request, Response

from .agent_loop import (
    AgentLoopProtocolError,
    FusionAgentLoop,
    PROTOCOL_VERSION,
    validate_perception,
)
from .agent_loop_baseline import goal_baseline
from .agent_loop_deadline import ModelQuarantine, abandonable, decision_timeout, restore
from .agent_loop_goals import with_goal
from .agent_loop_registry import AgentRegistry, build_default_registry
from .agent_loop_memory import DEFAULT_HISTORY_SIZE, StatefulAgentLoopDecision


# Values of FUSION_AGENT_LOOP_MODEL.
MODEL_KINDS = ("baseline", "gguf", "transformers")


def selected_model() -> str:
    """FUSION_AGENT_LOOP_MODEL: baseline, gguf or transformers. Unset, it is gguf when
    FUSION_GGUF_MODEL is set (as before it existed), else baseline. Anything else fails."""
    kind = os.environ.get("FUSION_AGENT_LOOP_MODEL", "").strip().lower()
    if not kind:
        return "gguf" if os.environ.get("FUSION_GGUF_MODEL", "").strip() else "baseline"
    if kind not in MODEL_KINDS:
        raise ValueError(
            f"FUSION_AGENT_LOOP_MODEL must be one of {', '.join(MODEL_KINDS)}: {kind!r}"
        )
    return kind


def build_decision_source(
    registry: AgentRegistry | None = None,
) -> Callable[[Mapping[str, Any]], Mapping[str, Any]]:
    """The decision source FUSION_AGENT_LOOP_MODEL selects, with per-agent memory.

    A model (`gguf` from FUSION_GGUF_MODEL, `transformers` from the FUSION_TRANSFORMERS_MODEL
    directory) is given the goal of the Avatar registered under each perception's agentId, its
    recent decisions (AGENT-LOOP-003 F2) and the ranked options (F3). The `baseline` (F4) takes
    the first-ranked option for the same goal. A model that is selected but cannot be loaded
    fails here, at startup, instead of on the first perception.
    FUSION_AGENT_LOOP_HISTORY sets how many past decisions each agent remembers.
    """
    raw_size = os.environ.get("FUSION_AGENT_LOOP_HISTORY", "").strip()
    history_size = int(raw_size) if raw_size else DEFAULT_HISTORY_SIZE
    agents = registry if registry is not None else build_default_registry()
    kind = selected_model()
    if kind == "baseline":
        return StatefulAgentLoopDecision(goal_baseline(agents), history_size=history_size)
    if kind == "gguf":
        from .gguf_agent_decision import LlamaCppAgentLoopDecision

        model: Any = LlamaCppAgentLoopDecision(_model_path("FUSION_GGUF_MODEL"))
    else:
        from .transformers_agent_decision import TransformersAgentLoopDecision

        model = TransformersAgentLoopDecision(_model_path("FUSION_TRANSFORMERS_MODEL"))
    return StatefulAgentLoopDecision(with_goal(model, agents), history_size=history_size)


def _model_path(variable: str) -> str:
    path = os.environ.get(variable, "").strip()
    if not path:
        raise ValueError(f"{variable} must be set for FUSION_AGENT_LOOP_MODEL={selected_model()}")
    return path


def create_app(
    decide: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
    registry: AgentRegistry | None = None,
) -> FastAPI:
    """Build the FastAPI app. Tests inject their own decide; production uses env.

    `registry` lists the agents this endpoint decides for; by default the roster pairs from
    `build_default_registry`.
    """
    agents = registry if registry is not None else build_default_registry()
    timeout = decision_timeout()
    app = FastAPI(title="nlt.agent-loop.v1 fusion endpoint", version=PROTOCOL_VERSION)
    loop = FusionAgentLoop(decide if decide is not None else build_decision_source(agents))

    in_flight: set[str] = set()
    quarantine = ModelQuarantine()

    @app.post("/agent-loop/perception")
    async def perception(request: Request) -> Response:
        body = await _read_perception(request, agents)
        if isinstance(body, Response):
            return body
        agent_id = body["agentId"]

        # One in-flight per agent. Duplicate → 429; Godot treats non-2xx as
        # fail-closed (no intent applied, avatar keeps its current controller).
        if agent_id in in_flight:
            return _error(429, f"decision already in flight for {agent_id}")
        # Never start a decision while one that timed out is still running.
        if quarantine.active:
            return _error(503, "model quarantined: a timed-out decision is still running")

        in_flight.add(agent_id)
        try:
            # Inference off the event loop: GGUF calls take seconds and must not
            # stall uvicorn (or, on the Godot side, its physics/render thread).
            # The worker thread inherits this context, and with it the flag.
            abandoned, token = abandonable()
            try:
                task = asyncio.ensure_future(asyncio.to_thread(loop.handle_observation, body))
            finally:
                restore(token)
            try:
                done, _ = await asyncio.wait({task}, timeout=timeout)
            except asyncio.CancelledError:
                # The request went away (shutdown); the call keeps running all the same.
                _abandon(task, abandoned, quarantine)
                raise
            if not done and _abandon(task, abandoned, quarantine):
                return _error(503, f"decision exceeded {timeout:g} s; model quarantined")
            # Done, or committed just as the time ran out: it finishes at once.
            intent = await task
        except AgentLoopProtocolError:
            return _error(422, "decision did not satisfy the agent-loop contract")
        except Exception:  # noqa: BLE001 - transport boundary fails closed
            return _error(503, "decision source unavailable")
        finally:
            in_flight.discard(agent_id)

        import json as _json

        return Response(
            content=_json.dumps(intent),
            media_type="application/json",
            status_code=200,
        )

    return app


def _abandon(task: asyncio.Future[Any], handle: Any, quarantine: ModelQuarantine) -> bool:
    """Give up on a running decision and quarantine the model until it returns. False if the
    decision was already committed, so its intent is about to arrive."""
    if not handle.abandon():
        return False
    quarantine.enter()
    task.add_done_callback(lambda finished: _released(finished, quarantine))
    return True


def _released(task: asyncio.Future[Any], quarantine: ModelQuarantine) -> None:
    """A timed-out decision has returned: end its part of the quarantine. Its result or error is
    read so it is not reported as unhandled, and discarded."""
    if not task.cancelled():
        task.exception()
    quarantine.leave()


async def _read_perception(request: Request, agents: AgentRegistry) -> dict[str, Any] | Response:
    """The request's perception, or the fail-closed error response for it."""
    # Parse strictly: an unparsable body is a transport failure, fail closed.
    try:
        body = await request.json()
    except Exception:
        return _error(400, "perception body is not valid JSON")

    # Envelope check before anything else touches it.
    try:
        validate_perception(body)
    except AgentLoopProtocolError:
        return _error(422, "invalid perception envelope")

    # Fail closed on an agent Fusion did not register: no avatar is created on demand.
    if body["agentId"] not in agents:
        return _error(404, "agent is not registered")
    return body


def _error(status: int, reason: str) -> Response:
    """Error envelope with a reason, mirroring the contract's rejection shape."""
    import json as _json

    return Response(
        content=_json.dumps({"error": reason, "status": status}),
        media_type="application/json",
        status_code=status,
    )


def main() -> None:
    """Run with uvicorn. Port matches Godot FusionHttpLink.FusionEndpoint."""
    import uvicorn

    uvicorn.run(
        create_app(),
        host="127.0.0.1",
        port=int(os.environ.get("FUSION_AGENT_LOOP_PORT", "8001")),
        log_level="info",
    )


if __name__ == "__main__":
    main()
