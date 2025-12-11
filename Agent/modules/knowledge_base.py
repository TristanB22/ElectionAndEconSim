#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime


@dataclass
class KnownEntity:
    entity_id: str
    kind: str  # place|firm|person|channel|role
    source: str  # purchase|visit|social|search|message
    confidence: float
    first_seen_ts: float
    last_seen_ts: float
    attrs: Dict[str, str] = field(default_factory=dict)  # e.g., role: doctor; capabilities: milk,eggs


class AgentKnowledgeBase:
    """
    simple per-agent knowledge base with confidence tracking and role/capability notes.
    comments are lowercase.
    """

    def __init__(self) -> None:
        self._by_id: Dict[str, KnownEntity] = {}
        self._by_kind: Dict[str, Dict[str, KnownEntity]] = {}

    def knows(self, entity_id: str, min_conf: float = 0.5) -> bool:
        ke = self._by_id.get(str(entity_id))
        return bool(ke and ke.confidence >= min_conf)

    def add(self, entity_id: str, kind: str, source: str, confidence: float = 0.7, attrs: Optional[Dict[str, str]] = None) -> KnownEntity:
        now = datetime.utcnow().timestamp()
        eid = str(entity_id)
        ke = self._by_id.get(eid)
        if ke:
            # update existing
            ke.last_seen_ts = now
            ke.source = source or ke.source
            ke.confidence = max(ke.confidence, float(confidence))
            if attrs:
                ke.attrs.update(attrs)
            return ke
        ke = KnownEntity(
            entity_id=eid,
            kind=kind,
            source=source,
            confidence=float(confidence),
            first_seen_ts=now,
            last_seen_ts=now,
            attrs=dict(attrs or {}),
        )
        self._by_id[eid] = ke
        self._by_kind.setdefault(kind, {})[eid] = ke
        return ke

    def list_by_kind(self, kind: str, min_conf: float = 0.5) -> List[KnownEntity]:
        out: List[KnownEntity] = []
        for ke in self._by_kind.get(kind, {}).values():
            if ke.confidence >= min_conf:
                out.append(ke)
        return out

    # compatibility helpers expected by agent
    def list_all_known_entities(self) -> List[Dict[str, str]]:
        out: List[Dict[str, str]] = []
        for ke in self._by_id.values():
            out.append({
                "entity_id": ke.entity_id,
                "kind": ke.kind,
                "source": ke.source,
                "confidence": f"{ke.confidence:.2f}",
            })
        return out

    def add_role(self, person_id: str, role_name: str, source: str = "social", confidence: float = 0.7) -> None:
        self.add(person_id, kind="role", source=source, confidence=confidence, attrs={"role": role_name})

    def note_capability(self, entity_id: str, capability: str, source: str = "purchase", confidence: float = 0.7) -> None:
        ke = self.add(entity_id, kind="firm", source=source, confidence=confidence)
        caps = ke.attrs.get("capabilities", "")
        parts = [p.strip() for p in caps.split(",") if p.strip()] if caps else []
        if capability not in parts:
            parts.append(capability)
        ke.attrs["capabilities"] = ",".join(parts)



