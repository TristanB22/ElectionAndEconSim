#!/usr/bin/env python3
"""
Helpers to derive planning-relevant features from an agent.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

from Agent.modules.planning.strata import build_stratum_features
from Agent.modules.planning.distributions import get_distribution_provider


def _gender_to_sex_code(gender: Optional[str]) -> Optional[int]:
	if not gender:
		return None
	gender_lower = gender.lower()
	if gender_lower.startswith("m"):
		return 1
	if gender_lower.startswith("f"):
		return 2
	return None


def _employment_to_telfs(agent) -> Optional[int]:
	try:
		employment = agent.get_recent_employment()
		if employment and any(employment.values()):
			return 1
	except Exception:
		pass
	# fall back to economic traits if available
	status = getattr(getattr(agent.l2_data, "work", None), "employment_status", None) if getattr(agent, "l2_data", None) else None
	if status:
		status_lower = status.lower()
		if "employed" in status_lower or "full" in status_lower or "part" in status_lower:
			return 1
		if "unemployed" in status_lower:
			return 3
		if "retired" in status_lower or "student" in status_lower or "not employed" in status_lower:
			return 4
	return None


def _hours_from_agent(agent) -> Optional[int]:
	work = getattr(agent.l2_data, "work", None) if getattr(agent, "l2_data", None) else None
	if work:
		hours = getattr(work, "hours_per_week", None)
		if hours:
			try:
				return int(hours)
			except (TypeError, ValueError):
				pass
	return None


def _education_to_code(education: Optional[str]) -> Optional[int]:
	if not education:
		return None
	edu_lower = education.lower()
	if "less than" in edu_lower or "no diploma" in edu_lower:
		return 36
	if "high school" in edu_lower:
		return 39
	if "associate" in edu_lower or "some college" in edu_lower:
		return 40
	if "bachelor" in edu_lower or "college" in edu_lower or "graduate" in edu_lower:
		return 42
	return None


def _income_to_weekly(income_str: Optional[str]) -> Optional[int]:
	if not income_str:
		return None
	digits = re.sub(r"[^0-9]", "", str(income_str))
	if not digits:
		return None
	try:
		annual = int(digits)
		if annual <= 0:
			return None
		return max(int(annual / 52), 1)
	except ValueError:
		return None


def stratum_id_for_agent(agent) -> Optional[int]:
	"""Resolve the best-fit stratum id for the agent."""
	age = agent.get_age() if hasattr(agent, "get_age") else None
	sex_code = _gender_to_sex_code(agent.get_gender() if hasattr(agent, "get_gender") else None)
	telfs = _employment_to_telfs(agent)
	hours = _hours_from_agent(agent)
	children_count = agent.get_children_count() if hasattr(agent, "get_children_count") else None
	education_code = _education_to_code(agent.get_education() if hasattr(agent, "get_education") else None)
	income_weekly = _income_to_weekly(agent.get_income() if hasattr(agent, "get_income") else None)

	region = None  # TODO: map from agent location if available
	metro = None

	features = build_stratum_features(
		age,
		sex_code,
		telfs,
		hours,
		children_count,
		education_code,
		income_weekly,
		region,
		metro,
	)

	provider = get_distribution_provider()
	return provider.resolve_stratum_id(features.to_definition())


def strata_mixture_for_agent(agent, top_k: int = 5, temperature: float = 0.7):
	"""Return a softmax-weighted mixture of strata for this agent's features."""
	age = agent.get_age() if hasattr(agent, "get_age") else None
	sex_code = _gender_to_sex_code(agent.get_gender() if hasattr(agent, "get_gender") else None)
	telfs = _employment_to_telfs(agent)
	hours = _hours_from_agent(agent)
	children_count = agent.get_children_count() if hasattr(agent, "get_children_count") else None
	education_code = _education_to_code(agent.get_education() if hasattr(agent, "get_education") else None)
	income_weekly = _income_to_weekly(agent.get_income() if hasattr(agent, "get_income") else None)

	region = None
	metro = None

	features = build_stratum_features(
		age,
		sex_code,
		telfs,
		hours,
		children_count,
		education_code,
		income_weekly,
		region,
		metro,
	)
	provider = get_distribution_provider()
	return provider.resolve_strata_mixture(features.to_definition(), top_k=top_k, temperature=temperature)
