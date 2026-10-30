"""ASFDK governance context for inbound Fusion requests.

The runtime must be able to carry agent identity, session context, provenance,
governance context and capability information across service boundaries — and an
authenticated caller must not be treated as an authorized one just because it
reached the endpoint.

This module does not implement ASFDK itself: ASFDK-C# governance and physical
validation stay at the Godot intent ingress (see docs/architecture.md §3). What it
does is stop Fusion from acting on a request that arrives without an explicit
capability grant, and pass the context through so downstream services can decide.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from fastapi import HTTPException, Request

AGENT_ID_HEADER = "X-NLT-Agent-Id"
SESSION_ID_HEADER = "X-NLT-Session-Id"
PROVENANCE_HEADER = "X-NLT-Provenance"
GOVERNANCE_VERSION_HEADER = "X-NLT-Governance-Version"
CAPABILITIES_HEADER = "X-NLT-Capabilities"

#: Capabilities the runtime can require of a caller.
CAPABILITY_FUSION_READ = "fusion.read"
CAPABILITY_FUSION_FUSE = "fusion.fuse"
CAPABILITY_SESSION_RUN = "fusion.session.run"
CAPABILITY_RUNTIME_INFO = "runtime.info"

ALL_CAPABILITIES = (
    CAPABILITY_FUSION_READ,
    CAPABILITY_FUSION_FUSE,
    CAPABILITY_SESSION_RUN,
    CAPABILITY_RUNTIME_INFO,
)



@dataclass(frozen=True)
class GovernanceContext:
    """Who is asking, on whose behalf, from where, and what they may do."""

    agent_id: str
    session_id: str
    provenance: str
    governance_version: str
    capabilities: frozenset[str] = field(default_factory=frozenset)

    def has(self, capability: str) -> bool:
        return capability in self.capabilities

    def to_dict(self) -> dict[str, object]:
        return {
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "provenance": self.provenance,
            "governance_version": self.governance_version,
            "capabilities": sorted(self.capabilities),
        }


def context_from_request(request: Request) -> GovernanceContext:
    """Extract the context. Missing values stay empty rather than defaulting to trust."""
    raw_caps: str = request.headers.get(CAPABILITIES_HEADER, "")
    capabilities = frozenset(c.strip() for c in raw_caps.split(",") if c.strip())
    return GovernanceContext(
        agent_id=request.headers.get(AGENT_ID_HEADER, "").strip(),
        session_id=request.headers.get(SESSION_ID_HEADER, "").strip(),
        provenance=request.headers.get(PROVENANCE_HEADER, "").strip(),
        governance_version=request.headers.get(GOVERNANCE_VERSION_HEADER, "").strip(),
        capabilities=capabilities,
    )


def _deny(status: int, code: str, reason: str, context: GovernanceContext) -> HTTPException:
    return HTTPException(
        status_code=status,
        detail={
            "error": code,
            "reason": reason,
            "required_context": [
                AGENT_ID_HEADER,
                SESSION_ID_HEADER,
                PROVENANCE_HEADER,
                GOVERNANCE_VERSION_HEADER,
                CAPABILITIES_HEADER,
            ],
            "context": context.to_dict(),
        },
    )


def authorize(
    request: Request,
    required: Iterable[str],
    *,
    enforced: bool,
    accepted_versions: Iterable[str] = (),
) -> GovernanceContext:
    """Require a provenance-bearing context holding every capability in ``required``.

    ``enforced=False`` (``NLT_GOVERNANCE_MODE=permissive``) records the context and
    lets the request through, so local development does not need signed headers.
    Responses always state which mode applied, so a permissive answer can never be
    mistaken for an authorized one.
    """
    context = context_from_request(request)
    missing = [name for name in required if not context.has(name)]

    if not enforced:
        return context

    if not context.agent_id or not context.session_id or not context.provenance:
        raise _deny(
            403,
            "governance_context_missing",
            "agent identity, session context and provenance are required",
            context,
        )
    if not context.governance_version:
        raise _deny(
            403,
            "governance_version_missing",
            "the caller did not state the governance version it operates under",
            context,
        )
    versions = set(accepted_versions)
    if versions and context.governance_version not in versions:
        raise _deny(
            403,
            "governance_version_unsupported",
            f"accepted versions: {', '.join(sorted(versions))}",
            context,
        )
    if missing:
        raise _deny(
            403,
            "capability_not_granted",
            f"missing capabilities: {', '.join(missing)}",
            context,
        )
    return context
