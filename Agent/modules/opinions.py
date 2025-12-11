#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict
from datetime import datetime


@dataclass
class PersonOpinion:
    trust: float
    liking: float
    last_interaction_ts: float


@dataclass
class PlaceOpinion:
    satisfaction: float  # -1..1
    last_visit_ts: float
    category: str


class OpinionsStore:
    """
    per-agent opinions for people and places with simple update rules and cooldown.
    comments are lowercase.
    """

    def __init__(self) -> None:
        self.people: Dict[str, PersonOpinion] = {}
        self.places: Dict[str, PlaceOpinion] = {}

    # compatibility helpers expected by other modules
    def get_person_opinion(self, person_id: str) -> PersonOpinion | None:
        return self.people.get(str(person_id))

    def update_person_opinion(self, person_id: str, trust_delta: float = 0.0, liking_delta: float = 0.0, _ts=None) -> PersonOpinion:
        return self.update_person(person_id, trust_delta=trust_delta, liking_delta=liking_delta)

    def update_place_opinion(self, place_id: str, satisfaction_delta: float, _reason: str = "") -> PlaceOpinion:
        return self.update_place(place_id, category=self.places.get(str(place_id), PlaceOpinion(0.0, 0.0, "unknown")).category if str(place_id) in self.places else "unknown", satisfaction_delta=satisfaction_delta)

    def update_person(self, person_id: str, trust_delta: float = 0.0, liking_delta: float = 0.0) -> PersonOpinion:
        now = datetime.utcnow().timestamp()
        po = self.people.get(str(person_id))
        if not po:
            po = PersonOpinion(trust=0.5, liking=0.5, last_interaction_ts=now)
        po.trust = max(0.0, min(1.0, po.trust + trust_delta))
        po.liking = max(0.0, min(1.0, po.liking + liking_delta))
        po.last_interaction_ts = now
        self.people[str(person_id)] = po
        return po

    def update_place(self, place_id: str, category: str, satisfaction_delta: float) -> PlaceOpinion:
        now = datetime.utcnow().timestamp()
        pl = self.places.get(str(place_id))
        if not pl:
            pl = PlaceOpinion(satisfaction=0.0, last_visit_ts=now, category=category)
        pl.satisfaction = max(-1.0, min(1.0, pl.satisfaction + satisfaction_delta))
        pl.last_visit_ts = now
        self.places[str(place_id)] = pl
        return pl

    def get_place_bias(self, place_id: str) -> float:
        pl = self.places.get(str(place_id))
        return pl.satisfaction if pl else 0.0

    def get_all_opinions_summary(self) -> Dict[str, Dict[str, float]]:
        # compact summary for json situation card
        people_summary = {pid: {"trust": op.trust, "liking": op.liking} for pid, op in self.people.items()}
        places_summary = {pid: {"satisfaction": op.satisfaction, "category": op.category} for pid, op in self.places.items()}
        return {"people": people_summary, "places": places_summary}



