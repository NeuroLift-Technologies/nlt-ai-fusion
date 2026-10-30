"""
NeuroLift AI-Fusion — FastAPI Backend
Exposes Avatar, Aide, session, scenario, and fusion APIs. The physical world is owned by the sibling Godot project.
"""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import avatars, aides, sessions, fusion, scenarios, health, ai

app = FastAPI(
    title="NeuroLift AI-Fusion API",
    description=(
        "REST API for the NeuroLift simulation training environment. "
        "Manages Avatars, Aides, training sessions, and the Avatar→Advocate fusion process."
    ),
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ---------------------------------------------------------------------------
# CORS — allow the web app and mobile apps to call the API
# ---------------------------------------------------------------------------
default_origins = [
    "http://localhost:3000",
    "http://localhost:4173",
    "http://localhost:5173",
    "http://localhost:8081",
]
cors_allow_origins = [
    origin.strip()
    for origin in os.getenv("NEUROLIFT_CORS_ALLOW_ORIGINS", ",".join(default_origins)).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(avatars.router, prefix="/api/avatars", tags=["Avatars"])
app.include_router(aides.router, prefix="/api/aides", tags=["Aides"])
app.include_router(sessions.router, prefix="/api/sessions", tags=["Training Sessions"])
app.include_router(fusion.router, prefix="/api/fusion", tags=["Fusion"])
app.include_router(scenarios.router, prefix="/api/scenarios", tags=["Scenarios"])
app.include_router(ai.router, prefix="/api/ai", tags=["AI Models"])
