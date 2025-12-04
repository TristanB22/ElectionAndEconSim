#!/usr/bin/env python3
"""
Helpers to load ATUS-derived distributions for agent planning.
"""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Any, Dict, List, Tuple

from Database.managers.atus import get_atus_database_manager


class DistributionProvider:
	def __init__(self) -> None:
		self.db = get_atus_database_manager()
		self._strata_defs: List[Dict[str, Any]] | None = None
		self._operator_specs: Dict[str, Dict[str, Any]] | None = None
		self._hourly_mix_cache: Dict[int, Dict[int, Dict[int, List[Dict[str, Any]]]]] = {}
		self._duration_cache: Dict[int, Dict[int, Dict[str, Dict[str, Any]]]] = {}
		self._transition_cache: Dict[int, Dict[int, Dict[str, List[Dict[str, Any]]]]] = {}
		self._social_cache: Dict[int, Dict[int, Dict[str, Dict[str, Any]]]] = {}
		self._weekly_presence_cache: Dict[int, Dict[str, Dict[str, Any]]] = {}
		# Pre-load strata definitions on init to avoid repeated queries in parallel threads
		self.load_strata_definitions()

	def load_strata_definitions(self) -> List[Dict[str, Any]]:
		if self._strata_defs is not None:
			return self._strata_defs
		query = "SELECT id, name, definition FROM world_sim_atus.strata_def"
		result = self.db.execute_query(query, fetch=True)
		if not result.success:
			raise RuntimeError(f"Failed to load strata definitions: {result.error}")
		defs = result.data or []
		for row in defs:
			if row.get("definition") and isinstance(row["definition"], str):
				try:
					row["definition"] = json.loads(row["definition"])
				except Exception:
					pass
		self._strata_defs = defs
		return defs

	def resolve_stratum_id(self, features: Dict[str, str]) -> Optional[int]:
		"""
		Resolve stratum ID using hierarchical fallback matching.
		Prioritizes: sex, age_band, employment, then progressively relaxes other criteria.
		"""
		defs = self.load_strata_definitions()
		if not defs:
			return None
		
		# Core features that should always match if available
		core_features = ["sex", "age_band", "employment"]
		# Secondary features to relax in order
		secondary_features = ["hours_band", "children", "education", "income", "region", "metro"]
		
		# Try exact match first
		for entry in defs:
			definition = entry.get("definition") or {}
			if all(features.get(k) == definition.get(k) or features.get(k) == "unknown" for k in features):
				return entry["id"]
		
		# Progressive relaxation: keep core features, relax secondary
		for relax_count in range(len(secondary_features) + 1):
			required_keys = set(core_features + secondary_features[relax_count:])
			for entry in defs:
				definition = entry.get("definition") or {}
				match = True
				for key in required_keys:
					feat_val = features.get(key)
					def_val = definition.get(key)
					# Skip if feature is unknown
					if feat_val == "unknown" or feat_val is None:
						continue
					# Must match if both are known
					if def_val != feat_val:
						match = False
						break
				if match:
					return entry["id"]
		
		# Final fallback: find stratum with best sample size for the agent's sex and age_band
		sex_val = features.get("sex")
		age_val = features.get("age_band")
		candidates = []
		for entry in defs:
			definition = entry.get("definition") or {}
			if sex_val and definition.get("sex") == sex_val:
				if age_val and definition.get("age_band") == age_val:
					candidates.append(entry["id"])
		
		if candidates:
			# Return the first candidate (they're ordered by sample size typically)
			return candidates[0]
		
		# Absolute fallback: return a well-populated stratum (not stratum 1)
		return 5493  # This stratum has 8062 samples and good coverage

	def resolve_strata_mixture(self, features: Dict[str, str], top_k: int = 5, temperature: float = 0.7) -> List[Tuple[int, float]]:
		"""Return a softmax-weighted mixture over top_k matching strata.

		Scores strata by number of matching feature keys. Applies softmax over scores/temperature.
		"""
		defs = self.load_strata_definitions()
		if not defs:
			return []
		def score(defn: Dict[str, Any]) -> int:
			count = 0
			for k, v in features.items():
				if v is None or v == "unknown":
					continue
				if defn.get(k) == v:
					count += 1
			return count
		ranked = []
		for entry in defs:
			definition = entry.get("definition") or {}
			ranked.append((entry["id"], score(definition)))
		ranked.sort(key=lambda x: x[1], reverse=True)
		candidates = ranked[:max(1, top_k)]
		if not candidates:
			return []
		# softmax weights
		import math
		exps = [math.exp(s / max(0.1, temperature)) for _, s in candidates]
		total = sum(exps)
		weights = [e / total for e in exps]
		return [(sid, w) for (sid, _), w in zip(candidates, weights)]

	def get_mixed_hourly_mix(self, mixture: List[Tuple[int, float]]) -> Dict[int, Dict[int, Dict[str, float]]]:
		"""Weighted combination of hourly_mix across strata mixture.

		Returns structure: dow -> hour -> operator_group -> probability
		"""
		from collections import defaultdict
		acc: Dict[int, Dict[int, Dict[str, float]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
		for sid, w in mixture:
			mix = self.get_hourly_mix(sid)
			for dow, hours in mix.items():
				for hour, items in hours.items():
					for item in items:
						acc[dow][hour][item["operator_group"]] += w * float(item.get("probability") or 0.0)
		# normalize per dow/hour
		for dow, hours in acc.items():
			for hour, ops in hours.items():
				total = sum(ops.values())
				if total > 0:
					for k in list(ops.keys()):
						ops[k] = ops[k] / total
		return acc

	def get_mixed_duration_stats(self, mixture: List[Tuple[int, float]]) -> Dict[int, Dict[str, Dict[str, float]]]:
		"""Weighted combination of duration stats across strata mixture.

		Returns: dow -> operator_group -> {p50, mean}
		"""
		from collections import defaultdict
		acc: Dict[int, Dict[str, Dict[str, float]]] = defaultdict(lambda: defaultdict(lambda: {"p50": 0.0, "mean": 0.0}))
		for sid, w in mixture:
			stats = self.get_duration_stats(sid)
			for dow, ops in stats.items():
				for op, row in ops.items():
					p50 = float(row.get("p50") or row.get("mean") or 0.0)
					mean = float(row.get("mean") or p50)
					acc[dow][op]["p50"] += w * p50
					acc[dow][op]["mean"] += w * mean
		return acc

	def get_mixed_weekly_presence(self, mixture: List[Tuple[int, float]]) -> Dict[str, Dict[str, float]]:
		"""Weighted combination of weekly presence stats across strata mixture.

		Returns: operator_group -> {presence_rate, mean_minutes_per_week}
		"""
		from collections import defaultdict
		acc: Dict[str, Dict[str, float]] = defaultdict(lambda: {"presence_rate": 0.0, "mean_minutes_per_week": 0.0})
		for sid, w in mixture:
			wp = self.get_weekly_presence(sid)
			for op, row in wp.items():
				acc[op]["presence_rate"] += w * float(row.get("presence_rate") or 0.0)
				acc[op]["mean_minutes_per_week"] += w * float(row.get("mean_minutes_per_week") or 0.0)
		return acc

	def get_operator_specs(self) -> Dict[str, Dict[str, Any]]:
		if self._operator_specs is not None:
			return self._operator_specs
		query = """
			SELECT operator_group, default_location, typical_minutes_p50,
			       cooldown_days, weekly_quota, prereq_flags
			FROM world_sim_atus.operator_map
			GROUP BY operator_group
		"""
		result = self.db.execute_query(query, fetch=True)
		if not result.success:
			raise RuntimeError(f"Failed to load operator map: {result.error}")
		specs: Dict[str, Dict[str, Any]] = {}
		for row in result.data or []:
			prereq = row.get("prereq_flags")
			if prereq and isinstance(prereq, str):
				try:
					prereq = json.loads(prereq)
				except Exception:
					prereq = None
			specs[row["operator_group"]] = {
				"default_location": row.get("default_location"),
				"typical_minutes_p50": row.get("typical_minutes_p50"),
				"cooldown_days": row.get("cooldown_days"),
				"weekly_quota": row.get("weekly_quota"),
				"prereq_flags": prereq,
			}
		self._operator_specs = specs
		return specs

	def get_hourly_mix(self, stratum_id: int) -> Dict[int, Dict[int, List[Dict[str, Any]]]]:
		if stratum_id in self._hourly_mix_cache:
			return self._hourly_mix_cache[stratum_id]
		query = """
			SELECT dow, hour, operator_group, probability, sample_n, weight_sum
			FROM world_sim_atus.hourly_mix
			WHERE stratum_id = %s
		"""
		result = self.db.execute_query(query, (stratum_id,), fetch=True)
		if not result.success:
			raise RuntimeError(f"Failed to load hourly_mix for stratum {stratum_id}: {result.error}")
		structure: Dict[int, Dict[int, List[Dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
		for row in result.data or []:
			structure[int(row["dow"])][int(row["hour"])].append({
				"operator_group": row["operator_group"],
				"probability": float(row.get("probability") or 0.0),
				"sample_n": int(row.get("sample_n") or 0),
				"weight_sum": float(row.get("weight_sum") or 0.0),
			})
		self._hourly_mix_cache[stratum_id] = structure
		return structure

	def get_duration_stats(self, stratum_id: int) -> Dict[int, Dict[str, Dict[str, Any]]]:
		if stratum_id in self._duration_cache:
			return self._duration_cache[stratum_id]
		query = """
			SELECT dow, operator_group, mean_minutes, sd_minutes,
			       p10_minutes, p50_minutes, p90_minutes, sample_n, weight_sum
			FROM world_sim_atus.duration_stats
			WHERE stratum_id = %s
		"""
		result = self.db.execute_query(query, (stratum_id,), fetch=True)
		if not result.success:
			raise RuntimeError(f"Failed to load duration_stats for stratum {stratum_id}: {result.error}")
		structure: Dict[int, Dict[str, Dict[str, Any]]] = defaultdict(dict)
		for row in result.data or []:
			structure[int(row["dow"])][row["operator_group"]] = {
				"mean": float(row.get("mean_minutes") or 0.0),
				"sd": float(row.get("sd_minutes") or 0.0),
				"p10": row.get("p10_minutes"),
				"p50": row.get("p50_minutes"),
				"p90": row.get("p90_minutes"),
				"sample_n": int(row.get("sample_n") or 0),
				"weight_sum": float(row.get("weight_sum") or 0.0),
			}
		self._duration_cache[stratum_id] = structure
		return structure

	def get_transitions(self, stratum_id: int) -> Dict[int, Dict[str, List[Dict[str, Any]]]]:
		if stratum_id in self._transition_cache:
			return self._transition_cache[stratum_id]
		query = """
			SELECT hour, from_operator, to_operator, probability, sample_n
			FROM world_sim_atus.transitions
			WHERE stratum_id = %s
		"""
		result = self.db.execute_query(query, (stratum_id,), fetch=True)
		if not result.success:
			raise RuntimeError(f"Failed to load transitions for stratum {stratum_id}: {result.error}")
		structure: Dict[int, Dict[str, List[Dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
		for row in result.data or []:
			structure[int(row["hour"])][row["from_operator"]].append({
				"to": row["to_operator"],
				"probability": float(row.get("probability") or 0.0),
				"sample_n": int(row.get("sample_n") or 0),
			})
		self._transition_cache[stratum_id] = structure
		return structure

	def get_social_context(self, stratum_id: int) -> Dict[int, Dict[str, Dict[str, Any]]]:
		if stratum_id in self._social_cache:
			return self._social_cache[stratum_id]
		query = """
			SELECT hour, operator_group, home_prob, with_spouse, with_child,
			       with_friend, alone_prob, sample_n, weight_sum
			FROM world_sim_atus.social_where
			WHERE stratum_id = %s
		"""
		result = self.db.execute_query(query, (stratum_id,), fetch=True)
		if not result.success:
			raise RuntimeError(f"Failed to load social context for stratum {stratum_id}: {result.error}")
		structure: Dict[int, Dict[str, Dict[str, Any]]] = defaultdict(dict)
		for row in result.data or []:
			structure[int(row["hour"])][row["operator_group"]] = {
				"home_prob": float(row.get("home_prob") or 0.0),
				"with_spouse": float(row.get("with_spouse") or 0.0),
				"with_child": float(row.get("with_child") or 0.0),
				"with_friend": float(row.get("with_friend") or 0.0),
				"alone_prob": float(row.get("alone_prob") or 0.0),
				"sample_n": int(row.get("sample_n") or 0),
				"weight_sum": float(row.get("weight_sum") or 0.0),
			}
		self._social_cache[stratum_id] = structure
		return structure

	def get_weekly_presence(self, stratum_id: int) -> Dict[str, Dict[str, Any]]:
		if stratum_id in self._weekly_presence_cache:
			return self._weekly_presence_cache[stratum_id]
		query = """
			SELECT operator_group, presence_rate, mean_minutes_per_week, sample_n, weight_sum
			FROM world_sim_atus.weekly_presence
			WHERE stratum_id = %s
		"""
		result = self.db.execute_query(query, (stratum_id,), fetch=True)
		if not result.success:
			raise RuntimeError(f"Failed to load weekly presence for stratum {stratum_id}: {result.error}")
		structure: Dict[str, Dict[str, Any]] = {}
		for row in result.data or []:
			structure[row["operator_group"]] = {
				"presence_rate": float(row.get("presence_rate") or 0.0),
				"mean_minutes_per_week": float(row.get("mean_minutes_per_week") or 0.0),
				"sample_n": int(row.get("sample_n") or 0),
				"weight_sum": float(row.get("weight_sum") or 0.0),
			}
		self._weekly_presence_cache[stratum_id] = structure
		return structure


# Singleton provider
_provider: DistributionProvider | None = None


def get_distribution_provider() -> DistributionProvider:
	global _provider
	if _provider is None:
		_provider = DistributionProvider()
	return _provider
