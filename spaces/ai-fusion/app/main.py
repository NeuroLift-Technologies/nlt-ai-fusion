"""AI-Fusion runtime entrypoint for the Hugging Face Space.

Composition, in the order the router table resolves:

1. ``/health``, ``/readyz``, ``/v1/runtime/info`` — Space health and metadata.
2. ``/v1/fusion/*`` — readiness, fusion attempt, renderer state feed.
3. ``/agent-loop/*`` — the frozen ``nlt.agent-loop.v1`` seam Godot calls, mounted
   unchanged from ``src.fusion.agent_loop_http.create_app`` so the contract's
   behaviour (registry, quarantine, one-in-flight, fail-closed errors) is the same
   code that is tested in the repository.

Boundaries this file must not cross: no physics, no world state, no rendering, and
no ASFDK enforcement (that lives at the Godot intent ingress).
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.fusion.agent_loop_http import create_app as create_agent_loop_app
from src.fusion.agent_loop_registry import build_default_registry

from .fusion_routes import build_router as build_fusion_router
from .session_routes import build_router as build_session_router
from .health import build_health_router
from .settings import load_settings

log = logging.getLogger("ai_fusion.space")


def _artifacts_writable(settings) -> bool:
    try:
        settings.artifacts_dir.mkdir(parents=True, exist_ok=True)
        probe = settings.artifacts_dir / ".write-probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True
    except OSError as exc:
        log.warning("artifacts directory unusable at %s: %s", settings.artifacts_dir, exc)
        return False


def create_runtime_app(*, settings=None) -> FastAPI:
    """Build the runtime. Importable and injectable so tests need no environment."""
    settings = settings or load_settings()

    registry = build_default_registry()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        logging.basicConfig(
            level=logging.INFO,
            format="%(levelname)s:     %(name)s: %(message)s",
        )
        log.info("ai-fusion runtime starting: %s", settings.describe())
        log.info("registered agents: %s", list(registry.agent_ids))
        if not settings.governance_enforced:
            log.warning(
                "NLT_GOVERNANCE_MODE=permissive: requests are accepted without a capability "
                "grant and responses carry governance_enforced=false"
            )
        os.environ.setdefault("NEUROLIFT_MODELS_DIR", str(settings.models_dir))
        try:
            yield
        finally:
            log.info("ai-fusion runtime stopping")

    app = FastAPI(
        title="NeuroLift AI-Fusion Runtime",
        description=(
            "Cognitive layer of the NeuroLift platform: Avatar/Aide/Advocate fusion and the "
            "nlt.agent-loop.v1 decision seam. Physical simulation stays in nlt-world-engine."
        ),
        version="1.0.0",
        lifespan=lifespan,
    )

    if settings.allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.allowed_origins,
            allow_credentials=True,
            allow_methods=["POST", "GET"],
            allow_headers=["*"],
        )

    app.include_router(build_health_router(registry, settings, _artifacts_writable(settings)))
    app.include_router(build_fusion_router(registry, settings))
    app.include_router(build_session_router(settings))

    # Mounted last: everything above keeps precedence, and the agent-loop app owns
    # its own paths (/agent-loop/perception, /agent-loop/status).
    app.mount("/", create_agent_loop_app(registry=registry))

    return app
