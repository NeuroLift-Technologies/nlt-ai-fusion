"""Runtime configuration for the AI-Fusion Space.

Every value comes from the environment so the same image runs locally, in CI and
on Hugging Face. Nothing here logs or returns a secret: :meth:`Settings.describe`
only reports whether an external dependency is configured, never its value.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

#: Governance modes. ``enforce`` refuses work that carries no capability grant;
#: ``permissive`` lets local development run without a grant and tags every
#: response with ``governance_enforced: false``.
GOVERNANCE_MODES = ("enforce", "permissive")


def _csv(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    """Resolved runtime configuration."""

    environment: str
    port: int
    allowed_origins: list[str] = field(default_factory=list)
    governance_mode: str = "enforce"
    governance_version: str = "ORG-DEV-OTOI-1.0.3"
    artifacts_dir: Path = Path("/data")
    models_dir: Path = Path("/data/models")
    supabase_configured: bool = False
    space_repo_id: str = ""

    @property
    def governance_enforced(self) -> bool:
        return self.governance_mode == "enforce"

    def describe(self) -> dict[str, object]:
        """Non-sensitive configuration summary, safe for logs and /v1/runtime/info."""
        return {
            "environment": self.environment,
            "governance_mode": self.governance_mode,
            "governance_version": self.governance_version,
            "allowed_origins": self.allowed_origins,
            "artifacts_dir": str(self.artifacts_dir),
            "models_dir": str(self.models_dir),
            "supabase_configured": self.supabase_configured,
            "space_repo_id": self.space_repo_id,
        }


def load_settings() -> Settings:
    """Read the environment. An unknown governance mode fails at startup."""
    mode = (os.environ.get("NLT_GOVERNANCE_MODE", "enforce").strip().lower() or "enforce")
    if mode not in GOVERNANCE_MODES:
        raise ValueError(
            f"NLT_GOVERNANCE_MODE must be one of {', '.join(GOVERNANCE_MODES)}: {mode!r}"
        )

    env = (os.environ.get("NLT_ENVIRONMENT", "production").strip() or "production")
    port_raw = os.environ.get("PORT", "7860").strip() or "7860"

    artifacts = Path(os.environ.get("NLT_ARTIFACTS_DIR", "/data").strip() or "/data")
    models = Path(
        os.environ.get("NEUROLIFT_MODELS_DIR", str(artifacts / "models")).strip()
        or str(artifacts / "models")
    )

    return Settings(
        environment=env,
        port=int(port_raw),
        allowed_origins=_csv(os.environ.get("ALLOWED_ORIGINS", "")),
        governance_mode=mode,
        governance_version=(
            os.environ.get("NLT_GOVERNANCE_VERSION", "ORG-DEV-OTOI-1.0.3").strip()
            or "ORG-DEV-OTOI-1.0.3"
        ),
        artifacts_dir=artifacts,
        models_dir=models,
        supabase_configured=bool(os.environ.get("SUPABASE_URL", "").strip()),
        space_repo_id=os.environ.get("SPACE_REPO_ID", "").strip(),
    )
