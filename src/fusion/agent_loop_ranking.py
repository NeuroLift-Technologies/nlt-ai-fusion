"""Which choices a model sees first, and which it no longer sees (AGENT-LOOP-003 F3).

A 0.6B model at temperature 0 takes the first option it is offered, and prompt wording does not
change that (F2 measured it), so the bias is removed structurally:

- **Ranking.** Visible entities are presented most goal-relevant first, then nearest, with their
  distance and relevance, instead of in engine order. Relevance comes from the F2 goal's needs.
- **Anti-repeat.** Some (verb, target) pairs are dropped from what the model may output, because
  repeating them cannot produce anything new:
  1. the pair chosen last, when its outcome changed nothing (brief F3). Except sitting on, resting
     on or using a goal-relevant target the agent is still at (`HOLD_RADIUS`): holding still is
     the goal reached, not a stall, and the engine treats the repeat as a no-op (AvatarCharacter
     ApplyInteraction). Without this the agent leaves its desk chair for the next one. A door or
     exit is not exempt: using it is a transition, and one that changed nothing has failed;
  2. `approach X` when the agent already stands within X's arrival radius (Joshua, 2026-10-28,
     brief §9.2): the engine counts it as arrived at once and the avatar wanders off;
  3. `look_at X` when the agent already looked at X since entering this scene, within the
     remembered history (F1, 8 decisions by default). Looking reveals nothing the
     perception did not already carry, and the wander that follows a look always moves the agent,
     so rule 1 alone never catches a look_at loop.

- **Ranked options.** The allowed pairs are put in one list, best first, because the model acts on
  the first option it is shown (brief §10.4):
  1. pairs on goal-relevant targets (sit, use, rest, approach; rest first when the need is rest),
     except `approach` to one already visited, which drops to tier 3;
  2. `approach` to targets not visited since entering the scene;
  3. everything else, `look_at` included.
  `wait` comes last. The model input lists the options in this order and the output grammar offers
  them in this order. The F4 baseline takes the first one.
- **Explore when the goal is not in view** (Josh, 2026-10-29: "if it has no goal then it should
  explore"). When no visible entity is goal-relevant and some `approach` is allowed, only
  `approach` is offered: unvisited targets first, farthest first, so each move carries the agent
  toward the edge of what it can perceive and new places come into view. Next, the walk already
  under way (the last approach, still moving the agent), so a walk is finished before another
  visited target is picked; without this the agent turned back halfway between two landmarks.
  `use`, `sit`, `rest` and `look_at` on targets that do not serve the goal are left out, so the
  agent cannot park beside one. No new verb and no reliance on the engine's wander: every move
  is a targeted `approach`.
- **Reach guard.** The engine refuses any intent whose target is beyond 30 m of the avatar's live
  position when it executes (IntentIngress.RecheckTarget), while perception lists entities out to
  25 m. A walking avatar keeps moving while the decision is made, so a target perceived at 24 m
  can be 31 m away at execution (measured: 24.1 m, 1.4 m/s, a 7 s decision). Pairs whose target
  would be out of reach at the position predicted from the avatar's velocity and the expected
  decision time are left out. A goal-relevant target that is out of reach does not stop the agent
  exploring.
- **Blocked targets.** An approach that made no progress toward a target the agent is still
  beyond the arrival radius of means the target cannot be reached from here (measured: the agent
  stopped 7.6 m short of a raised doorway). Every pair on that target except `look_at` is left out
  for the rest of the scene, within the remembered history.

`wait` is never dropped, so a model always has something to choose. Exclusions are computed from
the current perception and the F1 history only; history is cleared when the engine restarts, and
rules 1 and 3 count only decisions made since the agent entered its current scene, so going through
a door resets them.

Everything here shapes the model's prompt and output grammar. Nothing is sent to the world engine.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from math import hypot
from typing import Any, Mapping, Sequence

from .agent_loop_choices import grounded_choices
from .agent_loop_memory import MOVE_EPSILON, DecisionRecord

# The engine's arrival radius for a targeted move, in metres (AvatarCharacter.ApplyIntent).
ARRIVAL_RADIUS = 1.0

# How close an agent must be to a target it sits on, rests on or uses to count as still holding
# it. Wider than the arrival radius: a seated avatar drifts a little, and at 1.0 m exactly the
# exemption from rule 1 lapsed after 70 decisions and the agent moved to the next chair.
HOLD_RADIUS = 1.5

# The engine's reach for any targeted intent, in metres, from the avatar's live position at
# execution (IntentIngress.RecheckTarget).
REACH_RADIUS = 30.0

# Verbs that need the agent to get to the target.
_REACHING_VERBS = ("approach", "use", "sit", "rest")

# Words in an entity id that serve a need. Ids are readable slugs from the engine: doors are
# `door_<n>_<office|shop|school|home>`, furniture is `<label>_<n>` (`desk_1`, `desk_chair_2`,
# `sofa_1`), places are `plaza`, `well`, `shore_<n>`. A door counts when the building it leads to
# serves the need, since going through it is how the agent reaches that furniture.
NEED_KEYWORDS: dict[str, frozenset[str]] = {
    "focus": frozenset({"desk", "office", "study", "whiteboard"}),
    "rest": frozenset({"sofa", "bed", "home", "shore"}),
    "quiet": frozenset({"shore", "home", "bed"}),
}


@dataclass(frozen=True)
class ChoiceGuidance:
    """How to present one perception's entities to a model, and which pairs to leave out."""

    # Entity ids, most goal-relevant first, then nearest, then engine order.
    order: tuple[str, ...]
    # Horizontal distance from the agent to each entity, in metres.
    distances: Mapping[str, float]
    goal_relevant: frozenset[str]
    # (verb, targetId) pairs the model may not output for this perception.
    excluded: frozenset[tuple[str, str]]
    # Every allowed targeted (verb, targetId) pair, best first. `wait` is implied, after these.
    # Required: an empty tuple makes the grammar offer only wait.
    options: tuple[tuple[str, str], ...]


