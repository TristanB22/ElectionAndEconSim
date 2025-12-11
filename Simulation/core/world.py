#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from Environment.core.world_state import WorldState
from Environment.affordances import AffordanceIndex
from Agent.modules.actions.registry import ActionRegistry, register_baseline_actions
from Agent.modules.interpreter import Interpreter
from Economy.Accounting.ledger import AccountingAdapter, InMemoryLedger
from Firm.general_firm import GeneralFirm
from Agent.modules.channels import ChannelSpec, register_channel_actions

try:
	# Try to create a simple database action ledger inline
	import mysql.connector
	from datetime import datetime
	import json
	
	class SimpleDatabaseActionLedger:
		def __init__(self, simulation_id: str):
			self.simulation_id = simulation_id
			# Use the proper database connection manager that respects DATABASE_TARGET
			from Database.connection_manager import get_mysql_connection
			self.get_connection = get_mysql_connection
			self.conn = None
		
		def record(self, now: datetime, seed: Optional[int], agent_id: str, action: str, 
				   params: Dict[str, Any], events: List[Dict[str, Any]], 
				   journal: List[Dict[str, Any]], execution_time_ms: Optional[int] = None) -> None:
			"""Record an action to the consolidated events table."""
			try:
				# Get current simulation time instead of using passed parameter
				from Environment.simulation_time_manager import get_current_simulation_datetime
				simulation_time = get_current_simulation_datetime(self.simulation_id)
				
				# Use context manager for proper connection handling
				with self.get_connection() as conn:
					cursor = conn.cursor()
					cursor.execute("USE world_sim_simulations")  # Ensure we're using the right database
					cursor.execute("""
						INSERT INTO events (simulation_id, timestamp, simulation_time, 
										 agent_id, action_name, action_params, events, 
										 journal_entries, execution_time_ms, status)
						VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
					""", (
						self.simulation_id,
						simulation_time,  # Use simulation time for both timestamp and simulation_time
						simulation_time,  # Use current simulation time
						agent_id,
						action,
						json.dumps(params),
						json.dumps(events),
						json.dumps(journal),
						execution_time_ms,
						'success'
					))
					cursor.close()
					
			except Exception as e:
				# Silently log errors to avoid disrupting simulation
				pass
	
	create_action_ledger = lambda sim_id: SimpleDatabaseActionLedger(sim_id)
except Exception as e:
	create_action_ledger = None


@dataclass
class World:
	simulation_id: str
	state: WorldState
	event_bus: List[Dict[str, Any]]
	accounting: AccountingAdapter
	ledger: Any
	registry: ActionRegistry
	firms: Dict[str, GeneralFirm]

	def __init__(self, simulation_id: str) -> None:
		self.simulation_id = simulation_id
		self.state = WorldState()
		self.event_bus = []
		self.accounting = AccountingAdapter()
		# Prefer database-backed ledger when available
		if create_action_ledger is not None:
			try:
				self.ledger = create_action_ledger(simulation_id)
			except Exception as e:
				self.ledger = InMemoryLedger()
		else:
			self.ledger = InMemoryLedger()
		self.registry = ActionRegistry()
		# Baseline actions
		register_baseline_actions(self.registry)
		# register archetype channels at boot
		try:
			archetypes = [
				ChannelSpec(id="dm_local_v1", topology="dm", targeting={"radius_km": 5}, costs={"money": 0.0, "time": 1.0, "social_capital": 0.1, "compute": 0.0}, friction={"signup_steps": 1, "rate_limit_per_day": 20}, credibility_baseline=0.5, latency_s=1.0, caps={"daily_slots": 50, "group_size": 2}, diffusion={"homophily": 0.7, "tail": 0.1}),
				ChannelSpec(id="feed_city_v1", topology="feed", targeting={"city": True}, costs={"money": 0.0, "time": 2.0, "social_capital": 0.05, "compute": 0.0}, friction={"signup_steps": 1, "rate_limit_per_day": 10}, credibility_baseline=0.4, latency_s=2.0, caps={"daily_slots": 100, "group_size": 1000}, diffusion={"homophily": 0.6, "tail": 0.3}),
				ChannelSpec(id="event_hub_v1", topology="event", targeting={"local": True}, costs={"money": 0.0, "time": 5.0, "social_capital": 0.2, "compute": 0.0}, friction={"signup_steps": 2, "rate_limit_per_day": 5}, credibility_baseline=0.6, latency_s=5.0, caps={"daily_slots": 10, "group_size": 50}, diffusion={"homophily": 0.5, "tail": 0.2}),
			]
			for spec in archetypes:
				register_channel_actions(self.registry, spec)
		except Exception:
			pass
		# Build affordances now; refresh each tick
		self.affordances = AffordanceIndex(self)
		# Interpreter after registry/accounting ready
		self.interpreter = Interpreter(
			registry=self.registry,
			world=self,
			event_bus=self.event_bus,
			accounting=self.accounting,
			ledger=self.ledger,
			rng_seed=None,
		)
		# Simple locations placeholder
		self.locations: Dict[str, Dict[str, Any]] = {}
		self.firms = {}

	# Helpers to integrate firm data loaded from DB
	def ensure_firm(self, firm_id: str, prices: Dict[str, float], inventory: Dict[str, int], costs: Optional[Dict[str, float]] = None) -> None:
		fs = self.state.get_firm_state(firm_id)
		fs.setdefault("prices", {}).update(prices or {})
		fs.setdefault("inventory", {}).update(inventory or {})
		fs.setdefault("costs", {}).update(costs or {})
		fs.setdefault("cash", 0.0)
		fs.setdefault("orders", {})
		fs.setdefault("seq", 1)
		# Rebuild affordances after new firm
		self.affordances = AffordanceIndex(self)

	def add_firm_from_dnb(self, dnb_record: Dict[str, Any]) -> GeneralFirm:
		firm = GeneralFirm.from_dnb(dnb_record or {})
		self.firms[firm.firm_id] = firm
		# Initialize firm finances snapshot from current world state
		ws_firm = self.state.get_firm_state(firm.firm_id)
		firm.snapshot_opening_balances(ws_firm)
		return firm

	def now(self) -> datetime:
		try:
			from Environment.simulation_time_manager import get_current_simulation_datetime
			return get_current_simulation_datetime(self.simulation_id)
		except Exception:
			return datetime.utcnow()

	def rebuild_affordances(self) -> None:
		self.affordances = AffordanceIndex(self)


