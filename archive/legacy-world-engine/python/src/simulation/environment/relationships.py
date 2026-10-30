"""
Relationship System

Tracks the social web between Sims.  Each pair of Sims that has
interacted at least once gets a ``RelationshipComponent`` stored on the
``RelationshipManager``, which in turn is owned by the ``WorldEngine``.

The component stores three floats (friendship, romance, familiarity) in
the 0-100 range plus an interaction counter, and offers a tiny
``interact()`` helper that grows the bonds incrementally.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .ecs import Component


class RelationshipComponent(Component):
    """Holds relationship data for a pair of Sims.

    The component is identified by two Sim IDs.  Pass either ID to
    :meth:`other_sim` to retrieve the partner.
    """

    def __init__(self, sim1_id: str, sim2_id: str):
        self._sim_a: str = sim1_id
        self._sim_b: str = sim2_id
        self.friendship: float = 0.0
        self.romance: float = 0.0
        self.familiarity: float = 0.0
        self.interaction_count: int = 0

    # -- queries --------------------------------------------------------------

    @property
    def sim_a(self) -> str:
        return self._sim_a

    @property
    def sim_b(self) -> str:
        return self._sim_b

    def other_sim(self, sim_id: str) -> Optional[str]:
        """Return the other Sim's ID in the pair, or ``None`` if *sim_id*
        is not part of this relationship."""
        if sim_id == self._sim_a:
            return self._sim_b
        if sim_id == self._sim_b:
            return self._sim_a
        return None

    def involves(self, sim_id: str) -> bool:
        return sim_id in (self._sim_a, self._sim_b)

    # -- mutation -------------------------------------------------------------

    def interact(self, interaction_type: str = "chat") -> None:
        """Record a social interaction and grow relationship metrics."""
        self.interaction_count += 1
        self.familiarity = min(100.0, self.familiarity + 8.0)
        # Friendship grows faster for positive social interactions,
        # slower for neutral / negative ones.
        if interaction_type in ("chat", "positive", "romantic"):
            gain = 5.0
        else:
            gain = 2.0
        self.friendship = min(100.0, self.friendship + gain)
        if interaction_type == "romantic":
            self.romance = min(100.0, self.romance + 6.0)

    # -- serialization --------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sim_a": self._sim_a,
            "sim_b": self._sim_b,
            "friendship": self.friendship,
            "romance": self.romance,
            "familiarity": self.familiarity,
            "interaction_count": self.interaction_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RelationshipComponent":
        comp = cls(data["sim_a"], data["sim_b"])
        comp.friendship = data.get("friendship", 0.0)
        comp.romance = data.get("romance", 0.0)
        comp.familiarity = data.get("familiarity", 0.0)
        comp.interaction_count = data.get("interaction_count", 0)
        return comp


class RelationshipManager:
    """In-memory store of all Sim-to-Sim relationships.

    Relationships are keyed by a *canonical* pair key (sorted Sim IDs)
    so that ``get_or_create("A", "B")`` and ``get_or_create("B", "A")``
    return the same component.
    """

    def __init__(self):
        self._relationships: Dict[Tuple[str, str], RelationshipComponent] = {}

    @staticmethod
    def _key(sim1_id: str, sim2_id: str) -> Tuple[str, str]:
        return tuple(sorted([sim1_id, sim2_id]))  # type: ignore[return-value]

    def get_or_create(self, sim1_id: str, sim2_id: str) -> RelationshipComponent:
        """Return the relationship component for the pair, creating it if needed."""
        if sim1_id == sim2_id:
            raise ValueError("A Sim cannot have a relationship with itself")
        key = self._key(sim1_id, sim2_id)
        if key not in self._relationships:
            self._relationships[key] = RelationshipComponent(sim1_id, sim2_id)
        return self._relationships[key]

    def get(self, sim1_id: str, sim2_id: str) -> Optional[RelationshipComponent]:
        """Return the relationship for the pair, or ``None`` if it doesn't exist."""
        key = self._key(sim1_id, sim2_id)
        return self._relationships.get(key)

    def get_all_for_sim(self, sim_id: str) -> List[RelationshipComponent]:
        """Return every relationship component that involves *sim_id*."""
        return [
            comp for comp in self._relationships.values()
            if comp.involves(sim_id)
        ]

    def all_relationships(self) -> List[RelationshipComponent]:
        """Return a list of all relationship components."""
        return list(self._relationships.values())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "relationships": [comp.to_dict() for comp in self._relationships.values()],
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        self._relationships.clear()
        for raw in data.get("relationships", []):
            comp = RelationshipComponent.from_dict(raw)
            key = self._key(comp.sim_a, comp.sim_b)
            self._relationships[key] = comp
