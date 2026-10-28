"""What an agent is trying to do, for the agent-loop decision source (AGENT-LOOP-003 F2).

A model choosing from a perception alone has nothing to choose by, so it takes the first option it
is offered. This module turns the registered Avatar's own state into a short semantic goal and one
or two needs, and turns the agent's recent decisions (F1) into a compact window, both for the
model's prompt. Nothing here is sent to the world engine: intents still carry only a verb and a
target.

The goal reads the Avatar's state without changing it. That state (stress, cognitive load,
burnout risk, state machine) changes only in training sessions (attempt_task, receive_coaching);
nothing in the world loop updates it yet, so during a world run the goal stays the same. That is
recorded as an open gap (brief §7.3), not worked around here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from ..avatars.base_avatar import AvatarState, BaseAvatar
from .agent_loop_memory import DecisionRecord, DecisionWithHistory
from .agent_loop_ranking import guide
from .agent_loop_registry import AgentRegistry

# A goal and the needs behind it.
_GoalSpec = tuple[str, tuple[str, ...]]

# Goal for an Avatar with nothing pressing, by trait. Short on purpose: a 0.6B model will not use a
# long prompt.
_TRAIT_GOALS: dict[str, _GoalSpec] = {
    "StayAlert": (
        "start the task you have been putting off: get to your desk and sit down to work",
        ("focus",),
    ),
}
_DEFAULT_GOAL: _GoalSpec = ("get going on today's task", ("focus",))

_RECOVER: _GoalSpec = (
    "recover after stress: find somewhere quiet to rest",
    ("rest", "quiet"),
)
_BREAK: _GoalSpec = (
    "take a short break before going back to the task",
    ("rest",),
)

# Thresholds on the Avatar's own 0..1 levels. 0.6 is where assess_burnout_risk calls risk "high".
STRESS_THRESHOLD = 0.7
BURNOUT_THRESHOLD = 0.6
COGNITIVE_LOAD_THRESHOLD = 0.7

_STRAINED_STATES = frozenset(
    {AvatarState.BURNOUT_RISK, AvatarState.BURNOUT, AvatarState.RECOVERING}
)

# How many past decisions the prompt shows, newest last.
RECENT_WINDOW = 4


@dataclass(frozen=True)
class AgentGoal:
    """A short semantic goal and the needs behind it."""

    goal: str
    needs: tuple[str, ...]


def derive_goal(avatar: BaseAvatar) -> AgentGoal:
    """The goal the Avatar's current state calls for. Reads state only; changes nothing."""
    if (
        avatar.current_state in _STRAINED_STATES
        or avatar.stress_level >= STRESS_THRESHOLD
        or avatar.burnout_risk_level >= BURNOUT_THRESHOLD
    ):
        goal, needs = _RECOVER
    elif avatar.cognitive_load >= COGNITIVE_LOAD_THRESHOLD:
        goal, needs = _BREAK
    else:
        goal, needs = _TRAIT_GOALS.get(avatar.trait_name, _DEFAULT_GOAL)
    return AgentGoal(goal=goal, needs=needs)


def decision_context(
    goal: AgentGoal, history: Sequence[DecisionRecord], window: int = RECENT_WINDOW
) -> dict[str, Any]:
    """The prompt context: goal, needs, and the last `window` decisions with whether anything
    changed after each."""
    recent = []
    for record in list(history)[-window:] if window > 0 else []:
        did = record.verb if record.target_id is None else f"{record.verb} {record.target_id}"
        recent.append({"did": did, "changed": record.outcome.changed})
    return {"goal": goal.goal, "needs": list(goal.needs), "recent": recent}


def with_goal(
    decide: Callable[..., Mapping[str, Any]], registry: AgentRegistry
) -> DecisionWithHistory:
    """Adapt a model decision source that takes `context` and `guidance` to the
    `(observation, history)` shape, giving it the goal of the Avatar registered under the
    perception's agentId (F2) and, for that goal, the entity ranking and the anti-repeat
    exclusions (F3)."""

    def decide_with_goal(
        observation: Mapping[str, Any], history: Sequence[DecisionRecord]
    ) -> Mapping[str, Any]:
        goal = derive_goal(registry.get(observation["agentId"]).avatar)
        return decide(
            observation,
            context=decision_context(goal, history),
            guidance=guide(observation, goal.needs, history),
        )

    return decide_with_goal
