#!/usr/bin/env python3
"""
LLM-backed operator step synthesis with heuristic fallback.
"""

from __future__ import annotations

import json
import random
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from Utils.api_manager import APIManager

from .models import ActivityBlock, OperatorStep
from .venues import choose_place


def _time_string(start_hour: float) -> str:
	hour = int(start_hour)
	minute = int((start_hour - hour) * 60)
	return datetime.combine(date.today(), datetime.min.time()).replace(hour=hour, minute=minute).strftime("%I:%M %p")


def _call_llm(agent, goal: str, world_context: str, blocks: List[ActivityBlock], target_date: date) -> Optional[tuple[List[OperatorStep], str, str]]:
	api_key = None
	if hasattr(agent, "action") and getattr(agent.action, "api_manager", None):
		api_key = agent.action.api_manager.api_key
	if not api_key:
		return None

	api_manager = APIManager(api_key=api_key)
	payload = {
		"date": target_date.isoformat(),
		"blocks": [
			{
				"id": block.block_id,
				"operator_group": block.operator_group,
				"start_hour": block.start_hour,
				"duration_minutes": block.duration_minutes,
				"location_hint": block.location_hint,
				"anchor": block.anchor,
			}
			for block in blocks
		],
	}
	prompt = (
		"You are an assistant that converts activity blocks into executable plan steps.\n"
		"Return a JSON array where each item has fields: "
		"step_id, start_time (HH:MM AM/PM), operator (Travel|Exchange|Communicate|Wait|ReturnHome), "
		"location, parameters (object), source_block.\n"
		f"Agent summary: {agent.llm_summary or agent.get_broad_summary()}\n"
		f"Daily goal: {goal}\n"
		f"World context: {world_context}\n"
		f"Blocks JSON: {json.dumps(payload)}\n"
	)
	try:
		response, reasoning, model_name, _ = api_manager.make_request(
			prompt=prompt,
			intelligence_level=1,
			temperature=0.2,
			max_tokens=2000,
		)
	except Exception:
		return None
	if not response:
		return None
	try:
		data = json.loads(response)
	except json.JSONDecodeError:
		return None
	if not isinstance(data, list):
		return None
	steps: List[OperatorStep] = []
	for item in data:
		try:
			steps.append(OperatorStep(
				step_id=item.get("step_id") or "",
				start_time=item.get("start_time") or "08:00 AM",
				operator=item.get("operator") or "Wait",
				location=item.get("location") or "home",
				parameters=item.get("parameters") or {},
				source_block=item.get("source_block"),
			))
		except Exception:
			continue
	if steps:
		return steps, reasoning, model_name
	return None


