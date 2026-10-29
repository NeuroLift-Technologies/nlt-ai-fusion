"""Deterministic goal-driven decision source for the agent loop (AGENT-LOOP-003 F4).

The control for the model: it follows the same goal (F2) and the same ranked options (F3) a model
is shown, and always takes the first one, or waits when nothing is allowed. If this source passes
acceptance 4a and a model given the same input does not pass 4b, the input is sufficient and the
model is the bottleneck (brief §4).

It is also the endpoint's decision source when no model is configured, in place of the earlier
"approach the first visible entity" fallback.
"""

from __future__ import annotations

import uuid
from typing import Any, Mapping, Sequence

from .agent_loop import PROTOCOL_VERSION
from .agent_loop_goals import derive_goal
from .agent_loop_memory import DecisionRecord, DecisionWithHistory
from .agent_loop_ranking import guide
from .agent_loop_registry import AgentRegistry


def goal_baseline(registry: AgentRegistry) -> DecisionWithHistory:
    """A decision source that takes the best-ranked option for the registered Avatar's goal."""

    def decide(
        observation: Mapping[str, Any], history: Sequence[DecisionRecord]
    ) -> Mapping[str, Any]:
        goal = derive_goal(registry.get(observation["agentId"]).avatar)
        options = guide(observation, goal.needs, history).options
        intent: dict[str, Any] = {
            "protocolVersion": PROTOCOL_VERSION,
            "messageType": "intent",
            "messageId": f"intent-{uuid.uuid4().hex[:12]}",
            "agentId": observation["agentId"],
            "observedTick": observation["tick"],
            "verb": "wait",
        }
        if options:
            intent["verb"], intent["targetId"] = options[0]
        return intent

    return decide
