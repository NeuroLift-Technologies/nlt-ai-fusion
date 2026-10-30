"""Session orchestration routes — the Avatar/Aide training and evaluation loop.

This is the same service boundary `services/api/README.md` describes, reused rather
than reimplemented: `run_session` in `services.api.app.session_service` drives
`SessionOrchestrator` over `src.simulation.scenarios`. The Space adds governance,
a thread boundary (so a long session never blocks the decision seam) and a stable
`/v1` path.

Nothing here fuses models or mutates a world; it records session outcomes that make
readiness meaningful later.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from starlette.concurrency import run_in_threadpool

from services.api.app.session_service import DEFAULT_SCENARIOS, run_session

from .governance import CAPABILITY_SESSION_RUN, GovernanceContext, authorize
from .settings import Settings

def _guard(request: Request, settings: Settings) -> GovernanceContext:
    return authorize(
        request,
        (CAPABILITY_SESSION_RUN,),
        enforced=settings.governance_enforced,
        accepted_versions=(settings.governance_version,),
    )


def build_router(settings: Settings) -> APIRouter:
    """A fresh router per app, for the same reason as the fusion router."""
    router = APIRouter(prefix="/v1/sessions", tags=["sessions"])

    @router.post("/run")
    async def run(request: Request, payload: dict) -> dict:
        """Run one training session over the supplied scenarios.

        Body: ``{"scenarios": [{"name": ..., "task_type": ..., "base_success_rate":
        0.0-1.0, "cognitive_demand": 0.0-1.0}], "avatar_id": ..., "aide_id": ...,
        "ai_config": {...}}``. ``ai_config`` binds a model backend for the pair
        through the registry; it is optional and defaults to the rule fallback.
        """
        context = _guard(request, settings)

        scenarios = payload.get("scenarios")
        if scenarios is None:
            raise HTTPException(422, detail={"error": "scenarios_required"})
        if not isinstance(scenarios, list) or not scenarios:
            raise HTTPException(422, detail={"error": "scenarios_must_be_a_non_empty_list"})
        for index, scenario in enumerate(scenarios):
            if not isinstance(scenario, dict) or not str(scenario.get("name", "")).strip():
                raise HTTPException(
                    422,
                    detail={"error": "scenario_name_required", "index": index},
                )
            for field in ("base_success_rate", "cognitive_demand"):
                value = scenario.get(field)
                if value is not None and not (0.0 <= float(value) <= 1.0):
                    raise HTTPException(
                        422,
                        detail={"error": "value_out_of_range", "field": field, "index": index},
                    )

        result = await run_in_threadpool(
            run_session,
            scenarios,
            payload.get("avatar_id") or "stay_alert_api",
            payload.get("aide_id") or "stay_alert_aide_api",
            payload.get("ai_config"),
        )
        return {
            "session": result,
            "governance": context.to_dict(),
            "governance_enforced": settings.governance_enforced,
        }

    @router.get("/demo-run")
    async def demo_run(request: Request) -> dict:
        """Run the built-in deterministic session. Useful as a deploy smoke test."""
        context = _guard(request, settings)
        result = await run_in_threadpool(
            run_session, DEFAULT_SCENARIOS, "stay_alert_api", "stay_alert_aide_api", None
        )
        return {
            "session": result,
            "governance": context.to_dict(),
            "governance_enforced": settings.governance_enforced,
        }

    return router
