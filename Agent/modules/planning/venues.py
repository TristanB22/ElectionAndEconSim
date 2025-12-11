#!/usr/bin/env python3
"""
Venue selection and discovery helpers.
"""

from __future__ import annotations

import math
import random
from typing import Any, Dict, Optional, Tuple


def _match_score(name: str, category: str) -> float:
	name_lower = name.lower()
	category_lower = category.lower()
	keywords = {
		"grocery": ["market", "grocery", "super", "food"],
		"retail": ["mall", "store", "shop", "retail"],
		"exercise": ["gym", "fitness", "park", "trail"],
		"social": ["bar", "cafe", "restaurant", "club"],
		"medical": ["clinic", "hospital", "doctor", "health"],
		"pharmacy": ["pharmacy", "drug"],
		"leisure": ["cinema", "theater", "museum", "park"],
	}
	score = 0.0
	for token in keywords.get(category_lower, []):
		if token in name_lower:
			score += 1.0
	return score


def _knowledge_candidates(agent, category: str) -> Dict[str, Any]:
	if not hasattr(agent, "knowledge") or agent.knowledge is None:
		return {}
	entries = agent.knowledge.list_by_kind("place", min_conf=0.3)
	candidates = {}
	for entry in entries:
		score = _match_score(entry.entity_id, category)
		if entry.attrs:
			caps = entry.attrs.get("capabilities", "")
			if category.lower() in (caps or "").lower():
				score += 1.5
		if score > 0:
			candidates[entry.entity_id] = {"score": score, "entry": entry}
	return candidates


def choose_place(
	agent,
	category: str,
	rng: random.Random,
	allow_discovery: bool = False,
	discovery_probability: float = 0.0,
) -> Optional[str]:
	candidates = _knowledge_candidates(agent, category)
	if candidates:
		total = sum(c["score"] for c in candidates.values())
		choice = rng.random() * total
		accum = 0.0
		for place_id, meta in candidates.items():
			accum += meta["score"]
			if choice <= accum:
				return place_id
	if allow_discovery and rng.random() < discovery_probability:
		# placeholder: discovery not yet implemented; return None to signal skip
		return None
	return None
