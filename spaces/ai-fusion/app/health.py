"""Liveness, readiness and runtime metadata.

Hugging Face restarts a Space whose port stops answering, so liveness stays cheap
and dependency-free. Readiness reports what the runtime actually loaded, which is
what an operator or the API platform needs before routing traffic here.
"""

from __future__ import annotations

import platform
import sys
from datetime import datetime, timezone

import fastapi
from fastapi import APIRouter, Request

from src.fusion.agent_loop import PROTOCOL_VERSION
from src.fusion.agent_loop_http import selected_model
from src.fusion.agent_loop_registry import AgentRegistry

from .governance import ALL_CAPABILITIES, CAPABILITY_RUNTIME_INFO, authorize
from .settings import Settings


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_health_router(registry: AgentRegistry, settings: Settings, artifacts_writable: bool) -> APIRouter:
    router = APIRouter(tags=["runtime"])

    @router.get("/health")
    def health() -> dict:
        """Liveness only: the process is up and serving. No dependencies touched."""
        return {"status": "ok", "service": "ai-fusion-runtime", "timestamp": _now()}

    @router.get("/readyz")
    def readyz(request: Request) -> dict:
        """Readiness: the decision source resolved, agents are registered, storage is usable.

        Returns 503 with a reason list when the runtime cannot serve decisions, so a
        supervisor (or the Space health check) sees a hard failure rather than a
        process that answers but cannot think.
        """
        reasons: list[str] = []
        try:
            model_kind = selected_model()
        except ValueError as exc:  # unknown FUSION_AGENT_LOOP_MODEL
            model_kind = "invalid"
            reasons.append(str(exc))
        if not registry.agent_ids:
            reasons.append("no agents registered")
        if not artifacts_writable:
            reasons.append(f"artifacts directory is not writable: {settings.artifacts_dir}")

        body = {
            "status": "ok" if not reasons else "unavailable",
            "service": "ai-fusion-runtime",
            "timestamp": _now(),
            "model_kind": model_kind,
            "registered_agents": list(registry.agent_ids),
            "protocol_version": PROTOCOL_VERSION,
            "governance_mode": settings.governance_mode,
            "reasons": reasons,
        }
        if reasons:
            from fastapi.responses import JSONResponse

            return JSONResponse(content=body, status_code=503)
        return body

    @router.get("/v1/runtime/info")
    def runtime_info(request: Request) -> dict:
        """What this runtime is, and what it accepts. Capability-gated when enforced."""
        context = authorize(
            request,
            (CAPABILITY_RUNTIME_INFO,),
            enforced=settings.governance_enforced,
            accepted_versions=(settings.governance_version,),
        )
        return {
            "service": "ai-fusion-runtime",
            "protocol_version": PROTOCOL_VERSION,
            "model_kind": selected_model(),
            "registered_agents": list(registry.agent_ids),
            "capabilities_supported": list(ALL_CAPABILITIES),
            "governance": context.to_dict(),
            "governance_enforced": settings.governance_enforced,
            "configuration": settings.describe(),
            "versions": {
                "python": sys.version.split()[0],
                "fastapi": fastapi.__version__,
                "platform": platform.platform(),
            },
            "boundaries": {
                "owns": ["cognitive decision", "readiness", "fusion", "state feed production"],
                "does_not_own": [
                    "physics and world state",
                    "rendering",
                    "ASFDK-C# enforcement at Godot ingress",
                ],
            },
        }

    return router
