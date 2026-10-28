"""Async loopback HTTP transport for the nlt.agent-loop.v1 contract.

Godot POSTs one perception per decision opportunity to this server; a Fusion
decision source (local GGUF model or deterministic fallback) returns a correlated
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
  * ASFDK governance, live-world validation, and physical execution remain
    Godot's job; this server never claims execution.

Run:
    python -m src.fusion.agent_loop_http      # deterministic fallback decision
    FUSION_GGUF_MODEL=/path/model.gguf python -m src.fusion.agent_loop_http
"""

from __future__ import annotations

import asyncio
import os
import uuid
from typing import Any, Callable, Mapping

from fastapi import FastAPI, Request, Response

from .agent_loop import (
    AgentLoopProtocolError,
    FusionAgentLoop,
    PROTOCOL_VERSION,
    validate_perception,
)
from .agent_loop_memory import (
    DEFAULT_HISTORY_SIZE,
    StatefulAgentLoopDecision,
    ignore_history,
)


def _fallback_decide(observation: Mapping[str, Any]) -> dict[str, Any]:
    """Model-free decision source so the loop runs without a GGUF file.

    Chooses the first visible entity that is not occupied; otherwise waits.
    Deterministic on purpose: it is the control condition, not a wander loop.
    """
    for entity in observation.get("visibleEntities", []):
        if (
            entity.get("occupied") is False
            and entity.get("kind") != "agent"
            and "approach" in entity.get("affordances", [])
        ):
            return {
                "protocolVersion": PROTOCOL_VERSION,
                "messageType": "intent",
                "messageId": f"intent-{uuid.uuid4().hex[:12]}",
                "agentId": observation["agentId"],
                "observedTick": observation["tick"],
                "verb": "approach",
                "targetId": entity["id"],
            }
    return {
        "protocolVersion": PROTOCOL_VERSION,
        "messageType": "intent",
        "messageId": f"intent-{uuid.uuid4().hex[:12]}",
        "agentId": observation["agentId"],
        "observedTick": observation["tick"],
        "verb": "wait",
    }


def build_decision_source() -> Callable[[Mapping[str, Any]], Mapping[str, Any]]:
    """GGUF model when FUSION_GGUF_MODEL is set, else the fallback, with per-agent memory.

    FUSION_AGENT_LOOP_HISTORY sets how many past decisions each agent remembers.
    """
    raw_size = os.environ.get("FUSION_AGENT_LOOP_HISTORY", "").strip()
    history_size = int(raw_size) if raw_size else DEFAULT_HISTORY_SIZE
    model_path = os.environ.get("FUSION_GGUF_MODEL", "").strip()
    if not model_path:
        source: Callable[[Mapping[str, Any]], Mapping[str, Any]] = _fallback_decide
    else:
        from .gguf_agent_decision import LlamaCppAgentLoopDecision

        source = LlamaCppAgentLoopDecision(model_path)
    return StatefulAgentLoopDecision(ignore_history(source), history_size=history_size)


def create_app(
    decide: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
) -> FastAPI:
    """Build the FastAPI app. Tests inject their own decide; production uses env."""
    app = FastAPI(title="nlt.agent-loop.v1 fusion endpoint", version=PROTOCOL_VERSION)
    loop = FusionAgentLoop(decide if decide is not None else build_decision_source())

    in_flight: set[str] = set()

    @app.post("/agent-loop/perception")
    async def perception(request: Request) -> Response:
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

        agent_id = body["agentId"]

        # One in-flight per agent. Duplicate → 429; Godot treats non-2xx as
        # fail-closed (no intent applied, avatar keeps its current controller).
        if agent_id in in_flight:
            return _error(429, f"decision already in flight for {agent_id}")

        in_flight.add(agent_id)
        try:
            # Inference off the event loop: GGUF calls take seconds and must not
            # stall uvicorn (or, on the Godot side, its physics/render thread).
            intent = await asyncio.to_thread(loop.handle_observation, body)
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
