#!/usr/bin/env python3
"""
Weekly skeleton and daily template generation from ATUS distributions.
"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

from .distributions import get_distribution_provider
from .models import ActivityBlock
from .profile import stratum_id_for_agent


def _seeded_random(simulation_id: str, agent_id: str, anchor: str) -> random.Random:
	seed_str = f"{simulation_id}:{agent_id}:{anchor}"
	seed = hash(seed_str) & ((1 << 32) - 1)
	rng = random.Random()
	rng.seed(seed)
	return rng


def _week_start(day: date) -> date:
	return day - timedelta(days=day.weekday())


def _dow_index(day: date) -> int:
	return day.weekday()


def _atus_dow(day: date) -> int:
	# ATUS diary day: 1=Sunday ... 7=Saturday
	weekday = day.weekday()  # Monday=0
	return ((weekday + 1) % 7) + 1


def _sample_sleep_for_day(rng: random.Random, presence_meta: Dict[str, Dict[str, float]]) -> List[Dict[str, float]]:
	"""Sample bedtime and duration for a day from presence; split across midnight if needed."""
	mean_weekly = (presence_meta.get("sleep", {}) or {}).get("mean_minutes_per_week", 7.0 * 7.5 * 60.0)
	daily_target_h = max(min((mean_weekly / 7.0) / 60.0, 9.0), 5.5)
	bed = 21.5 + rng.random() * 3.0  # 21.5..24.5
	bed = max(19.0, min(24.0, bed))
	first = max(0.0, min(24.0 - bed, daily_target_h))
	second = max(0.0, daily_target_h - first)
	blks: List[Dict[str, float]] = []
	if first > 0.0:
		blks.append({"operator": "sleep", "start": bed, "duration": first, "anchor": True})
	if second > 0.0:
		blks.append({"operator": "sleep", "start": 0.0, "duration": second, "anchor": True})
	return blks


def _maybe_add_work_anchor(presence_meta: Dict[str, Dict[str, float]], rng: random.Random) -> Optional[Dict[str, float]]:
	work = presence_meta.get("work_onsite") or {}
	if work.get("presence_rate", 0.0) >= 0.15:
		start_hour = rng.choice([8.0, 8.5, 9.0])
		duration = max(work.get("mean_minutes_per_week", 240.0) / 5.0 / 60.0, 6.5)
		duration = min(duration, 9.5)
		return {"operator": "work_onsite", "start": start_hour, "duration": duration, "anchor": True}
	return None


def _choose_weekly_slots(presence_meta: Dict[str, Dict[str, float]], rng: random.Random) -> Dict[int, List[Dict[str, float]]]:
	slots: Dict[int, List[Dict[str, float]]] = defaultdict(list)
	# Seed weekly activities by presence rates, beyond a small hardcoded set.
	# Prioritize common weekly activities if present in the stratum.
	candidate_ops = [
		("grocery_shop", [5, 6], [9.5, 10.0, 11.0], 1.2),
		("retail_shop", [5, 6], [13.0, 15.0], 1.0),
		("exercise", [1, 3, 5], [6.5, 18.0], 1.0),
		("socialize", [4, 5], [19.0, 20.0], 2.0),
		("leisure_out", [5, 6], [18.0, 20.0], 2.5),
		("household_chore", [6], [10.0, 11.0, 14.0], 1.5),
		("household_management", [6], [12.0, 16.0], 1.0),
		("meal_prep", [5, 6], [16.5, 17.5], 1.0),
		("eat_meal", [5, 6], [18.0, 19.0], 1.0),
		("personal_care_out", [5, 6], [11.0, 15.0], 1.0),
		("childcare", [5, 6], [10.0, 15.0], 1.5),
	]
	for operator, candidate_days, candidate_hours, base_duration in candidate_ops:
		meta = presence_meta.get(operator) or {"presence_rate": 0.2, "mean_minutes_per_week": base_duration * 60}
		prob = meta.get("presence_rate", 0.0)
		# probabilistically include based on presence rate
		if rng.random() > max(min(prob + 0.1, 1.0), 0.15):
				continue
		day = rng.choice(candidate_days)
		start = rng.choice(candidate_hours)
		duration = max(base_duration, (meta.get("mean_minutes_per_week", base_duration * 60) / 60.0))
		duration = min(duration, base_duration * 1.8)
		slots[day].append({"operator": operator, "start": start, "duration": duration, "anchor": False})

	return slots


def build_weekly_skeleton(agent, simulation_id: str, target_week_start: date) -> Dict[int, List[Dict[str, float]]]:
	provider = get_distribution_provider()
	stratum_id = stratum_id_for_agent(agent) or 1
	presence_meta = provider.get_weekly_presence(stratum_id)

	rng = _seeded_random(simulation_id, str(agent.agent_id), f"week:{target_week_start.isoformat()}")

	skeleton: Dict[int, List[Dict[str, float]]] = {i: [] for i in range(7)}
	for dow in range(7):
		skeleton[dow].extend(_sample_sleep_for_day(rng, presence_meta))

	work_anchor = _maybe_add_work_anchor(presence_meta, rng)
	if work_anchor:
		for dow in range(5):  # Monday-Friday
			skeleton[dow].append(work_anchor.copy())

	weekly_slots = _choose_weekly_slots(presence_meta, rng)
	for dow, blocks in weekly_slots.items():
		skeleton[dow].extend(blocks)

	# Add soft daily meal anchors with probability based on presence where available
	meal_presence = presence_meta.get("eat_meal", {"presence_rate": 0.8})
	if meal_presence.get("presence_rate", 0.0) > 0.2:
		for dow in range(7):
			for start, base_minutes in [(7.5, 30.0), (12.0, 45.0), (18.5, 45.0)]:
				if rng.random() <= min(1.0, meal_presence.get("presence_rate", 0.6) + 0.2):
					skeleton[dow].append({
						"operator": "eat_meal",
						"start": start,
						"duration": base_minutes / 60.0,
						"anchor": False,
					})

	for dow, blocks in skeleton.items():
		blocks.sort(key=lambda b: b["start"])
		# Enforce minimum daily sleep ~6h
		sleep_total = sum(b["duration"] for b in blocks if b["operator"] == "sleep")
		if sleep_total < 6.0:
			missing = 6.0 - sleep_total
			blocks.append({"operator": "sleep", "start": 22.0, "duration": min(24.0 - 22.0, missing), "anchor": True})
		blocks.sort(key=lambda b: b["start"])
	return skeleton


def _occupied_ranges(blocks: List[Dict[str, float]]) -> List[Tuple[float, float]]:
	ranges = []
	for block in blocks:
		start = block["start"]
		end = start + block["duration"]
		ranges.append((start, end))
	return ranges


def _find_gaps(ranges: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
	if not ranges:
		return [(0.0, 24.0)]
	ranges_sorted = sorted(ranges)
	gaps: List[Tuple[float, float]] = []
	prev_end = 0.0
	for start, end in ranges_sorted:
		if start > prev_end:
			gaps.append((prev_end, min(start, 24.0)))
		prev_end = max(prev_end, end)
	if prev_end < 24.0:
		gaps.append((prev_end, 24.0))
	return gaps


def _sample_operator_for_window(
	stratum_id: int,
	dow_atus: int,
	hour_start: float,
	window: float,
	rng: random.Random,
) -> Optional[str]:
	provider = get_distribution_provider()
	hourly_mix = provider.get_hourly_mix(stratum_id)
	hour = int(math.floor(hour_start))
	candidates = hourly_mix.get(dow_atus, {}).get(hour, [])
	if not candidates:
		return None
	total = sum(max(c["probability"], 0.0) for c in candidates)
	if total <= 0:
		return None
	choice = rng.random() * total
	accum = 0.0
	for c in candidates:
		accum += max(c["probability"], 0.0)
		if choice <= accum:
			return c["operator_group"]
	return candidates[-1]["operator_group"]


def _block_from_window(
	operator: str,
	start: float,
	window: float,
	stratum_id: int,
	dow_atus: int,
) -> ActivityBlock:
	provider = get_distribution_provider()
	duration_meta = provider.get_duration_stats(stratum_id)
	stats = duration_meta.get(dow_atus, {}).get(operator, {})
	duration = stats.get("p50") or stats.get("mean", window * 60)
	duration_minutes = max(min(duration, window * 60), 30.0)
	location_hint = provider.get_operator_specs().get(operator, {}).get("default_location")
	return ActivityBlock(
		block_id=f"{operator}-{int(start*10)}",
		operator_group=operator,
		start_hour=start,
		duration_minutes=duration_minutes,
		location_hint=location_hint,
		social_hint={},
		anchor=False,
	)


def sample_daily_template(
	agent,
	simulation_id: str,
	target_date: date,
	weekly_skeleton: Dict[int, List[Dict[str, float]]],
) -> List[ActivityBlock]:
	provider = get_distribution_provider()
	dow = _dow_index(target_date)
	dow_atus = _atus_dow(target_date)

	# Prepare distributions (mixture over strata if possible)
	from .profile import strata_mixture_for_agent, stratum_id_for_agent
	mixture = strata_mixture_for_agent(agent)
	if mixture:
		presence_meta = provider.get_mixed_weekly_presence(mixture)
		hourly_mix_struct = provider.get_mixed_hourly_mix(mixture)  # dow -> hour -> op -> prob
		duration_meta = provider.get_mixed_duration_stats(mixture)  # dow -> op -> stats
		base_stratum = mixture[0][0]
	else:
		base_stratum = stratum_id_for_agent(agent) or 1
		presence_meta = provider.get_weekly_presence(base_stratum)
		# convert list-based hourly mix to map-based for unified handling
		_list_based = provider.get_hourly_mix(base_stratum)
		hourly_mix_struct = {}
		for _dow, hours in (_list_based or {}).items():
			inner = {}
			for h, items in hours.items():
				inner[h] = {it["operator_group"]: float(it.get("probability") or 0.0) for it in items}
			hourly_mix_struct[_dow] = inner
		duration_meta = provider.get_duration_stats(base_stratum)

	blocks = []
	for entry in weekly_skeleton.get(dow, []):
		duration_minutes = entry["duration"] * 60.0
		location_hint = provider.get_operator_specs().get(entry["operator"], {}).get("default_location")
		block = ActivityBlock(
			block_id=f"anchor-{entry['operator']}-{int(entry['start']*100)}",
			operator_group=entry["operator"],
			start_hour=entry["start"],
			duration_minutes=duration_minutes,
			location_hint=location_hint,
			social_hint={},
			anchor=bool(entry.get("anchor")),
		)
		blocks.append(block)

	ranges = _occupied_ranges(weekly_skeleton.get(dow, []))
	gaps = _find_gaps(ranges)

	rng = _seeded_random(simulation_id, str(agent.agent_id), f"day:{target_date.isoformat()}")

	# Local helpers using unified distribution structures
	def _sample_op_from_mix(hour_start: float) -> Optional[str]:
		hour = int(math.floor(hour_start))
		candidates = (hourly_mix_struct.get(dow_atus, {}) or {}).get(hour, {})
		if not candidates:
			return None
		total = sum(max(p, 0.0) for p in candidates.values())
		if total <= 0:
			return None
		choice = rng.random() * total
		acc = 0.0
		for op, p in candidates.items():
			acc += max(p, 0.0)
			if choice <= acc:
				return op
		# fallback
		return next(iter(candidates.keys()))

	def _block_from_mix(op: str, start: float, window: float) -> ActivityBlock:
		stats = (duration_meta.get(dow_atus, {}) or {}).get(op, {})
		duration = float(stats.get("p50") or stats.get("mean") or (window * 60.0))
		duration_minutes = max(min(duration, window * 60.0), 30.0)
		location_hint = provider.get_operator_specs().get(op, {}).get("default_location")
		return ActivityBlock(
			block_id=f"{op}-{int(start*10)}",
			operator_group=op,
			start_hour=start,
			duration_minutes=duration_minutes,
			location_hint=location_hint,
			social_hint={},
			anchor=False,
		)

	# Fill gaps by iteratively sampling within each gap to produce multiple blocks
	for gap_start, gap_end in gaps:
		cursor = gap_start
		while cursor + 0.25 <= gap_end:
			operator = _sample_op_from_mix(cursor)
			if not operator:
				cursor += 0.5
				continue
			block = _block_from_mix(operator, cursor, gap_end - cursor)
			blocks.append(block)
			# advance by the block duration (in hours), minimum 0.5h to avoid zero-progress loops
			advance = max(block.duration_minutes / 60.0, 0.5)
			cursor = min(cursor + advance, gap_end)

	social_meta = provider.get_social_context(base_stratum)
	for block in blocks:
		hour = int(math.floor(block.start_hour))
		meta = social_meta.get(hour, {}).get(block.operator_group, {})
		if meta:
			block.social_hint = {
				"k": v for k, v in {
					"home_prob": meta.get("home_prob"),
					"with_spouse": meta.get("with_spouse"),
					"with_child": meta.get("with_child"),
					"with_friend": meta.get("with_friend"),
					"alone": meta.get("alone_prob"),
				}.items() if v is not None
			}

	blocks.sort(key=lambda b: b.start_hour)
	return blocks