# Verbs that act on a target, in the order tier 1 tries them. A need for rest puts rest first.
_ACTING_VERBS = ("sit", "use", "rest", "approach")
_RESTING_ACTING_VERBS = ("rest", "sit", "use", "approach")
_RESTING_NEEDS = frozenset({"rest", "quiet"})
# Verbs that hold the agent at its target until the next intent.
_HOLDING_VERBS = frozenset({"sit", "use", "rest"})
# Id prefixes of portals: using one moves the agent to another scene.
_PORTAL_PREFIXES = ("door_", "exit_")
# Verbs that count as having been to a target.
_VISITING_VERBS = frozenset({"approach", "use", "sit", "rest"})


def _horizontal_distance(a: Mapping[str, float], b: Mapping[str, float]) -> float:
    return hypot(a["x"] - b["x"], a["z"] - b["z"])


def _id_words(entity_id: str) -> set[str]:
    return {part for part in entity_id.lower().split("_") if part and not part.isdigit()}


def is_goal_relevant(entity_id: str, needs: Sequence[str]) -> bool:
    """True when a word in the entity's id serves one of the goal's needs."""
    words = _id_words(entity_id)
    return any(words & NEED_KEYWORDS.get(need, frozenset()) for need in needs)


def _since_entry(
    observation: Mapping[str, Any], history: Sequence[DecisionRecord]
) -> list[DecisionRecord]:
    """Decisions since the agent entered the scene it is in now, oldest first."""
    scene_id = observation["scene"]["id"]
    since_entry: list[DecisionRecord] = []
    for record in reversed(history):
        if record.scene_id != scene_id:
            break
        since_entry.insert(0, record)
    return since_entry


