"""Which choices a model sees first, and which it no longer sees (AGENT-LOOP-003 F3).

A 0.6B model at temperature 0 takes the first option it is offered, and prompt wording does not
change that (F2 measured it), so the bias is removed structurally:

- **Ranking.** Visible entities are presented most goal-relevant first, then nearest, with their
  distance and relevance, instead of in engine order. Relevance comes from the F2 goal's needs.
- **Anti-repeat.** Some (verb, target) pairs are dropped from what the model may output, because
  repeating them cannot produce anything new:
  1. the pair chosen last, when its outcome changed nothing (brief F3);
  2. `approach X` when the agent already stands within X's arrival radius (Joshua, 2026-10-28,
     brief §9.2): the engine counts it as arrived at once and the avatar wanders off;
  3. `look_at X` when the agent already looked at X since entering this scene, within the
     remembered history (F1, 8 decisions by default). Looking reveals nothing the
     perception did not already carry, and the wander that follows a look always moves the agent,
     so rule 1 alone never catches a look_at loop.

`wait` is never dropped, so a model always has something to choose. Exclusions are computed from
the current perception and the F1 history only; history is cleared when the engine restarts, and
rules 1 and 3 count only decisions made since the agent entered its current scene, so going through
a door resets them.

Everything here shapes the model's prompt and output grammar. Nothing is sent to the world engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import hypot
from typing import Any, Mapping, Sequence

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


def _horizontal_distance(a: Mapping[str, float], b: Mapping[str, float]) -> float:
    return hypot(a["x"] - b["x"], a["z"] - b["z"])


def _id_words(entity_id: str) -> set[str]:
    return {part for part in entity_id.lower().split("_") if part and not part.isdigit()}


def is_goal_relevant(entity_id: str, needs: Sequence[str]) -> bool:
    """True when a word in the entity's id serves one of the goal's needs."""
    words = _id_words(entity_id)
    return any(words & NEED_KEYWORDS.get(need, frozenset()) for need in needs)


def excluded_pairs(
    observation: Mapping[str, Any],
    history: Sequence[DecisionRecord],
    distances: Mapping[str, float],
) -> frozenset[tuple[str, str]]:
    """The (verb, target) pairs repeating which cannot produce anything new (module docstring)."""
    scene_id = observation["scene"]["id"]
    excluded: set[tuple[str, str]] = set()

    # Decisions since the agent entered the scene it is in now, oldest first.
    since_entry: list[DecisionRecord] = []
    for record in reversed(history):
        if record.scene_id != scene_id:
            break
        since_entry.insert(0, record)

    if since_entry:
        last = since_entry[-1]
        if last.target_id is not None and not last.outcome.changed:
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
    return ChoiceGuidance(
        order=tuple(entity["id"] for _, entity in ranked),
        distances=distances,
        goal_relevant=relevant,
        excluded=excluded_pairs(observation, history, distances),
    )
