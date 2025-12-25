#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List, Tuple


@dataclass
class Affordance:
    kind: str
    props: Dict[str, Any]


class AffordanceIndex:
    """
    Build affordances from the thin world state. Rebuild each tick.
    """

    def __init__(self, world) -> None:
        self.world = world
        self.by_id: Dict[str, List[Affordance]] = {}
        self._build()

    def _build(self) -> None:
        # Exchange: for each firm that has prices, expose an Exchange affordance
        for firm_id, fs in self.world.state.firm_states.items():
            catalog = fs.get("prices", {})
            if catalog:
                self.by_id.setdefault(firm_id, []).append(
                    Affordance("Exchange", {"catalog": catalog, "pricing": "posted"})
                )
        # TravelTarget: allow all known locations (teleport world today)
        for loc_id in getattr(self.world, "locations", {}).keys():
            self.by_id.setdefault(loc_id, []).append(Affordance("TravelTarget", {}))
        # Also allow travel to firm ids (as locations) for simplicity
        for firm_id in self.world.state.firm_states.keys():
            self.by_id.setdefault(firm_id, []).append(Affordance("TravelTarget", {}))

    def list(self, object_id: str) -> List[Affordance]:
        return self.by_id.get(object_id, [])

    def find(self, kind: str) -> List[Tuple[str, Affordance]]:
        return [
            (obj_id, a)
            for obj_id, arr in self.by_id.items()
            for a in arr
            if a.kind == kind
        ]