def _heuristic_steps(agent, blocks: List[ActivityBlock], target_date: date) -> List[OperatorStep]:
	"""
	Convert ATUS activity blocks to executable operator steps using comprehensive heuristics.
	
	This function maps all 14 ATUS operator groups to realistic action sequences:
	- sleep, personal_care: rest at home
	- meal_prep, eat_meal, household_chore: domestic activities at home
	- work_onsite: travel to workplace, work, return
	- attend_class: travel to school, attend, return
	- retail_shop: travel to store, shop (Exchange), return
	- childcare: supervise at home or travel to childcare facility
	- leisure_home: relax at home
	- leisure_out: travel to venue, socialize, return
	- personal_care_out: travel to salon/barber, service, return
	- household_management: errands (bank, post office, etc.)
	- travel_support: picking up/dropping off others (ridesharing)
	"""
	steps: List[OperatorStep] = []
	rng = random.Random()
	rng.seed(hash(f"heuristic:{agent.agent_id}:{target_date.isoformat()}") & ((1 << 32) - 1))

	def add_step(step_id: str, start_hour: float, operator: str, location: str, params: Dict[str, Any], block_id: str):
		steps.append(OperatorStep(
			step_id=step_id,
			start_time=_time_string(start_hour),
			operator=operator,
			location=location,
			parameters=params,
			source_block=block_id,
		))

	for block in blocks:
		op = block.operator_group
		start = block.start_hour
		dur_min = block.duration_minutes
		loc_hint = block.location_hint or "home"
		
		# === Sleep and personal care at home ===
		if op == "sleep":
			add_step(f"{block.block_id}-sleep", start, "Wait", "home", 
					{"minutes": dur_min, "activity": "sleeping", "synth": "heuristic"}, block.block_id)
			continue
		
		if op == "personal_care":
			add_step(f"{block.block_id}-personal", start, "Wait", "home",
					{"minutes": dur_min, "activity": "personal_care", "synth": "heuristic"}, block.block_id)
			continue
		
		# === Domestic activities at home ===
		if op in {"meal_prep", "eat_meal"}:
			activity = "cooking" if op == "meal_prep" else "eating"
			add_step(f"{block.block_id}-meal", start, "Wait", "home",
					{"minutes": dur_min, "activity": activity, "synth": "heuristic"}, block.block_id)
			continue
		
		if op == "household_chore":
			add_step(f"{block.block_id}-chore", start, "Wait", "home",
					{"minutes": dur_min, "activity": "household_chore", "synth": "heuristic"}, block.block_id)
			continue
		
		if op == "leisure_home":
			add_step(f"{block.block_id}-leisure", start, "Wait", "home",
					{"minutes": dur_min, "activity": "leisure_home", "synth": "heuristic"}, block.block_id)
			continue
		
		# === Work ===
		if op == "work_onsite":
			workplace = choose_place(agent, "work", rng)
			if workplace:
				travel_time = 15  # minutes each way
				add_step(f"{block.block_id}-travel-to", start, "Travel", "in_transit",
						{"to": workplace, "synth": "heuristic"}, block.block_id)
				add_step(f"{block.block_id}-work", start + travel_time/60, "Wait", workplace,
						{"minutes": dur_min - 2*travel_time, "activity": "working", "synth": "heuristic"}, block.block_id)
				add_step(f"{block.block_id}-travel-home", start + dur_min/60 - travel_time/60, "Travel", "in_transit",
						{"to": "home", "synth": "heuristic"}, block.block_id)
			else:
				# Work from home fallback
				add_step(f"{block.block_id}-work", start, "Wait", "home",
						{"minutes": dur_min, "activity": "working_from_home", "synth": "heuristic"}, block.block_id)
			continue
		
		# === Education ===
		if op == "attend_class":
			school = choose_place(agent, "school", rng)
			if not school:
				school = choose_place(agent, "work", rng)  # Fallback to workplace as proxy
			if school:
				travel_time = 15
				add_step(f"{block.block_id}-travel-to", start, "Travel", "in_transit",
						{"to": school, "synth": "heuristic"}, block.block_id)
				add_step(f"{block.block_id}-class", start + travel_time/60, "Wait", school,
						{"minutes": dur_min - 2*travel_time, "activity": "attending_class", "synth": "heuristic"}, block.block_id)
				add_step(f"{block.block_id}-travel-home", start + dur_min/60 - travel_time/60, "Travel", "in_transit",
						{"to": "home", "synth": "heuristic"}, block.block_id)
			else:
				# Online class fallback
				add_step(f"{block.block_id}-class", start, "Wait", "home",
						{"minutes": dur_min, "activity": "online_class", "synth": "heuristic"}, block.block_id)
			continue
		
		# === Shopping ===
		if op == "retail_shop":
			store = choose_place(agent, "retail", rng)
			if not store:
				store = choose_place(agent, "grocery", rng)  # Fallback to grocery as proxy
			if store:
				travel_time = 15
				shop_time = min(dur_min - 2*travel_time, 30)
				browse_time = max(dur_min - 2*travel_time - shop_time, 0)
				add_step(f"{block.block_id}-travel-to", start, "Travel", "in_transit",
						{"to": store, "synth": "heuristic"}, block.block_id)
				if shop_time > 0:
					add_step(f"{block.block_id}-shop", start + travel_time/60, "Exchange", store,
							{"counterparty": store, "receive": {"RETAIL_ITEM": 1}, "synth": "heuristic"}, block.block_id)
				if browse_time > 0:
					add_step(f"{block.block_id}-browse", start + (travel_time + shop_time)/60, "Wait", store,
							{"minutes": browse_time, "activity": "browsing", "synth": "heuristic"}, block.block_id)
				add_step(f"{block.block_id}-travel-home", start + dur_min/60 - travel_time/60, "Travel", "in_transit",
						{"to": "home", "synth": "heuristic"}, block.block_id)
			else:
				# Online shopping fallback
				add_step(f"{block.block_id}-shop", start, "Wait", "home",
						{"minutes": dur_min, "activity": "online_shopping", "synth": "heuristic"}, block.block_id)
			continue
		
		# === Childcare ===
		if op == "childcare":
			# 70% at home, 30% at childcare facility
			if rng.random() < 0.7:
				add_step(f"{block.block_id}-childcare", start, "Wait", "home",
						{"minutes": dur_min, "activity": "childcare_home", "synth": "heuristic"}, block.block_id)
			else:
				facility = choose_place(agent, "school", rng)  # Use school as proxy for daycare
				if facility:
					travel_time = 10
					add_step(f"{block.block_id}-travel-to", start, "Travel", "in_transit",
							{"to": facility, "synth": "heuristic"}, block.block_id)
					add_step(f"{block.block_id}-dropoff", start + travel_time/60, "Wait", facility,
							{"minutes": dur_min - 2*travel_time, "activity": "childcare_facility", "synth": "heuristic"}, block.block_id)
					add_step(f"{block.block_id}-travel-home", start + dur_min/60 - travel_time/60, "Travel", "in_transit",
							{"to": "home", "synth": "heuristic"}, block.block_id)
				else:
					add_step(f"{block.block_id}-childcare", start, "Wait", "home",
							{"minutes": dur_min, "activity": "childcare_home", "synth": "heuristic"}, block.block_id)
			continue
		
		# === Leisure out ===
		if op == "leisure_out":
			venue = choose_place(agent, "social", rng)
			if not venue:
				venue = choose_place(agent, "retail", rng)  # Fallback to retail as proxy for social venues
			if venue:
				travel_time = 15
				add_step(f"{block.block_id}-travel-to", start, "Travel", "in_transit",
						{"to": venue, "synth": "heuristic"}, block.block_id)
				add_step(f"{block.block_id}-leisure", start + travel_time/60, "Wait", venue,
						{"minutes": dur_min - 2*travel_time, "activity": "socializing", "synth": "heuristic"}, block.block_id)
				add_step(f"{block.block_id}-travel-home", start + dur_min/60 - travel_time/60, "Travel", "in_transit",
						{"to": "home", "synth": "heuristic"}, block.block_id)
			else:
				# Stay home if no venue
				add_step(f"{block.block_id}-leisure", start, "Wait", "home",
						{"minutes": dur_min, "activity": "leisure_home", "synth": "heuristic"}, block.block_id)
			continue
		
		# === Personal care out (salon, barber, spa, etc.) ===
		if op == "personal_care_out":
			salon = choose_place(agent, "retail", rng)  # Use retail as proxy for personal services
			if salon:
				travel_time = 15
				service_time = min(dur_min - 2*travel_time, 45)
				wait_time = max(dur_min - 2*travel_time - service_time, 0)
				add_step(f"{block.block_id}-travel-to", start, "Travel", "in_transit",
						{"to": salon, "synth": "heuristic"}, block.block_id)
				if wait_time > 0:
					add_step(f"{block.block_id}-wait", start + travel_time/60, "Wait", salon,
							{"minutes": wait_time, "activity": "waiting", "synth": "heuristic"}, block.block_id)
				if service_time > 0:
					add_step(f"{block.block_id}-service", start + (travel_time + wait_time)/60, "Exchange", salon,
							{"counterparty": salon, "receive": {"SERVICE": 1}, "synth": "heuristic"}, block.block_id)
				add_step(f"{block.block_id}-travel-home", start + dur_min/60 - travel_time/60, "Travel", "in_transit",
						{"to": "home", "synth": "heuristic"}, block.block_id)
			else:
				# Personal care at home fallback
				add_step(f"{block.block_id}-personal", start, "Wait", "home",
						{"minutes": dur_min, "activity": "personal_care", "synth": "heuristic"}, block.block_id)
			continue
		
		# === Household management (errands: bank, post office, etc.) ===
		if op == "household_management":
			errand_location = choose_place(agent, "retail", rng)  # Use retail as proxy for service locations
			if errand_location:
				travel_time = 12
				transaction_time = min(dur_min - 2*travel_time, 20)
				wait_time = max(dur_min - 2*travel_time - transaction_time, 0)
				add_step(f"{block.block_id}-travel-to", start, "Travel", "in_transit",
						{"to": errand_location, "synth": "heuristic"}, block.block_id)
				if transaction_time > 0:
					add_step(f"{block.block_id}-errand", start + travel_time/60, "Exchange", errand_location,
							{"counterparty": errand_location, "receive": {"SERVICE": 1}, "synth": "heuristic"}, block.block_id)
				if wait_time > 0:
					add_step(f"{block.block_id}-wait", start + (travel_time + transaction_time)/60, "Wait", errand_location,
							{"minutes": wait_time, "activity": "waiting", "synth": "heuristic"}, block.block_id)
				add_step(f"{block.block_id}-travel-home", start + dur_min/60 - travel_time/60, "Travel", "in_transit",
						{"to": "home", "synth": "heuristic"}, block.block_id)
			else:
				# Online/phone errands fallback
				add_step(f"{block.block_id}-errand", start, "Wait", "home",
						{"minutes": dur_min, "activity": "household_management", "synth": "heuristic"}, block.block_id)
			continue
		
		# === Travel support (picking up/dropping off others) ===
		if op == "travel_support":
			# This is typically short trips to transport others
			destination = choose_place(agent, "school", rng)  # Schools are common pickup/dropoff points
			if not destination:
				destination = choose_place(agent, "work", rng)
			if destination:
				# Round trip: home -> destination -> home
				one_way_time = dur_min / 2
				add_step(f"{block.block_id}-travel-to", start, "Travel", "in_transit",
						{"to": destination, "synth": "heuristic"}, block.block_id)
				add_step(f"{block.block_id}-dropoff", start + one_way_time/60, "Wait", destination,
						{"minutes": 5, "activity": "dropoff_pickup", "synth": "heuristic"}, block.block_id)
				add_step(f"{block.block_id}-travel-home", start + (one_way_time + 5)/60, "Travel", "in_transit",
						{"to": "home", "synth": "heuristic"}, block.block_id)
			else:
				# Fallback: just mark as travel time
				add_step(f"{block.block_id}-support", start, "Travel", "in_transit",
						{"to": "home", "minutes": dur_min, "synth": "heuristic"}, block.block_id)
			continue
		
		# === Generic fallback (should rarely be reached now) ===
		add_step(f"{block.block_id}-wait", start, "Wait", loc_hint,
				{"minutes": dur_min, "activity": f"unhandled_{op}", "synth": "heuristic"}, block.block_id)
	
	return steps


def generate_operator_steps(
	agent,
	goal: str,
	world_context: str,
	blocks: List[ActivityBlock],
	target_date: date,
) -> tuple[List[OperatorStep], Optional[str], Optional[str]]:
	llm_out = _call_llm(agent, goal, world_context, blocks, target_date)
	if llm_out:
		steps, reasoning, model_name = llm_out
		return steps, reasoning, model_name
	return _heuristic_steps(agent, blocks, target_date), None, None
