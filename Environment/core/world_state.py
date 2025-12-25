#!/usr/bin/env python3
"""
Thin world state service.

This module provides a minimal, queryable state that preconditions/estimates can
read from. Mutations should happen via reducers that consume emitted events.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List


@dataclass
class WorldState:
    # Minimal shards; extend as needed
    positions: Dict[str, str] = field(default_factory=dict)  # agent_id -> place_id
    schedules: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)  # agent_id -> tasks
    firm_states: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # firm_id -> arbitrary state

    def get_agent_position(self, agent_id: str) -> Optional[str]:
        return self.positions.get(agent_id)

    def get_agent_schedule(self, agent_id: str) -> List[Dict[str, Any]]:
        return list(self.schedules.get(agent_id, []))

    def get_firm_state(self, firm_id: str) -> Dict[str, Any]:
        if firm_id not in self.firm_states:
            self.firm_states[firm_id] = {}
        return self.firm_states[firm_id]

    def firm_exists(self, firm_id: str) -> bool:
        return firm_id in self.firm_states

    def agent_exists(self, agent_id: str) -> bool:
        return agent_id in self.positions or agent_id in self.schedules

    def place_exists(self, place_id: str) -> bool:
        # For now, any string is a valid place
        return True

    def object_exists(self, object_id: str) -> bool:
        # For now, any string is a valid object
        return True

    def set_agent_position(self, agent_id: str, place_id: str):
        self.positions[agent_id] = place_id

    def add_agent(self, agent_id: str, initial_position: str = "home"):
        """Add an agent to the world state with an initial position"""
        self.positions[agent_id] = initial_position
        # Initialize empty schedule for the agent
        self.schedules[agent_id] = []

    def add_agent_task(self, agent_id: str, task: Dict[str, Any]):
        if agent_id not in self.schedules:
            self.schedules[agent_id] = []
        self.schedules[agent_id].append(task)

    def get_firm_inventory(self, firm_id: str, sku: str) -> int:
        return self.get_firm_state(firm_id).get("inventory", {}).get(sku, 0)

    def get_firm_price(self, firm_id: str, sku: str) -> float:
        return self.get_firm_state(firm_id).get("prices", {}).get(sku, 0.0)

    def get_firm_cost(self, firm_id: str, sku: str) -> float:
        return self.get_firm_state(firm_id).get("costs", {}).get(sku, 0.0)

    def get_firm_cash(self, firm_id: str) -> float:
        return self.get_firm_state(firm_id).get("cash", 0.0)

    def get_firm_ar(self, firm_id: str) -> float:
        return self.get_firm_state(firm_id).get("ar", 0.0)

    def get_firm_ap(self, firm_id: str) -> float:
        return self.get_firm_state(firm_id).get("ap", 0.0)

    def get_firm_order(self, firm_id: str, order_id: str) -> Optional[Dict[str, Any]]:
        return self.get_firm_state(firm_id).get("orders", {}).get(order_id)

    def get_next_firm_order_id(self, firm_id: str) -> str:
        firm_state = self.get_firm_state(firm_id)
        seq = firm_state.get("seq", 1)
        firm_state["seq"] = seq + 1
        return f"O{seq}"


