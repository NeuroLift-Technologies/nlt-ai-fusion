"""Which choices a model sees first, and which it no longer sees (AGENT-LOOP-003 F3).

A 0.6B model at temperature 0 takes the first option it is offered, and prompt wording does not
change that (F2 measured it), so the bias is removed structurally.

Only five rules drop a (verb, target) pair: anti-repeat rules 1-3, the reach guard and blocked
targets, each because the pair cannot produce anything new or cannot be carried out. Everything
else that a visible target affords is offered, in ranked order; in particular, holding actions on
targets that do not serve the goal are demoted, never dropped (Josh, 2026-10-28, decision 2).

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
  3. everything else: approaches first, then `sit`, `use` and `rest`, then `look_at` (Josh,
     2026-10-28: once every visible target is visited, option 1 had been a holding verb on a
     non-goal target, `use well` 45 times in 61). Approaches go least recently visited first,
     then farthest, because moving reveals new entities. Within each of the three groups a pair
     not yet chosen since entering the scene comes before one already chosen, whatever its
     outcome, which breaks up alternating between two pairs (`use well`, `use plaza`, ...) that
     rule 1 alone lets through.
  `wait` comes last. The model input lists the options in this order and the output grammar offers
  them in this order. The F4 baseline takes the first one. Nothing in tier 3 is left out for
  being in tier 3: an avatar may still choose to use the well (Josh, 2026-10-28: "demote them;
  never forbid them").
- **Explore when the goal is not in view** (Josh, 2026-10-29: "if it has no goal then it should
  explore"). Exploring is a ranking, not a filter: it applies while no visible entity is
  goal-relevant, or none the agent can still act on (each is out of reach or blocked), and ends as
  soon as one is. While it applies, tier 1 is empty and tier 2 goes farthest first, so each move
  carries the agent toward the edge of what it can perceive and new places come into view. The walk
  already under way (the last approach, still moving the agent) heads tier 3, so a walk is finished
  before another visited target is picked; without this the agent turned back halfway between two
  landmarks. No new verb and no reliance on the engine's wander: the moves the ranking puts first
  are targeted `approach`es.
- **Reach guard.** The engine refuses any intent whose target is beyond 30 m of the avatar's live
  position when it executes (IntentIngress.RecheckTarget), while perception lists entities out to
  25 m. A walking avatar keeps moving while the decision is made, so a target perceived at 24 m
  can be 31 m away at execution (measured: 24.1 m, 1.4 m/s, a 7 s decision). Pairs whose target
  would be out of reach at the position predicted from the avatar's velocity and the expected
  decision time are left out. A goal-relevant target that is out of reach does not stop the agent
  exploring.
- **Blocked targets.** Two decisions on a target (approach, sit, use or rest) after each of
  which the agent is no closer to and no farther from it, still short of it, with nobody else
  holding it, mean the target cannot be reached from here (measured: the agent stopped 7.6 m
  short of a raised doorway, then chose `use` on it 9 times). One such decision is not enough:
  with a model deciding, the next perception can come before the walk has started. Every pair on
  that target except `look_at` is left out for the rest of the scene, within the remembered
  history. Ending up farther away is not counted: with a model taking seconds to decide, the
  wander after a `look_at` can carry the agent off before the approach executes, and counting
  that left only the well at the spawn.

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

# How far from an entity's position an agent can stand while it sits on, uses or rests on it: the
# engine walks it to an anchor beside the entity (measured 1.9-2.0 m while using the well).
HOLDING_REACH = 3.0

# How many decisions on one target must leave the agent stuck short of it before it counts as
# blocked. One can be timing: the next perception came 290 ticks after `use plaza`, before the
# walk had started.
BLOCKED_AFTER = 2

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


def last_visits(
    observation: Mapping[str, Any], history: Sequence[DecisionRecord]
) -> dict[str, int]:
    """Targets the agent chose to go to, sit on, use or rest on since entering its current scene,
    each with the position of its latest such decision (higher is more recent).

    A choice counts even if the walk was interrupted: history records decisions, not arrivals.
    """
    return {
        record.target_id: index
        for index, record in enumerate(_since_entry(observation, history))
        if record.target_id is not None and record.verb in _VISITING_VERBS
    }


def chosen_pairs(
    observation: Mapping[str, Any], history: Sequence[DecisionRecord]
) -> frozenset[tuple[str, str]]:
    """(verb, target) pairs chosen since the agent entered its current scene, whatever came of
    them."""
    return frozenset(
        (record.verb, record.target_id)
        for record in _since_entry(observation, history)
        if record.target_id is not None
    )


def rank_options(
    choices: Mapping[str, Sequence[str]],
    order: Sequence[str],
    goal_relevant: frozenset[str],
    visits: Mapping[str, int],
    needs: Sequence[str],
    distances: Mapping[str, float] | None = None,
    walking_to: str | None = None,
    chosen: frozenset[tuple[str, str]] = frozenset(),
) -> tuple[tuple[str, str], ...]:
    """Put the allowed pairs in one list, best first (module docstring, "Ranked options").

    `choices` maps each verb to its allowed targets; `order` is the entity ranking. `visits`
    maps each target visited since entering the scene to how recently (higher is later),
    `walking_to` is the walk under way and `chosen` the pairs already chosen in this scene. With
    nothing goal-relevant in `goal_relevant`, unvisited targets are approached farthest first.
    """
    position = {entity_id: index for index, entity_id in enumerate(order)}
    far = distances or {}
    acting = _RESTING_ACTING_VERBS if _RESTING_NEEDS & set(needs) else _ACTING_VERBS
    verb_rank = {verb: index for index, verb in enumerate(acting)}

    def key(pair: tuple[str, str]) -> tuple[Any, ...]:
        # Smaller sorts first. Element 0 is the tier; keys of different tiers, and in tier 3 of
        # different groups (element 1), never get as far as comparing their later elements.
        verb, target = pair
        in_order = position.get(target, len(position))
        if target in goal_relevant and verb in verb_rank and not (
            verb == "approach" and target in visits
        ):
            # Tier 1: verb order for the need, then entity ranking.
            return (0, verb_rank[verb], in_order)
        if verb == "approach" and target not in visits:
            # Tier 2: farthest first while exploring, else entity ranking.
            return (1, -far.get(target, 0.0) if not goal_relevant else 0.0, in_order)
        if verb == "approach":
            # Tier 3, approaches: the walk under way, then not yet chosen, then least recently
            # visited, then farthest, then entity ranking.
            return (
                2,
                0,
                target != walking_to,
                pair in chosen,
                visits[target],
                -far.get(target, 0.0),
                in_order,
            )
        # Tier 3, holding verbs (group 1) then look_at (group 2): not yet chosen, then verb
        # order, then entity ranking. The False keeps the shape of the approach key.
        group = 1 if verb in _HOLDING_VERBS else 2
        return (2, group, False, pair in chosen, verb_rank.get(verb, len(verb_rank)), in_order)

    return tuple(
        sorted(
            ((verb, target) for verb, targets in choices.items() for target in targets),
            key=key,
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


def _blocked(record: DecisionRecord) -> bool:
    """True when a decision that needed the agent to get to its target left the agent neither
    closer to nor farther from it, short of it: beyond the arrival radius for `approach`, beyond
    `HOLDING_REACH` for `sit`, `use` and `rest`, which hold the agent at an anchor beside it.
    Farther means something else moved it, such as the wander after an earlier `look_at` while
    this decision was still being made; that says nothing about the target. Nor does a target
    someone else took meanwhile: the engine refuses to sit on, use or rest on it while it is
    held, and it may be free again later."""
    outcome = record.outcome
    if record.verb not in _REACHING_VERBS or outcome.target_taken:
        return False
    before, after = outcome.target_distance_before, outcome.target_distance_after
    if before is None or after is None:
        return False
    short_of = ARRIVAL_RADIUS if record.verb == "approach" else HOLDING_REACH
    return after > short_of and abs(before - after) < MOVE_EPSILON


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
    stalls: dict[str, int] = {}
    for record in since_entry:
        if record.verb == "look_at" and record.target_id is not None:
            excluded.add(("look_at", record.target_id))
        if record.target_id is not None and _blocked(record):
            stalls[record.target_id] = stalls.get(record.target_id, 0) + 1
            if stalls[record.target_id] >= BLOCKED_AFTER:
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
    choices = grounded_choices(observation, guidance)
    options = rank_options(
        choices,
        guidance.order,
        reachable_relevant(choices, relevant),
        last_visits(observation, history),
        needs,
        distances,
        walk_under_way(observation, history),
        chosen_pairs(observation, history),
    )
    return replace(guidance, options=options)
