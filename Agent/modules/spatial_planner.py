#!/usr/bin/env python3
"""
Spatial planner for location-aware plan execution.

This module stitches together agent knowledge, preferences, Valhalla routing,
and lightweight LLM guidance to turn symbolic plan steps (e.g. "Travel to grocery")
into concrete destinations with realistic travel times.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import json
import math
import random
from typing import Any, Dict, List, Optional, Tuple

from Database.managers import get_simulations_manager
from Database.geo_database_manager_postgis import get_geo_database_manager
from Utils.routing import RouteResult, get_routing_manager
from Utils.spatial.knowledge_config import DEFAULT_CATEGORY_WEIGHTS, DEFAULT_NEED_INTENT_MAP
from Utils.api_manager import APIManager


@dataclass
class PlaceHandle:
	id: str
	name: str
	lat: float
	lon: float
	category: str
	subcategory: str
	source: str
	confidence: float = 0.0
	metadata: Dict[str, Any] = field(default_factory=dict)

	def as_dict(self) -> Dict[str, Any]:
		return {
			"id": self.id,
			"name": self.name,
			"lat": self.lat,
			"lon": self.lon,
			"category": self.category,
			"subcategory": self.subcategory,
			"source": self.source,
			"confidence": self.confidence,
			"metadata": self.metadata,
		}


@dataclass
class Candidate:
	place: PlaceHandle
	knowledge_strength: float
	opinion: float
	distance_km: float
	score: float
	source: str
	reason: str


class SpatialPlanner:
	"""Resolves travel steps into concrete destinations and routes."""

	def __init__(self, simulation_id: str):
		self.simulation_id = simulation_id
		self.sim_manager = get_simulations_manager()
		self.geo_manager = get_geo_database_manager()
		self.routing = get_routing_manager()
		self._home_cache: Dict[str, Tuple[float, float]] = {}
		self._known_cache: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}
		self._poi_coord_cache: Dict[int, Tuple[float, float]] = {}

	def prepare_travel(
		self,
		agent: "Agent",
		params: Dict[str, Any],
		location_hint: Optional[str],
		world: "World",
		now: datetime,
	) -> Dict[str, Any]:
		"""
		Resolve a Travel action parameters dict into a concrete destination and route.
		Returns a mutated params dict with:
			- to: resolved place id
			- place_handle: structured place info
			- route: travel metrics
			- mode: chosen transport mode
			- planner_metadata: debug metadata for inspection
		"""

		# If already resolved with a place handle and route, honour existing data
		if params.get("route") and params.get("place_handle"):
			return params

		destination_hint = params.get("to") or location_hint or "home"
		place_handle: Optional[PlaceHandle] = None

		# Ensure we have the agent's home location
		home_lat, home_lon = self._get_agent_home(agent)

		# Determine origin coordinates (current position)
		current_lat, current_lon = self._get_agent_current_position(agent, world, default=(home_lat, home_lon))

		# If destination already references a concrete place id we recognise, build handle and route directly
		if isinstance(destination_hint, dict) and destination_hint.get("id"):
			place_handle = self._place_from_dict(destination_hint)
		elif isinstance(destination_hint, str) and destination_hint.startswith("osm:"):
			place_handle = self._place_from_osm(destination_hint)
		elif isinstance(destination_hint, str) and destination_hint.lower() == "home":
			place_handle = PlaceHandle(
				id="home",
				name="Home",
				lat=home_lat,
				lon=home_lon,
				category="residence",
				subcategory="home",
				source="home",
				confidence=1.0,
			)

		if place_handle is None:
			categories = self._infer_categories(destination_hint, agent)
			candidates = self._collect_candidates(agent, home_lat, home_lon, categories)

			if not candidates:
				raise RuntimeError(f"No viable destination candidates for hint '{destination_hint}'")

			place_handle = self._choose_candidate(agent, destination_hint, candidates)

		# Determine mode and compute route
		mode = self._choose_mode(agent, place_handle, current_lat, current_lon, home_lat, home_lon)
		route_result = self.routing.get_route(
			start_lat=current_lat,
			start_lon=current_lon,
			end_lat=place_handle.lat,
			end_lon=place_handle.lon,
			mode=mode,
			include_geometry=True,
		)

		params["to"] = place_handle.id
		params["mode"] = route_result.mode
		params["route"] = {
			"distance_km": route_result.distance_km,
			"duration_minutes": route_result.duration_minutes,
			"provider": route_result.provider,
			"polyline": route_result.polyline,
		}
		params["place_handle"] = place_handle.as_dict()
		params.setdefault("planner_metadata", {})["generated_at"] = now.isoformat()
		return params

	def on_travel_success(self, agent: "Agent", params: Dict[str, Any], event_time: datetime) -> None:
		"""
		Update simulation knowledge tables when a travel action succeeds.
		"""
		place_info = params.get("place_handle") or {}
		if not place_info:
			return

		place_id = place_info.get("id")
		if not place_id or not place_id.startswith("osm:"):
			return

		try:
			osm_id = int(place_id.split(":")[1])
		except (IndexError, ValueError):
			return

		route = params.get("route") or {}
		distance_km = float(route.get("distance_km") or 0.0)
		if distance_km <= 0.0:
			home_lat, home_lon = self._get_agent_home(agent)
			distance_km = _haversine_km(home_lat, home_lon, place_info.get("lat"), place_info.get("lon"))

		self.sim_manager.upsert_agent_poi_seen(
			self.simulation_id,
			str(agent.agent_id),
			osm_id=osm_id,
			distance_km=distance_km,
			seen_increment=1,
			visited=True,
			source="need",
			event_time=event_time,
		)

	# ----- candidate discovery -------------------------------------------------

	def _collect_candidates(
		self,
		agent: "Agent",
		home_lat: float,
		home_lon: float,
		categories: List[str],
	) -> List[Candidate]:
		known_rows = self._get_known_places(agent)
		opinion_store = getattr(agent, "opinions", None)
		candidates: List[Candidate] = []

		for row in known_rows:
			if categories and row.get("subcategory_name") not in categories and row.get("category_name") not in categories:
				continue

			place = PlaceHandle(
				id=f"osm:{row['osm_id']}",
				name=row.get("display_name") or row.get("name") or row.get("subcategory_name") or "POI",
				lat=float(row.get("lat")),
				lon=float(row.get("lon")),
				category=row.get("category_name") or "unknown",
				subcategory=row.get("subcategory_name") or "unknown",
				source="known",
				confidence=float(row.get("knowledge_strength") or 0.0),
				metadata={
					"times_seen": row.get("times_seen"),
					"times_visited": row.get("number_of_times_visited"),
					"familiarity_score": row.get("familiarity_score"),
				},
			)
			distance = _haversine_km(home_lat, home_lon, place.lat, place.lon)
			opinion = opinion_store.get_place_bias(place.id) if opinion_store else 0.0
			score = self._score_candidate(place, distance, place.confidence, opinion)
			candidates.append(Candidate(place=place, knowledge_strength=place.confidence, opinion=opinion, distance_km=distance, score=score, source="known", reason="known_place"))

		if not candidates or len(candidates) < 3:
			discovered = self._search_new_places(agent, home_lat, home_lon, categories)
			for item in discovered:
				opinion = 0.0
				confidence = 0.15  # new place; low confidence
				distance = _haversine_km(home_lat, home_lon, item.lat, item.lon)
				score = self._score_candidate(item, distance, confidence, opinion, novelty_boost=True)
				candidates.append(
					Candidate(
						place=item,
						knowledge_strength=confidence,
						opinion=opinion,
						distance_km=distance,
						score=score,
						source="search",
						reason="search_result",
					)
				)

		return sorted(candidates, key=lambda c: c.score, reverse=True)

	def _search_new_places(
		self,
		agent: "Agent",
		home_lat: float,
		home_lon: float,
		categories: List[str],
	) -> List[PlaceHandle]:
		mode = self._preferred_mode(agent)
		radius_km = self._mode_radius_km(mode)
		lat_pad = radius_km / 111.0
		lon_pad = radius_km / max(0.0001, 111.0 * math.cos(math.radians(home_lat)))

		pois = self.geo_manager.get_pois_in_bounds(
			min_lat=home_lat - lat_pad,
			min_lon=home_lon - lon_pad,
			max_lat=home_lat + lat_pad,
			max_lon=home_lon + lon_pad,
			category=None,
			limit=200,
		)

		selected: List[PlaceHandle] = []
		for row in pois:
			if not row.get("osm_id"):
				continue
			subcat = (row.get("subcategory") or row.get("category") or "").lower()
			cat = (row.get("category") or "").lower()
			if categories and subcat not in categories and cat not in categories:
				continue
			place = PlaceHandle(
				id=f"osm:{int(row['osm_id'])}",
				name=row.get("name") or subcat or cat or "POI",
				lat=float(row.get("latitude") or row.get("lat")),
				lon=float(row.get("longitude") or row.get("lon")),
				category=cat or "unknown",
				subcategory=subcat or "unknown",
				source="search",
				confidence=0.1,
				metadata={"properties": row.get("properties") or {}},
			)
			selected.append(place)
			if len(selected) >= 25:
				break

		# Ensure the POIs exist in poi_categories for downstream persistence
		try:
			osm_ids = [int(p.id.split(":")[1]) for p in selected if p.id.startswith("osm:")]
			if osm_ids:
				self.sim_manager._ensure_poi_categories_exist(osm_ids)  # type: ignore[attr-defined]
		except Exception:
			pass

		return selected

	# ----- selection helpers ---------------------------------------------------

	def _score_candidate(
		self,
		place: PlaceHandle,
		distance_km: float,
		knowledge_strength: float,
		opinion: float,
		novelty_boost: bool = False,
	) -> float:
		category_weight = DEFAULT_CATEGORY_WEIGHTS.get(place.subcategory, DEFAULT_CATEGORY_WEIGHTS.get(place.category, 0.4))
		distance_term = max(0.0, 1.0 - (distance_km / 15.0))
		opinion_term = (opinion + 1.0) / 2.0  # scale -1..1 -> 0..1
		score = knowledge_strength * 0.6 + opinion_term * 0.25 + distance_term * 0.1 + category_weight * 0.05
		if novelty_boost:
			score += 0.05
		score += random.uniform(-0.03, 0.03)
		return score

	def _choose_candidate(self, agent: "Agent", hint: str, candidates: List[Candidate]) -> PlaceHandle:
		if len(candidates) == 1:
			return candidates[0].place

		top = candidates[0]
		second = candidates[1]
		if abs(top.score - second.score) < 0.15:
			llm_choice = self._llm_break_tie(agent, hint, candidates[:3])
			if llm_choice:
				for cand in candidates:
					if cand.place.id == llm_choice:
						return cand.place
		return top.place

	def _llm_break_tie(self, agent: "Agent", hint: str, candidates: List[Candidate]) -> Optional[str]:
		try:
			api_manager = getattr(agent.action, "api_manager", None) or APIManager.get_instance()
		except Exception:
			return None

		serialized_options = [
			{
				"id": cand.place.id,
				"name": cand.place.name,
				"category": cand.place.category,
				"subcategory": cand.place.subcategory,
				"distance_km": round(cand.distance_km, 2),
				"knowledge_strength": round(cand.knowledge_strength, 3),
				"opinion": round(cand.opinion, 3),
				"score": round(cand.score, 3),
				"source": cand.source,
			}
			for cand in candidates
		]

		agent_summary = getattr(agent, "llm_summary", None) or getattr(agent, "l2_summary", None) or "An everyday person."
		prompt = (
			"Choose the best real-world place for the agent to visit based on their preferences and the task.\n"
			f"Task hint: {hint}\n"
			f"Agent summary: {agent_summary}\n"
			"Options:\n"
			f"{json.dumps(serialized_options, indent=2)}\n\n"
			"Respond with strict JSON: {\"choice\": \"<ID>\", \"reason\": \"one-sentence\"}"
		)

		try:
			response, *_ = api_manager.make_request(prompt=prompt, intelligence_level=2, max_tokens=120, temperature=0.4)
			data = json.loads(response)
			return data.get("choice")
		except Exception:
			return None

	# ----- inference utilities -------------------------------------------------

	def _infer_categories(self, label: str, agent: "Agent") -> List[str]:
		label_norm = (label or "").lower().replace("-", " ").replace("_", " ")
		matches: List[str] = []

		for need, cats in DEFAULT_NEED_INTENT_MAP.items():
			if need in label_norm or label_norm in need:
				matches.extend(cats)

		# Simple heuristics for common activities
		heuristics = [
			("grocery", ["grocery", "supermarket"]),
			("coffee", ["cafe"]),
			("lunch", ["restaurant", "fast_food"]),
			("dinner", ["restaurant"]),
			("pharmacy", ["pharmacy"]),
			("doctor", ["clinic", "hospital"]),
			("park", ["park"]),
			("exercise", ["gym", "sports"]),
			("gas", ["gas_station", "fuel"]),
			("bank", ["bank", "atm"]),
		]
		for keyword, cats in heuristics:
			if keyword in label_norm:
				matches.extend(cats)

		if not matches:
			# Use agent interests if available
			interests = getattr(agent, "l2_data", None)
			if interests:
				for attr in dir(interests):
					if label_norm in attr.lower():
						matches.append(attr.lower())

		return sorted(set(matches))

	def _choose_mode(
		self,
		agent: "Agent",
		place: PlaceHandle,
		current_lat: float,
		current_lon: float,
		home_lat: float,
		home_lon: float,
	) -> str:
		distance_km = _haversine_km(current_lat, current_lon, place.lat, place.lon)
		has_vehicle = getattr(agent, "has_vehicle", False)
		if not has_vehicle and getattr(agent, "l2_data", None):
			vehicles_val = getattr(agent.l2_data, "vehiclesvalue", None)
			has_vehicle = bool(vehicles_val and float(vehicles_val) > 0)

		if distance_km <= 2.0:
			return "walk"
		if distance_km <= 8.0 and not has_vehicle:
			return "bike"
		return "car" if has_vehicle else "walk"

	def _preferred_mode(self, agent: "Agent") -> str:
		has_vehicle = getattr(agent, "has_vehicle", False)
		if has_vehicle:
			return "car"
		return "walk"

	def _mode_radius_km(self, mode: str) -> float:
		if mode in {"car", "auto"}:
			return 25.0
		if mode in {"bike", "bicycle"}:
			return 10.0
		return 4.0

	def _get_agent_home(self, agent: "Agent") -> Tuple[float, float]:
		key = str(agent.agent_id)
		if key in self._home_cache:
			return self._home_cache[key]

		location = self.sim_manager.get_agent_home_location(self.simulation_id, str(agent.agent_id))
		if not location:
			raise RuntimeError(f"Agent {agent.agent_id} missing home location")
		coords = (float(location["lat"]), float(location["lon"]))
		self._home_cache[key] = coords
		return coords

	def _get_agent_current_position(
		self,
		agent: "Agent",
		world: "World",
		default: Tuple[float, float],
	) -> Tuple[float, float]:
		place_id = world.state.get_agent_position(str(agent.agent_id))
		if not place_id:
			return default
		if place_id == "home":
			return self._get_agent_home(agent)
		if place_id.startswith("osm:"):
			try:
				osm_id = int(place_id.split(":")[1])
			except (IndexError, ValueError):
				return default
			coords = self._poi_coord_cache.get(osm_id)
			if not coords:
				coords_map = self.sim_manager.get_poi_coords([osm_id])
				coords = coords_map.get(osm_id)
				if coords:
					self._poi_coord_cache[osm_id] = coords
			if coords:
				return (float(coords[0]), float(coords[1]))
		return default

	def _get_known_places(self, agent: "Agent") -> List[Dict[str, Any]]:
		key = str(agent.agent_id)
		cache_entry = self._known_cache.get(key)
		if cache_entry and (datetime.utcnow().timestamp() - cache_entry[0]) < 300:
			return cache_entry[1]
		rows = self.sim_manager.get_agent_poi_knowledge(self.simulation_id, str(agent.agent_id), limit=200)
		self._known_cache[key] = (datetime.utcnow().timestamp(), rows)
		return rows

	def _place_from_dict(self, data: Dict[str, Any]) -> PlaceHandle:
		return PlaceHandle(
			id=data.get("id"),
			name=data.get("name", "POI"),
			lat=float(data.get("lat")),
			lon=float(data.get("lon")),
			category=data.get("category", "unknown"),
			subcategory=data.get("subcategory", "unknown"),
			source=data.get("source", "user"),
			confidence=float(data.get("confidence", 0.5)),
			metadata=data.get("metadata", {}),
		)

	def _place_from_osm(self, place_id: str) -> Optional[PlaceHandle]:
		try:
			osm_id = int(place_id.split(":")[1])
		except (IndexError, ValueError):
			return None

		coords_map = self.sim_manager.get_poi_coords([osm_id])
		coords = coords_map.get(osm_id)
		if not coords:
			return None

		return PlaceHandle(
			id=place_id,
			name=f"Place {osm_id}",
			lat=float(coords[0]),
			lon=float(coords[1]),
			category="unknown",
			subcategory="unknown",
			source="explicit",
			confidence=0.5,
		)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
	r = 6371.0
	phi1, phi2 = math.radians(lat1), math.radians(lat2)
	dphi = math.radians(lat2 - lat1)
	dlambda = math.radians(lon2 - lon1)
	a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
	c = 2 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1 - a)))
	return r * c
