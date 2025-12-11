#!/usr/bin/env python3
"""
Precompute ATUS-derived distributions for agent planning.

Generates:
- strata definitions and case-to-stratum mapping
- operator mappings from ATUS activity codes
- hourly activity mix, duration statistics, transitions
- social context probabilities and weekly presence metrics

Usage:
    python -m Utils.atus.atus_precompute

Requires:
- ATUS tables populated (case_id, atusact, who, mapping_codes, etc.)
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from collections import defaultdict, OrderedDict
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

try:
	from tqdm import tqdm
except ImportError:
	# Fallback if tqdm not available
	def tqdm(iterable, *args, **kwargs):
		return iterable

# Ensure project root (World_Sim) is on sys.path when running as a script
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Database.managers.atus import get_atus_database_manager
from Agent.modules.planning.strata import (
	StratumFeatures,
	build_stratum_features,
)


# -----------------------------------------------------------------------------
# Operator mapping heuristics
# -----------------------------------------------------------------------------

def classify_operator(major: str, tier: str, code: str, activity: str) -> str:
	act_lower = (activity or "").lower()

	if code.startswith("0101"):
		return "sleep"
	if major == "01":
		return "personal_care"
	if major == "02":
		if tier.startswith("0202"):
			return "meal_prep"
		return "household_chore"
	if major == "03":
		return "childcare"
	if major == "04":
		return "work_onsite"
	if major == "05":
		return "attend_class"
	if major == "06":
		if "grocery" in act_lower or "food shopping" in act_lower or "supermarket" in act_lower:
			return "grocery_shop"
		if "shopping" in act_lower:
			return "retail_shop"
		return "retail_shop"
	if major == "07":
		if "medical" in act_lower or "doctor" in act_lower or "health" in act_lower:
			return "medical"
		if "pharmacy" in act_lower or "prescription" in act_lower:
			return "pharmacy"
		return "personal_care_out"
	if major == "08":
		if "sports" in act_lower or "exercise" in act_lower:
			return "exercise"
		if "religious" in act_lower or "spiritual" in act_lower:
			return "religious"
		if "volunteer" in act_lower:
			return "volunteer"
		if "socializing" in act_lower:
			return "socialize"
		if "arts" in act_lower or "entertainment" in act_lower or "recreation" in act_lower:
			return "leisure_out"
		return "leisure_home"
	if major == "09":
		return "eat_meal"
	if major == "10":
		return "household_management"
	if major == "11":
		return "travel_support"
	if major == "14":
		return "leisure_out"
	if major == "15":
		return "travel_support"
	if major == "16":
		return "travel_support"
	if major == "18":
		return "travel_support"

	return "other"


def default_location_for_operator(operator: str) -> Optional[str]:
	if operator in {"sleep", "personal_care", "meal_prep", "eat_meal", "household_chore", "leisure_home", "work_remote"}:
		return "home"
	if operator in {"work_onsite", "grocery_shop", "retail_shop", "medical", "pharmacy", "exercise", "socialize", "leisure_out", "religious", "volunteer", "household_management", "travel_support"}:
		return "out"
	return None


def cooldown_defaults(operator: str) -> Tuple[Optional[int], Optional[int], Optional[Dict[str, Any]]]:
	if operator == "grocery_shop":
		return 2, 2, {"inventory_trigger": "pantry_low"}
	if operator == "retail_shop":
		return 2, 3, {}
	if operator == "medical":
		return 30, 1, {"requires_health_need": True}
	if operator == "pharmacy":
		return 7, 2, {"inventory_trigger": "medication_low"}
	if operator == "exercise":
		return 0, 5, {}
	if operator == "socialize":
		return 0, 7, {}
	if operator == "leisure_out":
		return 0, 7, {}
	return None, None, {}


# -----------------------------------------------------------------------------
# Data loading
# -----------------------------------------------------------------------------

def fetch_mapping_codes(db) -> List[Dict[str, Any]]:
	query = """
		SELECT major_code, tier_code, six_digit_activity_code, activity
		FROM world_sim_atus.mapping_codes
	"""
	result = db.execute_query(query, fetch=True)
	if not result.success:
		raise RuntimeError(f"Failed to fetch mapping codes: {result.error}")
	return result.data


def build_operator_map_rows(mapping_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
	rows: List[Dict[str, Any]] = []
	for row in tqdm(mapping_rows, desc="  Building operator map", unit="rows"):
		major = (row.get("major_code") or "").zfill(2)
		tier = (row.get("tier_code") or "").zfill(4)
		code = (row.get("six_digit_activity_code") or "").zfill(6)
		activity = row.get("activity") or ""
		operator = classify_operator(major, tier, code, activity)
		if operator == "other":
			continue
		default_loc = default_location_for_operator(operator)
		cooldown_days, weekly_quota, prereq_flags = cooldown_defaults(operator)
		rows.append({
			"six_digit_activity_code": code,
			"operator_group": operator,
			"default_location": default_loc,
			"typical_minutes_p50": None,
			"cooldown_days": cooldown_days,
			"weekly_quota": weekly_quota,
			"prereq_flags": prereq_flags or None,
		})
	return rows


def fetch_case_metadata(db) -> List[Dict[str, Any]]:
	query = """
		SELECT
			c.TUCASEID,
			c.TEAGE,
			c.TESEX,
			c.TELFS,
			c.TRCHILDNUM,
			c.TEHRUSLT,
			c.GEMETSTA,
			c.TUFNWGTP,
			c.TUDIARYDAY,
			c.PEEDUCA,
			c.TRERNWA,
			cp.GEREG
		FROM world_sim_atus.case_id c
		LEFT JOIN world_sim_atus.cps cp
			ON cp.TUCASEID = c.TUCASEID
			AND cp.TULINENO = 1
	"""
	result = db.execute_query(query, fetch=True)
	if not result.success:
		raise RuntimeError(f"Failed to fetch case metadata: {result.error}")
	return result.data


def fetch_who_data(db) -> Dict[Tuple[str, int], List[int]]:
	query = """
		SELECT TUCASEID, TUACTIVITY_N, TUWHO_CODE
		FROM world_sim_atus.who
		WHERE TUWHO_CODE IS NOT NULL AND TUWHO_CODE > 0
	"""
	result = db.execute_query(query, fetch=True)
	if not result.success:
		raise RuntimeError(f"Failed to fetch who data: {result.error}")

	companion_map: Dict[Tuple[str, int], List[int]] = defaultdict(list)
	for row in tqdm(result.data, desc="  Processing companion data", unit="rows"):
		key = (row["TUCASEID"], row["TUACTIVITY_N"])
		companion_map[key].append(int(row["TUWHO_CODE"]))
	return companion_map


def fetch_activities(db) -> Iterable[Dict[str, Any]]:
	query = """
		SELECT
			TUCASEID,
			TUACTIVITY_N,
			TUSTARTTIM,
			TRCODEP,
			TUACTDUR24,
			TEWHERE
		FROM world_sim_atus.atusact
		ORDER BY TUCASEID, TUACTIVITY_N
	"""
	result = db.execute_query(query, fetch=True)
	if not result.success:
		raise RuntimeError(f"Failed to fetch activities: {result.error}")
	return result.data


# -----------------------------------------------------------------------------
# Aggregation helpers
# -----------------------------------------------------------------------------

def weighted_quantiles(values: List[Tuple[float, float]], quantiles: Sequence[float]) -> List[Optional[float]]:
	if not values:
		return [None for _ in quantiles]
	values_sorted = sorted(values, key=lambda x: x[0])
	total_weight = sum(w for _, w in values_sorted)
	if total_weight <= 0:
		return [None for _ in quantiles]
	cumulative = 0.0
	results: List[Optional[float]] = []
	targets = [q * total_weight for q in quantiles]
	idx = 0
	for target in targets:
		while idx < len(values_sorted):
			duration, weight = values_sorted[idx]
			cumulative += weight
			if cumulative >= target:
				results.append(duration)
				break
			idx += 1
		else:
			results.append(values_sorted[-1][0])
	return results


def parse_start_hour(start_time: Optional[str]) -> int:
	if not start_time:
		return 0
	try:
		parts = start_time.split(":")
		if not parts:
			return 0
		return int(parts[0]) % 24
	except (ValueError, TypeError):
		return 0


def is_home_location(tewhere: Optional[int]) -> bool:
	if tewhere is None:
		return False
	return int(tewhere) in {1, 2}


def companion_flags(codes: List[int]) -> Dict[str, bool]:
	flags = {
		"with_spouse": False,
		"with_child": False,
		"with_friend": False,
	}
	for code in codes:
		if code == 18:
			flags["with_spouse"] = True
		elif code in {20, 21, 22, 40}:
			flags["with_child"] = True
		elif code in {30, 31, 32, 33, 34, 35, 36, 37}:
			flags["with_friend"] = True
	return flags


# -----------------------------------------------------------------------------
# Main computation
# -----------------------------------------------------------------------------

def build_strata(case_rows: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, int]]:
	strata_lookup: OrderedDict[StratumFeatures, int] = OrderedDict()
	strata_rows: List[Dict[str, Any]] = []
	case_stratum_rows: List[Dict[str, Any]] = []
	case_to_stratum: Dict[str, int] = {}

	for row in tqdm(case_rows, desc="  Building strata", unit="cases"):
		features = build_stratum_features(
			row.get("TEAGE"),
			row.get("TESEX"),
			row.get("TELFS"),
			row.get("TEHRUSLT"),
			row.get("TRCHILDNUM"),
			row.get("PEEDUCA"),
			row.get("TRERNWA"),
			row.get("GEREG"),
			row.get("GEMETSTA"),
		)
		if features not in strata_lookup:
			strata_id = len(strata_lookup) + 1
			strata_lookup[features] = strata_id
			strata_rows.append({
				"id": strata_id,
				"name": f"stratum_{strata_id}",
				"definition": features.to_definition(),
			})
		else:
			strata_id = strata_lookup[features]
		case_stratum_rows.append({
			"TUCASEID": row["TUCASEID"],
			"stratum_id": strata_id,
		})
		case_to_stratum[row["TUCASEID"]] = strata_id

	return strata_rows, case_stratum_rows, case_to_stratum


def compute_distributions(
	case_rows: List[Dict[str, Any]],
	case_to_stratum: Dict[str, int],
	operator_lookup: Dict[str, str],
	activities: List[Dict[str, Any]],
	companion_map: Dict[Tuple[str, int], List[int]],
) -> Tuple[
	List[Dict[str, Any]],  # hourly_mix
	List[Dict[str, Any]],  # duration_stats
	List[Dict[str, Any]],  # transitions
	List[Dict[str, Any]],  # social_where
	List[Dict[str, Any]],  # weekly_presence
]:

	case_meta = {
		row["TUCASEID"]: {
			"weight": float(row.get("TUFNWGTP") or 0.0),
			"dow": int(row.get("TUDIARYDAY") or 1),
		}
		for row in case_rows
	}

	hourly_minutes: Dict[Tuple[int, int, int, str], float] = defaultdict(float)
	hourly_totals: Dict[Tuple[int, int, int], float] = defaultdict(float)
	hourly_samples: Dict[Tuple[int, int, int], set] = defaultdict(set)

	duration_values: Dict[Tuple[int, int, str], List[Tuple[float, float]]] = defaultdict(list)
	duration_moments: Dict[Tuple[int, int, str], Tuple[float, float, float]] = defaultdict(lambda: (0.0, 0.0, 0.0))
	duration_counts: Dict[Tuple[int, int, str], Tuple[int, float]] = defaultdict(lambda: (0, 0.0))

	transition_counts: Dict[Tuple[int, int, str, str], float] = defaultdict(float)
	transition_totals: Dict[Tuple[int, int, str], float] = defaultdict(float)
	transition_samples: Dict[Tuple[int, int, str], set] = defaultdict(set)

	social_counts: Dict[Tuple[int, int, str], Dict[str, float]] = defaultdict(lambda: defaultdict(float))
	social_totals: Dict[Tuple[int, int, str], float] = defaultdict(float)
	social_samples: Dict[Tuple[int, int, str], set] = defaultdict(set)

	case_operator_minutes: Dict[Tuple[str, str], float] = defaultdict(float)

	current_case = None
	current_sequence: List[Tuple[int, str, float]] = []

	for act in tqdm(activities, desc="  Processing activities", unit="activities"):
		tucaseid = act["TUCASEID"]
		if tucaseid not in case_to_stratum or tucaseid not in case_meta:
			continue

		stratum_id = case_to_stratum[tucaseid]
		meta = case_meta[tucaseid]
		weight = meta["weight"]
		if weight <= 0:
			continue

		operator = operator_lookup.get(act["TRCODEP"])
		if not operator:
			continue

		dow = meta["dow"]
		hour = parse_start_hour(act["TUSTARTTIM"])
		duration = float(act.get("TUACTDUR24") or 0.0)
		if duration <= 0:
			continue

		key_hourly = (stratum_id, dow, hour, operator)
		key_hour_total = (stratum_id, dow, hour)
		weighted_minutes = duration * weight
		hourly_minutes[key_hourly] += weighted_minutes
		hourly_totals[key_hour_total] += weighted_minutes
		hourly_samples[key_hour_total].add(tucaseid)

		key_duration = (stratum_id, dow, operator)
		duration_values[key_duration].append((duration, weight))
		sum_w, sum_wx, sum_wx2 = duration_moments[key_duration]
		duration_moments[key_duration] = (
			sum_w + weight,
			sum_wx + duration * weight,
			sum_wx2 + (duration ** 2) * weight,
		)
		count, weight_sum = duration_counts[key_duration]
		duration_counts[key_duration] = (count + 1, weight_sum + weight)

		comp_key = (tucaseid, act["TUACTIVITY_N"])
		comp_codes = companion_map.get(comp_key, [])
		flags = companion_flags(comp_codes)
		key_social = (stratum_id, hour, operator)
		social_totals[key_social] += weight
		if is_home_location(act.get("TEWHERE")):
			social_counts[key_social]["home"] += weight
		else:
			social_counts[key_social]["out"] += weight
		for flag, value in flags.items():
			if value:
				social_counts[key_social][flag] += weight
		if not comp_codes:
			social_counts[key_social]["alone"] += weight
		social_samples[key_social].add(tucaseid)

		# Handle transitions per case
		if current_case != tucaseid:
			current_case = tucaseid
			current_sequence = []
		current_sequence.append((hour, operator, weight))
		if len(current_sequence) >= 2:
			prev_hour, prev_operator, prev_weight = current_sequence[-2]
			key_transition = (stratum_id, prev_hour, prev_operator, operator)
			key_transition_total = (stratum_id, prev_hour, prev_operator)
			transition_counts[key_transition] += weight
			transition_totals[key_transition_total] += weight
			transition_samples[key_transition_total].add(tucaseid)

	# Weekly presence aggregated by stratum/operator
		key_case_operator = (tucaseid, operator)
		case_operator_minutes[key_case_operator] += duration

	weekly_presence_rows: List[Dict[str, Any]] = []
	stratum_presence_weight: Dict[Tuple[int, str], float] = defaultdict(float)
	stratum_minutes_weighted: Dict[Tuple[int, str], float] = defaultdict(float)
	stratum_weight_sum: Dict[Tuple[int, str], float] = defaultdict(float)
	stratum_case_counts: Dict[Tuple[int, str], int] = defaultdict(int)

	for (case_id, operator), minutes in tqdm(case_operator_minutes.items(), desc="  Computing weekly presence", unit="cases"):
		if case_id not in case_to_stratum or case_id not in case_meta:
			continue
		stratum_id = case_to_stratum[case_id]
		weight = case_meta[case_id]["weight"]
		key = (stratum_id, operator)
		stratum_minutes_weighted[key] += minutes * weight
		stratum_weight_sum[key] += weight
		stratum_case_counts[key] += 1
		if minutes > 0:
			stratum_presence_weight[key] += weight

	for key, weight_sum in stratum_weight_sum.items():
		stratum_id, operator = key
		if weight_sum <= 0:
			continue
		presence_weight = stratum_presence_weight.get(key, 0.0)
		minutes_weighted = stratum_minutes_weighted.get(key, 0.0)
		sample_n = stratum_case_counts.get(key, 0)
		weekly_presence_rows.append({
			"stratum_id": stratum_id,
			"operator_group": operator,
			"presence_rate": presence_weight / weight_sum,
			"mean_minutes_per_week": minutes_weighted / weight_sum,
			"sample_n": sample_n,
			"weight_sum": weight_sum,
		})

	# Precompute operator counts per (stratum_id, dow, hour) to avoid quadratic scans
	operator_counts: Dict[Tuple[int, int, int], int] = defaultdict(int)
	for (sid, d, h, _op) in hourly_minutes.keys():
		operator_counts[(sid, d, h)] += 1

	# Hourly mix rows
	alpha = 0.1
	hourly_mix_rows: List[Dict[str, Any]] = []
	for (stratum_id, dow, hour, operator), weighted_minutes in hourly_minutes.items():
		total = hourly_totals[(stratum_id, dow, hour)]
		operator_count = operator_counts[(stratum_id, dow, hour)]
		alpha_total = alpha * operator_count
		probability = (weighted_minutes + alpha) / (total + alpha_total) if total + alpha_total > 0 else 0.0
		sample_n = len(hourly_samples[(stratum_id, dow, hour)])
		hourly_mix_rows.append({
			"stratum_id": stratum_id,
			"dow": dow,
			"hour": hour,
			"operator_group": operator,
			"probability": probability,
			"sample_n": sample_n,
			"weight_sum": total,
		})

	# Duration stats rows
	duration_rows: List[Dict[str, Any]] = []
	for key, values in duration_values.items():
		stratum_id, dow, operator = key
		sum_w, sum_wx, sum_wx2 = duration_moments[key]
		if sum_w <= 0:
			continue
		mean = sum_wx / sum_w
		var = max((sum_wx2 / sum_w) - (mean ** 2), 0.0)
		sd = math.sqrt(var)
		p10, p50, p90 = weighted_quantiles(values, [0.1, 0.5, 0.9])
		count, weight_sum = duration_counts[key]
		duration_rows.append({
			"stratum_id": stratum_id,
			"dow": dow,
			"operator_group": operator,
			"mean_minutes": mean,
			"sd_minutes": sd,
			"p10_minutes": p10,
			"p50_minutes": p50,
			"p90_minutes": p90,
			"sample_n": count,
			"weight_sum": weight_sum,
		})

	# Precompute out-degree counts for (stratum_id, hour, from_operator)
	outdegree_counts: Dict[Tuple[int, int, str], int] = defaultdict(int)
	for (sid, hr, from_op, _to_op) in transition_counts.keys():
		outdegree_counts[(sid, hr, from_op)] += 1

	# Transition rows
	transition_rows: List[Dict[str, Any]] = []
	for key, count in transition_counts.items():
		stratum_id, hour, from_op, to_op = key
		total = transition_totals.get((stratum_id, hour, from_op), 0.0)
		if total <= 0:
			continue
		alpha_trans = 0.05
		outdeg = outdegree_counts[(stratum_id, hour, from_op)] or 1
		probability = (count + alpha_trans) / (total + alpha_trans * outdeg)
		sample_n = len(transition_samples[(stratum_id, hour, from_op)])
		transition_rows.append({
			"stratum_id": stratum_id,
			"hour": hour,
			"from_operator": from_op,
			"to_operator": to_op,
			"probability": probability,
			"sample_n": sample_n,
		})

	# Social where rows
	social_rows: List[Dict[str, Any]] = []
	for key, counts in social_counts.items():
		stratum_id, hour, operator = key
		total_weight = social_totals.get(key, 0.0)
		if total_weight <= 0:
			continue
		social_rows.append({
			"stratum_id": stratum_id,
			"hour": hour,
			"operator_group": operator,
			"home_prob": counts.get("home", 0.0) / total_weight,
			"with_spouse": counts.get("with_spouse", 0.0) / total_weight,
			"with_child": counts.get("with_child", 0.0) / total_weight,
			"with_friend": counts.get("with_friend", 0.0) / total_weight,
			"alone_prob": counts.get("alone", 0.0) / total_weight,
			"sample_n": len(social_samples.get(key, set())),
			"weight_sum": total_weight,
		})

	return hourly_mix_rows, duration_rows, transition_rows, social_rows, weekly_presence_rows


# -----------------------------------------------------------------------------
# Main entry
# -----------------------------------------------------------------------------

def run_precompute(dry_run: bool = False) -> None:
	db = get_atus_database_manager()

	print("[atus_precompute] Loading mapping codes...")
	mapping_rows = fetch_mapping_codes(db)
	operator_map_rows = build_operator_map_rows(mapping_rows)

	print("[atus_precompute] Loading case metadata...")
	case_rows = fetch_case_metadata(db)
	strata_rows, case_stratum_rows, case_to_stratum = build_strata(case_rows)

	print(f"[atus_precompute] Generated {len(strata_rows)} strata")

	print("[atus_precompute] Loading companion data...")
	companion_map = fetch_who_data(db)

	print("[atus_precompute] Loading activities...")
	activities_raw = fetch_activities(db)
	# Count first for progress bar
	activities_list = list(activities_raw)
	print(f"  Loaded {len(activities_list)} activities")
	activities = activities_list

	operator_lookup = {
		row["six_digit_activity_code"]: row["operator_group"]
		for row in operator_map_rows
	}

	print("[atus_precompute] Computing distributions...")
	hourly_mix_rows, duration_rows, transition_rows, social_rows, weekly_presence_rows = compute_distributions(
		case_rows,
		case_to_stratum,
		operator_lookup,
		activities,
		companion_map,
	)

	if dry_run:
		print("[atus_precompute] Dry run complete. Not writing to database.")
		print(f"  strata_def: {len(strata_rows)} rows")
		print(f"  operator_map: {len(operator_map_rows)} rows")
		print(f"  case_stratum: {len(case_stratum_rows)} rows")
		print(f"  hourly_mix: {len(hourly_mix_rows)} rows")
		print(f"  duration_stats: {len(duration_rows)} rows")
		print(f"  transitions: {len(transition_rows)} rows")
		print(f"  social_where: {len(social_rows)} rows")
		print(f"  weekly_presence: {len(weekly_presence_rows)} rows")
		return

	print("[atus_precompute] Clearing existing model tables...")
	db.clear_model_tables()

	print("[atus_precompute] Writing strata definitions...")
	success, error = db.upsert_strata_def(strata_rows)
	if not success:
		raise RuntimeError(f"Failed to upsert strata_def: {error}")

	print("[atus_precompute] Writing case-stratum mapping...")
	success, error = db.upsert_case_stratum(case_stratum_rows)
	if not success:
		raise RuntimeError(f"Failed to upsert case_stratum: {error}")

	print("[atus_precompute] Writing operator map...")
	success, error = db.upsert_operator_map(operator_map_rows)
	if not success:
		raise RuntimeError(f"Failed to upsert operator_map: {error}")

	print("[atus_precompute] Writing hourly mix...")
	success, error = db.upsert_hourly_mix(hourly_mix_rows)
	if not success:
		raise RuntimeError(f"Failed to upsert hourly_mix: {error}")

	print("[atus_precompute] Writing duration stats...")
	success, error = db.upsert_duration_stats(duration_rows)
	if not success:
		raise RuntimeError(f"Failed to upsert duration_stats: {error}")

	print("[atus_precompute] Writing transitions...")
	success, error = db.upsert_transitions(transition_rows)
	if not success:
		raise RuntimeError(f"Failed to upsert transitions: {error}")

	print("[atus_precompute] Writing social context data...")
	success, error = db.upsert_social_where(social_rows)
	if not success:
		raise RuntimeError(f"Failed to upsert social_where: {error}")

	print("[atus_precompute] Writing weekly presence metrics...")
	success, error = db.upsert_weekly_presence(weekly_presence_rows)
	if not success:
		raise RuntimeError(f"Failed to upsert weekly_presence: {error}")

	print("[atus_precompute] Precompute complete.")


def main() -> None:
	parser = argparse.ArgumentParser(description="Precompute ATUS planning distributions.")
	parser.add_argument(
		"--dry-run",
		action="store_true",
		help="Run computations without writing results to the database.",
	)
	args = parser.parse_args()
	run_precompute(dry_run=args.dry_run)


if __name__ == "__main__":
	main()

