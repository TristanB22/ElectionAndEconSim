#!/usr/bin/env python3
"""
Routing utilities shared by simulation modules.

Provides a small cached client around the Valhalla routing service with a
graceful fallback to Haversine estimates when Valhalla is unavailable.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import os
import threading
from typing import Dict, Optional, Tuple

import requests

try:
	from Utils.env_loader import load_environment
	load_environment()
except Exception:
	# Environment loader optional; ignore failures so env vars can be provided externally.
	pass

# Lazy import Reporting config to avoid circular dependencies and missing deps
try:
	from Reporting.config import settings  # Reuse unified configuration
	from Reporting.services.routing_config import get_costing_options, validate_mode
except ImportError as e:
	# Fall back to loading from env directly if Reporting module has dependency issues
	class FallbackSettings:
		def __init__(self):
			self.VALHALLA_BASE_URL = os.getenv("VALHALLA_BASE_URL", "http://localhost:8002")
			timeout_str = os.getenv("VALHALLA_TIMEOUT", "10")
			self.VALHALLA_TIMEOUT = int(float(timeout_str))  # Handle float strings
	settings = FallbackSettings()
	def get_costing_options(mode: str):
		return {}
	def validate_mode(mode: str):
		return mode

try:
	import polyline  # type: ignore
	_HAS_POLYLINE = True
except Exception:  # pragma: no cover
	_HAS_POLYLINE = False


_DEFAULT_SPEEDS_KMH = {
	"auto": float(os.getenv("ROUTING_DEFAULT_AUTO_KMH", "45.0")),
	"pedestrian": float(os.getenv("ROUTING_DEFAULT_PEDESTRIAN_KMH", "5.0")),
	"bicycle": float(os.getenv("ROUTING_DEFAULT_BICYCLE_KMH", "16.0")),
}


@dataclass(frozen=True)
class RouteResult:
	mode: str
	distance_km: float
	duration_minutes: float
	provider: str
	coordinates: Optional[list] = None
	polyline: Optional[str] = None


class _LRUCache:
	def __init__(self, max_size: int = 512) -> None:
		self.max_size = max_size
		self._store: Dict[Tuple, Tuple[RouteResult, float]] = {}
		self._order: Dict[Tuple, float] = {}
		self._lock = threading.Lock()
		self._counter = 0.0

	def get(self, key: Tuple) -> Optional[RouteResult]:
		with self._lock:
			entry = self._store.get(key)
			if not entry:
				return None
			result, _ = entry
			self._counter += 1.0
			self._order[key] = self._counter
			return result

	def set(self, key: Tuple, value: RouteResult) -> None:
		with self._lock:
			self._counter += 1.0
			self._store[key] = (value, self._counter)
			self._order[key] = self._counter
			if len(self._store) > self.max_size:
				# Evict the least recently touched key
				oldest_key = min(self._order, key=self._order.get)
				self._store.pop(oldest_key, None)
				self._order.pop(oldest_key, None)


class RoutingManager:
	"""Simple cached Valhalla client with haversine fallback."""

	_MODE_ALIAS = {
		"car": "auto",
		"drive": "auto",
		"walk": "pedestrian",
		"pedestrian": "pedestrian",
		"bike": "bicycle",
		"bicycle": "bicycle",
	}

	def __init__(self, cache_size: int = 512) -> None:
		self.use_valhalla = os.getenv("USE_VALHALLA_ROUTING", "true").lower() in {"1", "true", "yes", "on"}
		self.base_url = settings.VALHALLA_BASE_URL
		self.timeout = settings.VALHALLA_TIMEOUT
		self.session = requests.Session()
		self.cache = _LRUCache(cache_size=cache_size)

	def get_route(
		self,
		start_lat: float,
		start_lon: float,
		end_lat: float,
		end_lon: float,
		mode: str = "walk",
		include_geometry: bool = True,
	) -> RouteResult:
		"""Return a cached Valhalla route (or haversine estimate on failure)."""

		mode_key = self._MODE_ALIAS.get(mode.lower(), mode.lower())
		cache_key = (
			round(start_lat, 4),
			round(start_lon, 4),
			round(end_lat, 4),
			round(end_lon, 4),
			mode_key,
			include_geometry,
		)

		cached = self.cache.get(cache_key)
		if cached:
			return cached

		if self.use_valhalla:
			try:
				validate_mode(mode_key)
				result = self._call_valhalla(
					start_lat, start_lon, end_lat, end_lon, mode_key, include_geometry=include_geometry
				)
				self.cache.set(cache_key, result)
				return result
			except Exception:
				# Fall back gracefully
				pass

		result = self._haversine_fallback(start_lat, start_lon, end_lat, end_lon, mode_key)
		self.cache.set(cache_key, result)
		return result

	def _call_valhalla(
		self,
		start_lat: float,
		start_lon: float,
		end_lat: float,
		end_lon: float,
		mode: str,
		include_geometry: bool = True,
	) -> RouteResult:
		payload = {
			"locations": [
				{"lat": start_lat, "lon": start_lon},
				{"lat": end_lat, "lon": end_lon},
			],
			"costing": mode,
			"units": "kilometers",
			"shape_format": "polyline6" if include_geometry else "none",
			"costing_options": {mode: get_costing_options(mode, None)},
			"directions_options": {"units": "kilometers", "narrative": False},
		}

		resp = self.session.post(
			f"{self.base_url}/route",
			json=payload,
			headers={"Content-Type": "application/json"},
			timeout=self.timeout,
		)
		resp.raise_for_status()
		data = resp.json()

		trip = data.get("trip", {})
		leg = (trip.get("legs") or [{}])[0]
		summary = leg.get("summary", {})
		distance_km = float(summary.get("length", 0.0))
		duration_minutes = float(summary.get("time", 0.0)) / 60.0

		coordinates = None
		encoded = None
		if include_geometry and _HAS_POLYLINE:
			try:
				encoded = leg.get("shape")
				if encoded:
					decoded = polyline.decode(encoded, precision=6)
					coordinates = [[lon, lat] for lat, lon in decoded]
			except Exception:
				encoded = None
				coordinates = None

		return RouteResult(
			mode=mode,
			distance_km=distance_km,
			duration_minutes=duration_minutes,
			provider="valhalla",
			coordinates=coordinates,
			polyline=encoded,
		)

	def _haversine_fallback(
		self,
		start_lat: float,
		start_lon: float,
		end_lat: float,
		end_lon: float,
		mode: str,
	) -> RouteResult:
		distance_km = _haversine_km(start_lat, start_lon, end_lat, end_lon)
		speed_kmh = _DEFAULT_SPEEDS_KMH.get(mode, _DEFAULT_SPEEDS_KMH["pedestrian"])
		duration_minutes = (distance_km / max(speed_kmh, 0.1)) * 60.0
		return RouteResult(
			mode=mode,
			distance_km=distance_km,
			duration_minutes=duration_minutes,
			provider="haversine",
			coordinates=None,
			polyline=None,
		)


_ROUTING_MANAGER: Optional[RoutingManager] = None
_ROUTING_LOCK = threading.Lock()


def get_routing_manager() -> RoutingManager:
	global _ROUTING_MANAGER
	if _ROUTING_MANAGER is None:
		with _ROUTING_LOCK:
			if _ROUTING_MANAGER is None:
				cache_size = int(os.getenv("ROUTING_CACHE_SIZE", "512"))
				_ROUTING_MANAGER = RoutingManager(cache_size=cache_size)
	return _ROUTING_MANAGER


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
	radius = 6371.0
	phi1, phi2 = math.radians(lat1), math.radians(lat2)
	dphi = math.radians(lat2 - lat1)
	dlambda = math.radians(lon2 - lon1)
	a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
	c = 2 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1 - a)))
	return radius * c