def visited_targets(
    observation: Mapping[str, Any], history: Sequence[DecisionRecord]
) -> frozenset[str]:
    """Targets the agent chose to go to, sit on, use or rest on since entering its current scene.

    A choice counts even if the walk was interrupted: history records decisions, not arrivals.
    """
    return frozenset(
        record.target_id
        for record in _since_entry(observation, history)
        if record.target_id is not None and record.verb in _VISITING_VERBS
    )


def rank_options(
    choices: Mapping[str, Sequence[str]],
    order: Sequence[str],
    goal_relevant: frozenset[str],
    visited: frozenset[str],
    needs: Sequence[str],
    distances: Mapping[str, float] | None = None,
    walking_to: str | None = None,
) -> tuple[tuple[str, str], ...]:
    """Put the allowed pairs in one list, best first (module docstring, "Ranked options").

    `choices` maps each verb to its allowed targets; `order` is the entity ranking. With nothing
    goal-relevant in view, only approaches remain allowed (see `exploring_exclusions`) and they
    are ranked unvisited first, then `walking_to` (the walk under way), then farthest first.
    """
    position = {entity_id: index for index, entity_id in enumerate(order)}
    allowed = [
        (verb, target)
        for verb, targets in choices.items()
        for target in targets
    ]
    if not goal_relevant and allowed and all(verb == "approach" for verb, _ in allowed):
        far = distances or {}
        return tuple(
            sorted(
                allowed,
                key=lambda pair: (
                    0 if pair[1] not in visited else 1 if pair[1] == walking_to else 2,
                    -far.get(pair[1], 0.0),
                    position.get(pair[1], len(position)),
                ),
            )
        )
    acting = _RESTING_ACTING_VERBS if _RESTING_NEEDS & set(needs) else _ACTING_VERBS
    verb_rank = {verb: index for index, verb in enumerate(acting)}

    def tier(pair: tuple[str, str]) -> int:
        verb, target = pair
        if target in goal_relevant and verb in verb_rank:
            return 2 if verb == "approach" and target in visited else 0
        if verb == "approach" and target not in visited:
            return 1
        return 2

    return tuple(
        sorted(
            allowed,
            key=lambda pair: (
                tier(pair),
                verb_rank.get(pair[0], len(verb_rank)),
                position.get(pair[1], len(position)),
            ),
        )
    )


def walk_under_way(
    observation: Mapping[str, Any], history: Sequence[DecisionRecord]
) -> str | None:
    """The last decision's target, when it was an approach in this scene that moved the agent.

    The agent itself must have moved: `outcome.changed` alone also counts a target that moved while
    the agent stood still, which would keep the agent on a failed approach instead of exploring.
    """
    since_entry = _since_entry(observation, history)
    if not since_entry:
        return None
    last = since_entry[-1]
    if last.verb == "approach" and last.outcome.moved_distance >= MOVE_EPSILON:
        return last.target_id
    return None


def reachable_relevant(
    choices: Mapping[str, Sequence[str]], goal_relevant: frozenset[str]
) -> frozenset[str]:
    """Goal-relevant targets with at least one allowed pair left."""
    return frozenset(
        target for targets in choices.values() for target in targets if target in goal_relevant
    )


def exploring_exclusions(
    observation: Mapping[str, Any], guidance: ChoiceGuidance
) -> frozenset[tuple[str, str]]:
    """With nothing goal-relevant in view that the agent can still act on, every allowed pair
    except `approach`, if some approach is allowed; else nothing. Leaving these out is what makes
    the agent explore."""
    choices = grounded_choices(observation, guidance)
    if reachable_relevant(choices, guidance.goal_relevant):
        return frozenset()
    if not choices.get("approach"):
        return frozenset()
    return frozenset(
        (verb, target)
        for verb, targets in choices.items()
        if verb != "approach"
        for target in targets
    )


