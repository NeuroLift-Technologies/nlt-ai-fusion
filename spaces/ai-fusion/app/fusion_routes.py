"""Fusion capability routes over the cognitive core in ``src.fusion``.

These routes are the stable service interface the NeuroLift API platform and the
Godot World Engine call. They expose Fusion's own semantics only:

* readiness assessment for a registered Avatar/Aide pair,
* a fusion attempt that produces an Advocate result,
* the one-way renderer state feed.

Physics, world state and rendering stay in ``nlt-world-engine``; nothing here
returns coordinates, velocity or object state, and nothing here mutates the world.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from src.fusion import FusionEngine, build_state_feed
from src.fusion.agent_loop_registry import AgentRegistry, UnknownAgentError

from .governance import (
    CAPABILITY_FUSION_FUSE,
    CAPABILITY_FUSION_READ,
    GovernanceContext,
    authorize,
)
from .settings import Settings

router = APIRouter(prefix="/v1/fusion", tags=["fusion"])  # replaced per app; see build_router
#: One engine per process. FusionEngine owns a ReadinessAssessor and its event
#: bus, so readiness and fusion always agree on the same thresholds.
_ENGINE = FusionEngine()


def _pair(registry: AgentRegistry, agent_id: str):
    try:
        return registry.get(agent_id)
    except UnknownAgentError:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "agent_not_registered",
                "reason": f"'{agent_id}' is not in this runtime's registry",
                "registered": list(registry.agent_ids),
            },
        ) from None


def _guard(request: Request, settings: Settings, capability: str) -> GovernanceContext:
    return authorize(
        request,
        (capability,),
        enforced=settings.governance_enforced,
        accepted_versions=(settings.governance_version,),
    )


def build_router(registry: AgentRegistry, settings: Settings) -> APIRouter:
    """Bind the routes to one process-wide registry and configuration.

    A fresh router per call: routes close over ``settings``, so reusing a module-level
    router would let the first app's governance mode leak into every later app in the
    same process (tests, reloads, or a factory called twice).
    """
    router = APIRouter(prefix="/v1/fusion", tags=["fusion"])

    @router.get("/agents")
    def list_agents(request: Request) -> dict:
        """Registered pairs. Fusion never invents an agent for an unknown id."""
        context = _guard(request, settings, CAPABILITY_FUSION_READ)
        pairs = [
            {
                "agent_id": agent_id,
                "avatar": {
                    "avatar_id": registry.get(agent_id).avatar.avatar_id,
                    "trait_name": registry.get(agent_id).avatar.trait_name,
                },
                "aide": {
                    "aide_id": registry.get(agent_id).aide.aide_id,
                },
            }
            for agent_id in registry.agent_ids
        ]
        return {
            "agents": pairs,
            "count": len(pairs),
            "governance": context.to_dict(),
            "governance_enforced": settings.governance_enforced,
        }

    @router.post("/readiness")
    def readiness(request: Request, payload: dict) -> dict:
        """Readiness dimensions for a pair. Read-only; no fusion is performed."""
        context = _guard(request, settings, CAPABILITY_FUSION_READ)
        agent_id = str(payload.get("agent_id", "")).strip()
        if not agent_id:
            raise HTTPException(422, detail={"error": "agent_id_required"})
        pair = _pair(registry, agent_id)
        assessment = _ENGINE.check_readiness(pair.avatar, pair.aide)
        return {
            "agent_id": agent_id,
            "readiness": assessment.to_dict(),
            "governance": context.to_dict(),
            "governance_enforced": settings.governance_enforced,
        }

    @router.post("/attempt")
    def attempt(request: Request, payload: dict) -> dict:
        """Attempt an Avatar + Aide -> Advocate fusion.

        ``force`` skips the readiness gate and exists for testing only; it is
        refused while governance is enforced unless the caller holds the fuse
        capability, which every authorised caller already needs.
        """
        context = _guard(request, settings, CAPABILITY_FUSION_FUSE)
        agent_id = str(payload.get("agent_id", "")).strip()
        if not agent_id:
            raise HTTPException(422, detail={"error": "agent_id_required"})
        force = bool(payload.get("force", False))
        pair = _pair(registry, agent_id)
        report = _ENGINE.fuse(pair.avatar, pair.aide, force=force)
        body = report.to_dict()
        body["agent_id"] = agent_id
        body["governance"] = context.to_dict()
        body["governance_enforced"] = settings.governance_enforced
        return body

    @router.get("/state-feed/{agent_id}")
    def state_feed(
        request: Request,
        agent_id: str,
        tick: int = Query(0, ge=0),
        scene_id: str = Query("open_world"),
    ) -> dict:
        """Renderer-facing state feed. One-way: Fusion produces, the renderer consumes."""
        context = _guard(request, settings, CAPABILITY_FUSION_READ)
        pair = _pair(registry, agent_id)
        feed = build_state_feed(pair.avatar, pair.aide, tick=tick, scene_id=scene_id)
        return {
            "agent_id": agent_id,
            "state_feed": feed,
            "governance": context.to_dict(),
            "governance_enforced": settings.governance_enforced,
        }

    return router
