#!/usr/bin/env python3
"""
Route Interpolation Utilities

Handles smooth agent position interpolation along routes for frontend scrubbing.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import List, Tuple, Optional, Dict, Any


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
	"""Calculate great-circle distance between two points on Earth (in km)."""
	R = 6371.0  # Earth radius in km
	lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
	dlat = lat2 - lat1
	dlon = lon2 - lon1
	a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
	c = 2 * math.asin(math.sqrt(a))
	return R * c


def interpolate_point(lat1: float, lon1: float, lat2: float, lon2: float, fraction: float) -> Tuple[float, float]:
	"""
	Linearly interpolate between two lat/lon points.
	
	Args:
		lat1, lon1: Start point
		lat2, lon2: End point
		fraction: Interpolation fraction (0.0 to 1.0)
	
	Returns:
		Tuple of (latitude, longitude)
	"""
	lat = lat1 + (lat2 - lat1) * fraction
	lon = lon1 + (lon2 - lon1) * fraction
	return lat, lon


def interpolate_route_timeline(
	route_coords: List[List[float]],
	start_time: datetime,
	end_time: datetime,
	interval_minutes: int = 1
) -> List[Dict[str, Any]]:
	"""
	Interpolate agent position along a route at regular time intervals.
	
	Args:
		route_coords: List of [lat, lon] pairs along the route
		start_time: Route start time
		end_time: Route end time
		interval_minutes: Time interval for interpolation (default 1 minute)
	
	Returns:
		List of dicts with {timestamp, lat, lon, segment_index}
	"""
	if not route_coords or len(route_coords) < 2:
		return []
	
	total_duration = (end_time - start_time).total_seconds() / 60.0  # minutes
	if total_duration <= 0:
		return []
	
	# Calculate cumulative distances along route
	cumulative_dist = [0.0]
	for i in range(1, len(route_coords)):
		lat1, lon1 = route_coords[i - 1]
		lat2, lon2 = route_coords[i]
		dist = haversine_distance(lat1, lon1, lat2, lon2)
		cumulative_dist.append(cumulative_dist[-1] + dist)
	
	total_distance = cumulative_dist[-1]
	if total_distance == 0:
		return []
	
	# Generate timeline points
	timeline = []
	current_time = start_time
	
	while current_time <= end_time:
		# Calculate how far along the route we should be at this time
		elapsed_minutes = (current_time - start_time).total_seconds() / 60.0
		progress_fraction = min(1.0, elapsed_minutes / total_duration)
		target_distance = progress_fraction * total_distance
		
		# Find the segment containing this distance
		segment_idx = 0
		for i in range(len(cumulative_dist) - 1):
			if cumulative_dist[i] <= target_distance <= cumulative_dist[i + 1]:
				segment_idx = i
				break
		
		# Interpolate within the segment
		if segment_idx < len(route_coords) - 1:
			segment_start_dist = cumulative_dist[segment_idx]
			segment_end_dist = cumulative_dist[segment_idx + 1]
			segment_length = segment_end_dist - segment_start_dist
			
			if segment_length > 0:
				segment_progress = (target_distance - segment_start_dist) / segment_length
			else:
				segment_progress = 0.0
			
			lat1, lon1 = route_coords[segment_idx]
			lat2, lon2 = route_coords[segment_idx + 1]
			lat, lon = interpolate_point(lat1, lon1, lat2, lon2, segment_progress)
			
			timeline.append({
				'timestamp': current_time,
				'lat': lat,
				'lon': lon,
				'segment_index': segment_idx,
				'progress_fraction': progress_fraction
			})
		
		current_time += timedelta(minutes=interval_minutes)
	
	# Ensure end point is included
	if timeline and timeline[-1]['timestamp'] < end_time:
		lat, lon = route_coords[-1]
		timeline.append({
			'timestamp': end_time,
			'lat': lat,
			'lon': lon,
			'segment_index': len(route_coords) - 2,
			'progress_fraction': 1.0
		})
	
	return timeline


def decode_polyline(polyline_str: str) -> List[List[float]]:
	"""
	Decode a Google/Valhalla encoded polyline into list of [lat, lon] pairs.
	
	Args:
		polyline_str: Encoded polyline string
	
	Returns:
		List of [lat, lon] pairs
	"""
	try:
		import polyline as polyline_lib
		# polyline library returns list of (lat, lon) tuples
		coords = polyline_lib.decode(polyline_str)
		return [[lat, lon] for lat, lon in coords]
	except ImportError:
		# Fallback: Manual decode (simplified version)
		return _manual_decode_polyline(polyline_str)
	except Exception:
		return []


def _manual_decode_polyline(polyline_str: str) -> List[List[float]]:
	"""Manual polyline decoding (simplified, may not handle all edge cases)."""
	coords = []
	index = 0
	lat = 0
	lon = 0
	
	while index < len(polyline_str):
		# Decode latitude
		result = 0
		shift = 0
		while True:
			b = ord(polyline_str[index]) - 63
			index += 1
			result |= (b & 0x1f) << shift
			shift += 5
			if b < 0x20:
				break
		dlat = ~(result >> 1) if result & 1 else result >> 1
		lat += dlat
		
		# Decode longitude
		result = 0
		shift = 0
		while True:
			b = ord(polyline_str[index]) - 63
			index += 1
			result |= (b & 0x1f) << shift
			shift += 5
			if b < 0x20:
				break
		dlon = ~(result >> 1) if result & 1 else result >> 1
		lon += dlon
		
		coords.append([lat / 1e5, lon / 1e5])
	
	return coords


def get_position_at_time(
	route_coords: List[List[float]],
	start_time: datetime,
	end_time: datetime,
	query_time: datetime
) -> Optional[Tuple[float, float]]:
	"""
	Get interpolated position at a specific time during a route.
	
	Args:
		route_coords: List of [lat, lon] pairs along the route
		start_time: Route start time
		end_time: Route end time
		query_time: Time to query position
	
	Returns:
		Tuple of (lat, lon) or None if query_time is outside route
	"""
	if not route_coords or query_time < start_time or query_time > end_time:
		return None
	
	total_duration = (end_time - start_time).total_seconds()
	if total_duration <= 0:
		return route_coords[0][0], route_coords[0][1]
	
	elapsed = (query_time - start_time).total_seconds()
	progress = min(1.0, elapsed / total_duration)
	
	# Calculate cumulative distances
	cumulative_dist = [0.0]
	for i in range(1, len(route_coords)):
		lat1, lon1 = route_coords[i - 1]
		lat2, lon2 = route_coords[i]
		dist = haversine_distance(lat1, lon1, lat2, lon2)
		cumulative_dist.append(cumulative_dist[-1] + dist)
	
	total_distance = cumulative_dist[-1]
	if total_distance == 0:
		return route_coords[0][0], route_coords[0][1]
	
	target_distance = progress * total_distance
	
	# Find segment
	for i in range(len(cumulative_dist) - 1):
		if cumulative_dist[i] <= target_distance <= cumulative_dist[i + 1]:
			segment_length = cumulative_dist[i + 1] - cumulative_dist[i]
			if segment_length > 0:
				segment_progress = (target_distance - cumulative_dist[i]) / segment_length
			else:
				segment_progress = 0.0
			
			lat1, lon1 = route_coords[i]
			lat2, lon2 = route_coords[i + 1]
			return interpolate_point(lat1, lon1, lat2, lon2, segment_progress)
	
	# Fallback to last point
	return route_coords[-1][0], route_coords[-1][1]