def _blocked(record: DecisionRecord) -> bool:
    """True when an approach brought the agent no closer to a target it had not reached."""
    outcome = record.outcome
    if record.verb != "approach":
        return False
    before, after = outcome.target_distance_before, outcome.target_distance_after
    if before is None or after is None:
        return False
    return after > ARRIVAL_RADIUS and before - after < MOVE_EPSILON


def out_of_reach_pairs(
    observation: Mapping[str, Any], latency_seconds: float
) -> frozenset[tuple[str, str]]:
    """Pairs whose target will be beyond the engine's reach where the avatar is predicted to be
    when the intent executes: its position moved along its current velocity for
    `latency_seconds`."""
    position = observation["self"]["position"]
    velocity = observation["self"]["velocity"]
    predicted = {
        "x": position["x"] + velocity["x"] * latency_seconds,
        "z": position["z"] + velocity["z"] * latency_seconds,
    }
    return frozenset(
        (verb, entity["id"])
        for entity in observation["visibleEntities"]
        if _horizontal_distance(predicted, entity["position"]) > REACH_RADIUS
        for verb in (*_REACHING_VERBS, "look_at")
    )


def excluded_pairs(
    observation: Mapping[str, Any],
    history: Sequence[DecisionRecord],
    distances: Mapping[str, float],
    goal_relevant: frozenset[str] = frozenset(),
) -> frozenset[tuple[str, str]]:
    """The (verb, target) pairs repeating which cannot produce anything new (module docstring)."""
    excluded: set[tuple[str, str]] = set()
    since_entry = _since_entry(observation, history)
    if since_entry:
        last = since_entry[-1]
        holding_goal = (
            last.verb in _HOLDING_VERBS
            and last.target_id is not None
            and not last.target_id.startswith(_PORTAL_PREFIXES)
            and last.target_id in goal_relevant
            and distances.get(last.target_id, HOLD_RADIUS + 1) <= HOLD_RADIUS
        )
        if last.target_id is not None and not last.outcome.changed and not holding_goal:
            excluded.add((last.verb, last.target_id))
    for record in since_entry:
        if record.verb == "look_at" and record.target_id is not None:
            excluded.add(("look_at", record.target_id))
        if record.target_id is not None and _blocked(record):
            excluded.update((verb, record.target_id) for verb in _REACHING_VERBS)

    for entity_id, distance in distances.items():
        if distance <= ARRIVAL_RADIUS:
            excluded.add(("approach", entity_id))
    return frozenset(excluded)


def guide(
    observation: Mapping[str, Any],
    needs: Sequence[str],
    history: Sequence[DecisionRecord],
    latency_seconds: float = 0.0,
) -> ChoiceGuidance:
    """Rank one perception's entities for the goal's `needs` and work out what the model may not
    repeat. `latency_seconds` is how long the decision is expected to take; the reach guard
    predicts the avatar's position that far ahead."""
    position = observation["self"]["position"]
    entities = list(observation["visibleEntities"])
    distances = {
        entity["id"]: _horizontal_distance(position, entity["position"]) for entity in entities
    }
    relevant = frozenset(
        entity["id"] for entity in entities if is_goal_relevant(entity["id"], needs)
    )
    ranked = sorted(
        enumerate(entities),
        key=lambda item: (item[1]["id"] not in relevant, distances[item[1]["id"]], item[0]),
    )
    guidance = ChoiceGuidance(
        order=tuple(entity["id"] for _, entity in ranked),
        distances=distances,
        goal_relevant=relevant,
        excluded=excluded_pairs(observation, history, distances, relevant)
        | out_of_reach_pairs(observation, latency_seconds),
        options=(),
    )
    guidance = replace(
        guidance, excluded=guidance.excluded | exploring_exclusions(observation, guidance)
    )
    choices = grounded_choices(observation, guidance)
    options = rank_options(
        choices,
        guidance.order,
        reachable_relevant(choices, relevant),
        visited_targets(observation, history),
        needs,
        distances,
        walk_under_way(observation, history),
    )
    return replace(guidance, options=options)
