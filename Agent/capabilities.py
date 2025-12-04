#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List

from Agent.modules.knowledge_base import AgentKnowledgeBase


@dataclass
class Capability:
    op: str
    target_id: str
    props: Dict[str, Any]


def get_capability_context(agent, world) -> Dict[str, List[Capability]]:
    caps: Dict[str, List[Capability]] = {}
    # base ops always available
    for op in ("Communicate", "Consume", "Transfer", "Work", "Exchange", "Travel"):
        caps.setdefault(op, [])

    # ensure knowledge base present
    kb: AgentKnowledgeBase = getattr(agent, 'knowledge', None) or AgentKnowledgeBase()
    agent.knowledge = kb

    # discover exchange targets gated by knowledge
    for obj_id, aff in world.affordances.find("Exchange"):
        if kb.knows(obj_id, min_confidence=0.5):
            caps["Exchange"].append(Capability("Exchange", obj_id, aff.props))
    # travel targets gated by knowledge
    for obj_id, aff in world.affordances.find("TravelTarget"):
        if kb.knows(obj_id, min_confidence=0.3):
            caps["Travel"].append(Capability("Travel", obj_id, aff.props))
    # employs (future)
    for obj_id, aff in world.affordances.find("Employs"):
        caps["Work"].append(Capability("Work", obj_id, aff.props))
    
    # include known roles/capabilities of people/places
    known_roles = kb.list_by_kind("role", min_confidence=0.7)
    for role_entity in known_roles:
        caps.setdefault("Interact", []).append(Capability("Interact", role_entity.entity_id, {"role": role_entity.entity_id}))
    
    return caps


