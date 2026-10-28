"""Which avatars the agent loop may decide for (AGENT-LOOP-003 F0).

The world engine names the agent in every perception (`agentId`). Fusion owns the Avatar/Aide
pairs, so it keeps an explicit registry from that id to a pair it created at startup. A
perception for an id that is not registered fails closed: Fusion never creates an avatar for a
name the engine sends.

The registered id is the Avatar's roster id (`avatar_id`, e.g. "stay_alert_001"). The engine
sends it as `agentId`, set on the Godot side by NLT_AGENT_LOOP_AGENT_ID.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..aides.base_aide import BaseAide
from ..aides.coaching.stay_alert_aide import StayAlertAide
from ..avatars.adhd_traits.stay_alert_avatar import StayAlertAvatar
from ..avatars.base_avatar import BaseAvatar
from ..simulation.session_orchestrator import SessionOrchestrator

_SRC = Path(__file__).resolve().parents[1]
STAY_ALERT_AVATAR_CONFIG = _SRC / "avatars" / "avatar_configs" / "stay_alert.json"
STAY_ALERT_AIDE_CONFIG = _SRC / "aides" / "aide_configs" / "stay_alert_aide.json"


class UnknownAgentError(LookupError):
    """A perception named an agent Fusion has not registered."""


@dataclass(frozen=True)
class AgentPair:
    """One registered Avatar/Aide pair, bound through its SessionOrchestrator."""

    agent_id: str
    avatar: BaseAvatar
    aide: BaseAide
    orchestrator: SessionOrchestrator


class AgentRegistry:
    """Explicit `agentId` -> pair registry. Filled at startup, read-only afterwards."""

    def __init__(self) -> None:
        self._pairs: dict[str, AgentPair] = {}

    def register(self, avatar: BaseAvatar, aide: BaseAide) -> AgentPair:
        """Bind `aide` to `avatar` and register the pair under the avatar's roster id.

        Raises:
            ValueError: If the avatar has no id or the id is already registered.
        """
        agent_id = avatar.avatar_id
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise ValueError("avatar_id must be a non-empty string")
        if agent_id in self._pairs:
            raise ValueError(f"agent '{agent_id}' is already registered")
        pair = AgentPair(
            agent_id=agent_id,
            avatar=avatar,
            aide=aide,
            orchestrator=SessionOrchestrator(avatar, aide),
        )
        self._pairs[agent_id] = pair
        return pair

    def get(self, agent_id: str) -> AgentPair:
        """The pair registered as `agent_id`.

        Raises:
            UnknownAgentError: If no pair is registered under `agent_id`.
        """
        try:
            return self._pairs[agent_id]
        except KeyError:
            raise UnknownAgentError(f"agent '{agent_id}' is not registered") from None

    def __contains__(self, agent_id: object) -> bool:
        return agent_id in self._pairs

    @property
    def agent_ids(self) -> tuple[str, ...]:
        """Registered ids, in registration order."""
        return tuple(self._pairs)


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def register_stay_alert(registry: AgentRegistry) -> AgentPair:
    """Create the StayAlert Avatar and its Aide from their roster configs and register them."""
    avatar_config = _load_json(STAY_ALERT_AVATAR_CONFIG)
    aide_config = _load_json(STAY_ALERT_AIDE_CONFIG)
    avatar = StayAlertAvatar(avatar_config["avatar_id"], dict(avatar_config["trait_config"]))
    aide = StayAlertAide(aide_config["aide_id"], dict(aide_config["expertise_config"]))
    return registry.register(avatar, aide)


def build_default_registry() -> AgentRegistry:
    """The pairs the agent-loop endpoint serves. StayAlert is the only fully implemented one."""
    registry = AgentRegistry()
    register_stay_alert(registry)
    return registry
