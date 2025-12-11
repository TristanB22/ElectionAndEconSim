#!/usr/bin/env python3
"""
Dataclasses describing intermediate planning artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ActivityBlock:
	block_id: str
	operator_group: str
	start_hour: int
	duration_minutes: float
	location_hint: Optional[str] = None
	social_hint: Dict[str, float] = field(default_factory=dict)
	anchor: bool = False
	metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OperatorStep:
	step_id: str
	start_time: str  # HH:MM format
	operator: str
	location: str
	parameters: Dict[str, Any] = field(default_factory=dict)
	source_block: Optional[str] = None

