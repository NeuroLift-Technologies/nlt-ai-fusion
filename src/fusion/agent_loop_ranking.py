"""Which choices a model sees first, and which it no longer sees (AGENT-LOOP-003 F3).

A 0.6B model at temperature 0 takes the first option it is offered, and prompt wording does not
change that (F2 measured it), so the bias is removed structurally:

- **Ranking.** Visible entities are presented most goal-relevant first, then nearest, with their
  distance and relevance, instead of in engine order. Relevance comes from the F2 goal's needs.
- **Anti-repeat.** Some (verb, target) pairs are dropped from what the model may output, because
  repeating them cannot produce anything new:
  1. the pair chosen last, when its outcome changed nothing (brief F3). Except sitting on, resting
     on or using a goal-relevant target the agent is already at: holding still there is the goal
     reached, not a stall, and the engine treats the repeat as a no-op (AvatarCharacter
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
from .agent_loop_memory import DecisionRecord

# The engine's arrival radius for a targeted move, in metres (AvatarCharacter.ApplyIntent).
ARRIVAL_RADIUS = 1.0

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
) -> tuple[tuple[str, str], ...]:
    """Put the allowed pairs in one list, best first (module docstring, "Ranked options").

    `choices` maps each verb to its allowed targets; `order` is the entity ranking.
    """
    position = {entity_id: index for index, entity_id in enumerate(order)}
    allowed = [
        (verb, target)
        for verb, targets in choices.items()
        for target in targets
    ]
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
            and distances.get(last.target_id, ARRIVAL_RADIUS + 1) <= ARRIVAL_RADIUS
        )
        if last.target_id is not None and not last.outcome.changed and not holding_goal:
            excluded.add((last.verb, last.target_id))
    for record in since_entry:
        if record.verb == "look_at" and record.target_id is not None:
            excluded.add(("look_at", record.target_id))

    for entity_id, distance in distances.items():
        if distance <= ARRIVAL_RADIUS:
            excluded.add(("approach", entity_id))
    return frozenset(excluded)


def guide(
    observation: Mapping[str, Any],
    needs: Sequence[str],
    history: Sequence[DecisionRecord],
) -> ChoiceGuidance:
    """Rank one perception's entities for the goal's `needs` and work out what the model may not
    repeat."""
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
        excluded=excluded_pairs(observation, history, distances, relevant),
        options=(),
    )
    options = rank_options(
        grounded_choices(observation, guidance),
        guidance.order,
        relevant,
        visited_targets(observation, history),
        needs,
    )
    return replace(guidance, options=options)
