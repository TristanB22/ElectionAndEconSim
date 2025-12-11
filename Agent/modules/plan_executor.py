from __future__ import annotations
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import json
import logging

from Agent.cognitive_modules.structured_planning import PlanStep
from Environment.reducers import reduce_event
from Agent.modules.spatial_planner import SpatialPlanner

# Import GDP measurement components
try:
    from Economy.gdp_measurement import EventIngestor, EconomicEvent, EventType
    GDP_AVAILABLE = True
except ImportError:
    GDP_AVAILABLE = False
    EventIngestor = None
    EconomicEvent = None
    EventType = None

logger = logging.getLogger(__name__)

class PlanExecutor:
	def __init__(self, world) -> None:
		self.world = world
		# Initialize financial transaction processors for each firm
		self.financial_processors: Dict[str, Any] = {}
		self.spatial_planner = SpatialPlanner(world.simulation_id)
		# Add GDP measurement system
		if GDP_AVAILABLE:
			self.event_ingestor = EventIngestor(world.simulation_id)
			self.gdp_enabled = True
		else:
			logger.warning("GDP measurement system not available")
			self.event_ingestor = None
			self.gdp_enabled = False
		# Track simulation day offset for action context
		self._simulation_start_date = None
		self._last_route_id = None

	def _get_financial_processor(self, firm_id: str):
		"""Get or create a financial transaction processor for a firm."""
		if firm_id not in self.financial_processors:
			try:
				from Firm.financial_transaction_processor import FinancialTransactionProcessor
				self.financial_processors[firm_id] = FinancialTransactionProcessor(firm_id)
				logger.info(f"Created financial processor for firm {firm_id}")
			except ImportError as e:
				logger.warning(f"Financial processor not available: {e}")
				return None
		return self.financial_processors.get(firm_id)

	def _normalize_params(self, step: PlanStep, default_firm_id: Optional[str]) -> (str, Dict[str, Any], Optional[str]):
		"""
		Return (action_name, params, firm_id_for_context)
		"""
		action = (step.action or "").strip()
		params: Dict[str, Any] = dict(step.parameters or {})
		firm_id: Optional[str] = None

		if action == "ReturnHome":
			action = "Travel"
			params = {"to": "home"}

		if action == "Travel":
			# Ensure destination exists
			if not params.get("to"):
				# Fallback to step.location label if provided
				loc = step.location
				if isinstance(loc, str) and loc.lower().startswith("store"):
					params["to"] = "store"
				else:
					params["to"] = loc if isinstance(loc, str) and loc else "home"

		if action == "Exchange":
			# Prefer explicit firm id when provided by caller
			if default_firm_id:
				params["counterparty"] = default_firm_id
			firm_id = params.get("counterparty")
			# Normalize receive to dict of sku->qty
			rec = params.get("receive")
			if isinstance(rec, list):
				# Convert list of {sku, qty} to dict
				recv: Dict[str, int] = {}
				for it in rec:
					sku = it.get("sku")
					qty = int(it.get("qty", 0))
					if sku and qty:
						recv[sku] = recv.get(sku, 0) + qty
				params["receive"] = recv

		return action, params, firm_id

	def execute(
		self,
		agent,
		steps: List[PlanStep],
		default_firm_id: Optional[str] = None
	) -> Dict[str, Any]:
		"""
		Execute a sequence of plan steps for the given agent.

		Args:
			agent: The agent executing the plan.
			steps: List of PlanStep objects to execute.
			default_firm_id: Optional firm id to use as context for certain actions.

		Returns:
			Dictionary with execution results, including executed and failed steps, and timing info.
		"""

		# Record the overall start time for the execution
		start_time = datetime.now()

		# Prepare results dictionary to track executed and failed steps, and timing info
		results: Dict[str, Any] = {
			"executed": [],
			"failed": []
		}

		# Get the current simulation time from the world
		now: datetime = self.world.now()

		# Initialize daily budgets (placeholder for now, should come from day manager)
		# These should be refreshed by the day_simulation_manager at each tick
		agent.attention_budget_minutes = getattr(agent, 'attention_budget_minutes', 60 * 8) # 8 hours default
		agent.time_budget_minutes = getattr(agent, 'time_budget_minutes', 60 * 16) # 16 hours active time

		# Iterate through each step in the plan
		for idx, step in enumerate(steps):

			# Record the start time for this step
			step_start_time = datetime.now()

			# Normalize the action name, parameters, and firm context for this step
			action_name, params, firm_id = self._normalize_params(step, default_firm_id)

			if action_name == "Travel":
				try:
					params = self.spatial_planner.prepare_travel(agent, params, step.location, self.world, now)
				except Exception as exc:
					results["failed"].append({
						"index": idx,
						"action": action_name,
						"params": params,
						"error": f"spatial_planner_error: {exc}",
						"execution_time_ms": 0,
					})
					continue
			
			# Store route if Travel action has route info
			route_id = None
			if action_name == "Travel":
				route_id = self._store_travel_route(agent, params, now)

			# Handle "Wait" actions as no-ops that just consume simulated time
			if action_name == "Wait":
				step_execution_time = int((datetime.now() - step_start_time).total_seconds() * 1000)
				results["executed"].append({
					"index": idx,
					"action": action_name,
					"params": params,
					"events": [],
					"execution_time_ms": step_execution_time
				})
				continue  # Move to the next step

			# Check attention/time budgets before executing
			action_estimate = self.world.interpreter.dry_run(str(agent.agent_id), action_name, params, firm_id=firm_id).estimate
			if action_estimate:
				time_cost = action_estimate.get("time_minutes", 0.0)
				if agent.attention_budget_minutes < time_cost:
					results["failed"].append({
						"index": idx,
						"action": action_name,
						"params": params,
						"error": f"Insufficient attention budget ({agent.attention_budget_minutes:.1f} < {time_cost:.1f} min)",
						"execution_time_ms": 0
					})
					continue
				if agent.time_budget_minutes < time_cost:
					results["failed"].append({
						"index": idx,
						"action": action_name,
						"params": params,
						"error": f"Insufficient time budget ({agent.time_budget_minutes:.1f} < {time_cost:.1f} min)",
						"execution_time_ms": 0
					})
					continue
				
				# Deduct from budgets
				agent.attention_budget_minutes -= time_cost
				agent.time_budget_minutes -= time_cost

			# knowledge gate: prevent actions involving unknown entities
			if hasattr(agent, 'knowledge'):
				# for travel, ensure place is known; for exchange, ensure firm known; for channel ops, ensure channel known
				if action_name == "Travel" and params.get("to") and not agent.knowledge.knows(params.get("to"), min_conf=0.3):
					results["failed"].append({
						"index": idx,
						"action": action_name,
						"params": params,
						"error": "knowledge_gate_unknown_place",
						"execution_time_ms": 0
					})
					continue
				if action_name == "Exchange" and params.get("counterparty") and not agent.knowledge.knows(params.get("counterparty"), min_conf=0.3):
					results["failed"].append({
						"index": idx,
						"action": action_name,
						"params": params,
						"error": "knowledge_gate_unknown_firm",
						"execution_time_ms": 0
					})
					continue

			# Commit the action to the world interpreter
			res = self.world.interpreter.commit(
				agent_id=str(agent.agent_id),
				action_name=action_name,
				params=params,
				now=now,
				firm_id=firm_id,
			)

			# If the action was successful
			if res.get("ok"):

				# Apply reducers for any events emitted by the action
				for evt in res.get("events", []) or []:
					reduce_event(self.world, evt)

					# channel usage logging and holdout tally
					if evt.get("event_type", "").startswith("channel_"):
						try:
							from Database.managers import get_simulations_manager
							db = get_simulations_manager()
							meta = evt.get("metadata", {})
							payload = {
								"simulation_id": self.world.simulation_id,
								"channel_id": meta.get("channel_id"),
								"agent_id": str(agent.agent_id),
								"action_type": evt.get("event_type").replace("channel_", ""),
								"target_id": evt.get("target"),
								"content": evt.get("content"),
								"metadata": meta,
							}
							# store via action ledger to ensure persistence
							db.log_action(
								self.world.simulation_id,
								str(agent.agent_id),
								f"channel_{payload['action_type']}",
								payload,
								[],
								[],
								0,
								"success",
							)
							if meta.get("holdout"):
								agent.holdouts_today = getattr(agent, 'holdouts_today', 0) + 1
						except Exception:
							pass


				# Discovery: Add to agent's knowledge base
				if action_name == "Exchange" and firm_id:
					agent.knowledge.add(firm_id, "firm", "purchase", 0.8)
					# Also add items/capabilities of the firm
					fs = self.world.state.get_firm_state(firm_id)
					for sku in fs.get("prices", {}).keys():
						agent.knowledge.add(sku, "product", "purchase", 0.7, parent_entity_id=firm_id)
					agent.knowledge.add(f"{firm_id}_retail_grocery", "role", "purchase", 0.9, parent_entity_id=firm_id)
				elif action_name == "Travel" and params.get("to"):
					agent.knowledge.add(params["to"], "place", "visit", 0.6)
					try:
						self.spatial_planner.on_travel_success(agent, params, now)
					except Exception:
						pass
				elif action_name == "message" and params.get("target_id"):
					agent.knowledge.add(params["target_id"], "person", "social", 0.5)
				
				# Opinion updates based on experience quality (placeholder for now)
				# Example: if action result indicates a bad experience (e.g., stockout, long queue)
				if res.get("events") and hasattr(agent, 'opinions') and agent.opinions:
					for evt in res["events"]:
						if evt.get("event_type") == "retail_order_placed" and evt.get("metadata", {}).get("stockout"):
							if firm_id:
								agent.opinions.update_place_opinion(firm_id, -0.2, "stockout") # Decrease satisfaction
						# Add more conditions for good/bad experiences
						elif evt.get("event_type") == "retail_payment_received" and evt.get("metadata", {}).get("smooth_checkout"):
							if firm_id:
								agent.opinions.update_place_opinion(firm_id, 0.1, "smooth_checkout") # Increase satisfaction

				# Special handling for "Exchange" actions (e.g., retail transactions)
				if action_name == "Exchange":
					# Determine the counterparty (firm) for the transaction
					cp = params.get("counterparty") or default_firm_id
					if cp:
						# Gather details about the items being received in the exchange
						receive_items = params.get("receive", {})
						total_amount = 0.0

						# Get the current firm state for the counterparty
						fs = self.world.state.get_firm_state(cp)
						prices = fs.get("prices", {})
						costs = fs.get("costs", {})

						# Calculate the total value of the transaction based on item prices and quantities
						for sku, qty in receive_items.items():
							unit_price = float(prices.get(sku, 0.0))
							total_amount += unit_price * int(qty)

						# Enhanced transaction logging with financial processing
						transaction_data = {
							"simulation_id": self.world.simulation_id,
							"transaction_type": "retail_sale",
							"from_entity": str(agent.agent_id),
							"to_entity": cp,
							"amount": total_amount,
							"currency": "USD",
							"item_type": "groceries",
							"item_quantity": sum(receive_items.values()),
							"metadata": {
								"items": receive_items,
								"prices": {sku: prices.get(sku, 0.0) for sku in receive_items.keys()},
								"costs": {sku: costs.get(sku, 0.0) for sku in receive_items.keys()},
								"action": "Exchange",
								"agent_id": str(agent.agent_id)
							}
						}

						# Log the transaction to the database for later reconstruction
						self._log_firm_transaction(transaction_data)

						# knowledge: note firm capability from purchased items
						try:
							if hasattr(agent, 'knowledge') and agent.knowledge and cp:
								for sku in receive_items.keys():
									agent.knowledge.note_capability(str(cp), sku, source="purchase", confidence=0.8)
						except Exception:
							pass

						# Process through enhanced financial system if available
						financial_processor = self._get_financial_processor(cp)
						if financial_processor:
							try:
								success, errors, journal_entries = financial_processor.process_retail_sale(transaction_data)
								if success:
									logger.info(f"Successfully processed financial transaction for firm {cp}")
									# Store journal entries in the world state for later access
									if 'journal_entries' not in fs:
										fs['journal_entries'] = []
									fs['journal_entries'].extend([entry.to_dict() for entry in journal_entries])
								else:
									logger.warning(f"Financial transaction processing failed for firm {cp}: {errors}")
							except Exception as e:
								logger.error(f"Error in financial transaction processing: {e}")

						# Update the world state for the firm: decrement inventory, increment cash
						inv = fs.setdefault("inventory", {})
						for sku, qty in receive_items.items():
							inv[sku] = max(0, int(inv.get(sku, 0)) - int(qty))
						fs["cash"] = float(fs.get("cash", 0.0)) + total_amount
						
						# Sync world state changes back to the financial system
						if financial_processor:
							try:
								# Update cash balance in financial system
								financial_processor.enhanced_finances.current_balances['1000'] = fs["cash"]
								
								# Update inventory balance in financial system
								total_inventory_value = 0.0
								for sku, qty in inv.items():
									unit_cost = float(costs.get(sku, 0))
									total_inventory_value += unit_cost * qty
								financial_processor.enhanced_finances.current_balances['1200'] = total_inventory_value
								
								logger.info(f"Synced world state changes to financial system for firm {cp}")
							except Exception as e:
								logger.error(f"Error syncing world state to financial system: {e}")

				# Record the execution time for this step
				step_execution_time = int((datetime.now() - step_start_time).total_seconds() * 1000)

				# Update agent telemetry
				agent.actions_executed_today = getattr(agent, 'actions_executed_today', 0) + 1
				if action_name == "Exchange":
					agent.conversions_today = getattr(agent, 'conversions_today', 0) + 1

				# Add this step to the list of executed steps
				results["executed"].append({
					"index": idx,
					"action": action_name,
					"params": params,
					"events": res.get("events", []),
					"execution_time_ms": step_execution_time
				})

			else:
				# If the action failed, record the failure and error message
				step_execution_time = int((datetime.now() - step_start_time).total_seconds() * 1000)
				results["failed"].append({
					"index": idx,
					"action": action_name,
					"params": params,
					"error": res.get("error"),
					"execution_time_ms": step_execution_time
				})
				
			# Track holdouts (failed actions due to budget constraints)
			err_val = res.get("error", "")
			# res["error"] may be a list; normalize to string for checks
			if isinstance(err_val, list):
				err_text = " ".join(map(str, err_val))
			else:
				err_text = str(err_val)
			if "budget" in err_text.lower():
				agent.holdouts_today = getattr(agent, 'holdouts_today', 0) + 1

			# If action failed, potentially update opinions negatively
			if firm_id and "precondition_failed" in res.get("error", "") and hasattr(agent, 'opinions') and agent.opinions:
				agent.opinions.update_place_opinion(firm_id, -0.1, "action_failed_precondition")

		# After all steps, record the total execution time for the plan
		total_execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
		results["total_execution_time_ms"] = total_execution_time

		# Return the results dictionary with all execution details
		return results

	def _log_firm_transaction(self, transaction_data: Dict[str, Any]) -> None:
		"""Log firm state changes as transactions for reconstruction."""
		try:
			# Create and ingest economic event for GDP measurement (writes to transactions)
			if self.gdp_enabled and self.event_ingestor:
				economic_event = self._create_economic_event(transaction_data)
				if economic_event:
					self.event_ingestor.ingest_event(economic_event)
					logger.info(f"GDP economic event ingested: {economic_event.event_type.value} - ${economic_event.total_amount}")
					
		except Exception as e:
			# Log error but don't fail the simulation
			logger.error(f"Could not log transaction: {e}")
	
	def _create_economic_event(self, transaction_data: Dict[str, Any]) -> Optional[Any]:
		"""
		Construct an EconomicEvent object from a transaction record for economic analysis and GDP tracking.

		This function takes a transaction dictionary (such as a retail sale, exchange, or other economic action)
		and translates it into a structured EconomicEvent object. The EconomicEvent is a canonical representation
		of an economic activity in the simulation, capturing all relevant details such as the type of event,
		entities involved, sector, quantities, prices, and additional metadata. 

		The purpose of this function is to enable downstream systems (such as GDP measurement, economic reporting,
		and transaction reconstruction) to work with a consistent, information-rich event format. This is essential
		for accurate economic analysis, auditing, and simulation replay.

		Args:
			transaction_data (Dict[str, Any]): 
				A dictionary containing all relevant information about the transaction, 
				including agent/firm IDs, item details, amounts, and metadata.

		Returns:
			Optional[Any]: 
				An EconomicEvent object if GDP tracking is enabled and the event can be constructed, 
				or None if GDP tracking is disabled or an error occurs.
		"""
		# If GDP tracking is not enabled or available, do not create an event
		if not GDP_AVAILABLE:
			return None
			
		try:
			# Classify the transaction to determine its economic type (e.g., final/intermediate consumption)
			# This determines how the event will be treated in GDP and economic statistics.
			event_type, buyer_type, use_type = self._classify_transaction(transaction_data)
			
			# Extract additional metadata from the transaction, such as item details and costs
			metadata = transaction_data.get('metadata', {})
			items = metadata.get('items', {})
			
			# Construct the EconomicEvent object with all required fields.
			# Many fields are derived from the transaction_data, while some (sector/subsector) are currently hardcoded.
			event = EconomicEvent(
				simulation_id=transaction_data["simulation_id"],
				event_type=event_type,
				source_timestamp=self.world.now(),  # Use simulation time instead of real time
				from_entity=transaction_data["from_entity"],  # The entity initiating the transaction
				to_entity=transaction_data["to_entity"],      # The entity receiving the transaction
				# Only assign firm_id if the to_entity is a digit (i.e., a firm, not an agent)
				firm_id=transaction_data["to_entity"] if transaction_data["to_entity"].isdigit() else None,
				buyer_type=buyer_type,    # "household" or "firm", for GDP classification
				use_type=use_type,        # "final" or "intermediate", for GDP classification
				# Sector and subsector are currently hardcoded for retail grocery, but could be dynamic in the future
				sector="retail_trade",  # TODO: Make dynamic based on firm data
				subsector="food_beverage_stores",  # TODO: Make dynamic based on firm data
				quantity=transaction_data["item_quantity"],  # Total quantity of items in the transaction
				# Calculate unit price, avoid division by zero
				unit_price=float(transaction_data["amount"]) / float(transaction_data["item_quantity"]) if transaction_data["item_quantity"] > 0 else 0,
				total_amount=transaction_data["amount"],     # Total transaction value
				currency=transaction_data["currency"],       # Currency code (e.g., "USD")
				# Use the first SKU in the items dict, if available
				sku=list(items.keys())[0] if items else None,
				# Get the unit cost for the first SKU, default to 0 if not found, ensure it's a proper decimal
				unit_cost=round(float(metadata.get('costs', {}).get(list(items.keys())[0] if items else None, 0)), 2),
				metadata=metadata,  # Attach all additional metadata for auditing and reconstruction
				# Generate a unique idempotency key for this event to prevent duplicates
				idempotency_key=f"{transaction_data['from_entity']}_{transaction_data['to_entity']}_{transaction_data['amount']}_{self.world.now().isoformat()}"
			)
			
			# Return the constructed EconomicEvent object for ingestion/logging
			return event
			
		except Exception as e:
			# Log any errors encountered during event creation and return None
			logger.error(f"Failed to create economic event: {e}")
			return None
	
	def _classify_transaction(self, transaction_data: Dict[str, Any]) -> Tuple[Any, str, str]:
		"""
		Classify a transaction for GDP accounting and economic event logging.

		This function determines the economic classification of a transaction, which is essential for
		accurate GDP measurement and economic statistics within the simulation. The classification
		includes:
		  - The event type (e.g., final consumption, intermediate consumption)
		  - The buyer type (e.g., "household" or "firm")
		  - The use type (e.g., "final" or "intermediate")

		Args:
			transaction_data: Dictionary containing transaction details, including type and participants.

		Returns:
			A tuple of (event_type, buyer_type, use_type), where:
			  - event_type: An EventType enum value (e.g., FINAL_CONSUMPTION, INTERMEDIATE_CONSUMPTION)
			  - buyer_type: "household" or "firm"
			  - use_type: "final" or "intermediate"
			If GDP tracking is not available, returns (None, "household", "final") as a default.

		Notes:
			- The logic can be extended to handle more transaction types as needed.
			- This function is a key part of the event creation pipeline for economic measurement.
		"""
		# If GDP tracking is not enabled, return a default classification
		if not GDP_AVAILABLE:
			return None, "household", "final"
		
		# Extract the transaction type (e.g., "retail_sale")
		tx_type = transaction_data["transaction_type"]
		
		if tx_type == "retail_sale":
			# For retail sales, determine if the buyer is a household (agent) or a business (firm)
			from_entity = transaction_data["from_entity"]
			
			if from_entity.startswith("agent_"):
				# If the buyer is an agent, this is considered final consumption by a household
				return EventType.FINAL_CONSUMPTION, "household", "final"
			else:
				# If the buyer is not an agent (assumed to be a firm), this is intermediate consumption
				return EventType.INTERMEDIATE_CONSUMPTION, "firm", "intermediate"
		
		# Default classification for unhandled transaction types: treat as final household consumption
		# This can be expanded with more logic for other transaction types as needed
		return EventType.FINAL_CONSUMPTION, "household", "final"

	def initialize_firm_finances(self, firm_id: str, initial_cash: float, 
							   initial_inventory: Dict[str, int], initial_costs: Dict[str, float]) -> bool:
		"""
		Initialize the financial system and records for a firm at the start of a simulation or scenario.

		This function sets up the initial financial state for a firm, including its cash balance,
		inventory levels, and unit costs for each SKU. This is a critical step to ensure that the
		firm's financial processor has all necessary data to track transactions, generate statements,
		and participate in the simulated economy.

		Args:
			firm_id: The unique identifier for the firm to initialize.
			initial_cash: The starting cash balance for the firm.
			initial_inventory: A dictionary mapping SKU to initial inventory quantity.
			initial_costs: A dictionary mapping SKU to unit cost.

		Returns:
			True if initialization was successful, False otherwise.

		Notes:
			- If the financial processor for the firm is not available, logs a warning and returns False.
			- Any exceptions during initialization are logged and result in a False return value.
		"""
		try:
			# Retrieve the financial processor object for the given firm
			financial_processor = self._get_financial_processor(firm_id)
			if financial_processor:
				# Initialize the firm's finances with the provided starting values
				financial_processor.initialize_firm_finances(
					initial_cash=initial_cash,
					initial_inventory=initial_inventory,
					initial_costs=initial_costs
				)
				logger.info(f"Successfully initialized finances for firm {firm_id}")
				return True
			else:
				logger.warning(f"Financial processor not available for firm {firm_id}")
				return False
		except Exception as e:
			logger.error(f"Error initializing finances for firm {firm_id}: {e}")
			return False

	def get_firm_financial_statements(self, firm_id: str) -> Optional[Dict[str, Any]]:
		"""
		Retrieve the current financial statements for a given firm.

		This function queries the firm's financial processor to obtain up-to-date financial statements,
		which may include the balance sheet, income statement, and other relevant financial data.
		This is useful for reporting, auditing, and analysis within the simulation.

		Args:
			firm_id: The unique identifier for the firm whose statements are requested.

		Returns:
			A dictionary containing the firm's financial statements, or None if unavailable.

		Notes:
			- If the financial processor is not available, returns None.
			- Any exceptions during retrieval are logged and result in a None return value.
		"""
		try:
			# Retrieve the financial processor object for the given firm
			financial_processor = self._get_financial_processor(firm_id)
			if financial_processor:
				# Return the firm's current financial statements
				return financial_processor.get_financial_statements()
			return None
		except Exception as e:
			logger.error(f"Error getting financial statements for firm {firm_id}: {e}")
			return None
			
	def calculate_simulation_gdp(self, start_time: datetime, end_time: datetime) -> Optional[Dict[str, Any]]:
		"""
		Calculate the Gross Domestic Product (GDP) for the entire simulation period.

		This function aggregates all relevant economic activity within the simulation between the specified
		start and end times, using the GDP measurement system. It leverages the GDPAssembler to process
		transactions and events, and computes GDP using the expenditure approach (and potentially others).
		The result provides a quantitative measure of the simulated economy's output, which is useful for
		evaluating macroeconomic performance, comparing scenarios, and supporting research or policy analysis.

		Args:
			start_time: The datetime marking the beginning of the simulation period to analyze.
			end_time: The datetime marking the end of the simulation period to analyze.

		Returns:
			A dictionary containing GDP calculation results (e.g., expenditure GDP and its components),
			or None if the GDP measurement system is not enabled or an error occurs.

		Notes:
			- If the GDP measurement system is not enabled, a warning is logged and None is returned.
			- Any exceptions during calculation are logged and result in a None return value.
			- The calculation granularity is set to 'day' (can be adjusted as needed).
		"""
		try:
			# Check if GDP measurement is enabled for this simulation
			if not self.gdp_enabled:
				logger.warning("GDP measurement system not available")
				return None

			# Import the GDPAssembler class responsible for GDP calculations
			from Economy.gdp_measurement import GDPAssembler

			# Instantiate the GDPAssembler with the current simulation ID
			gdp_assembler = GDPAssembler(self.world.simulation_id)

			# Perform the GDP calculation for the specified period and granularity ('day')
			gdp_result = gdp_assembler.calculate_period_gdp(
				start_time, end_time, 'day'
			)

			# Log the total expenditure GDP for transparency and debugging
			logger.info(f"GDP calculation completed: ${gdp_result['expenditure_gdp']['total']:.2f}")

			# Return the full GDP calculation result dictionary
			return gdp_result

		except Exception as e:
			# Log any errors encountered during GDP calculation
			logger.error(f"Error calculating simulation GDP: {e}")
			return None
	
	def _store_travel_route(self, agent, params: Dict[str, Any], now: datetime) -> Optional[int]:
		"""
		Store route information for Travel actions in the database.
		
		Args:
			agent: Agent performing the travel
			params: Travel action parameters with route info
			now: Current simulation time
		
		Returns:
			route_id if successful, None otherwise
		"""
		try:
			route = params.get('route')
			place_handle = params.get('place_handle')
			
			if not route or not place_handle:
				return None
			
			from Database.managers import get_simulations_manager
			from Utils.route_interpolation import decode_polyline
			
			db = get_simulations_manager()
			
			# Get origin coordinates (current location or home)
			origin_lat, origin_lon = agent.get_coords() if hasattr(agent, 'get_coords') else (None, None)
			if origin_lat is None:
				# Try to get home location
				home_loc = db.get_agent_home_location(self.world.simulation_id, str(agent.agent_id))
				if home_loc:
					origin_lat, origin_lon = home_loc
				else:
					return None
			
			# Destination from place_handle
			destination_lat = place_handle.get('lat')
			destination_lon = place_handle.get('lon')
			if not destination_lat or not destination_lon:
				return None
			
			# Route details
			mode = route.get('mode', 'pedestrian')
			distance_km = route.get('distance_km', 0.0)
			duration_minutes = route.get('duration_minutes', 0.0)
			provider = route.get('provider', 'valhalla')
			
			# Calculate route times
			route_start_time = now
			route_end_time = now + timedelta(minutes=duration_minutes)
			
			# Get route geometry
			route_polyline = route.get('polyline')
			route_coordinates = route.get('coordinates')
			
			# If only polyline is available, decode it
			if not route_coordinates and route_polyline:
				route_coordinates = decode_polyline(route_polyline)
			
			# Get place IDs
			origin_place_id = params.get('from') or 'current_location'
			destination_place_id = place_handle.get('id')
			
			# Store planner metadata
			planner_metadata = params.get('planner_metadata', {})
			
			# Insert route
			route_id = db.insert_agent_route(
				simulation_id=self.world.simulation_id,
				agent_id=str(agent.agent_id),
				route_start_time=route_start_time,
				route_end_time=route_end_time,
				origin_lat=origin_lat,
				origin_lon=origin_lon,
				destination_lat=destination_lat,
				destination_lon=destination_lon,
				mode=mode,
				distance_km=distance_km,
				duration_minutes=duration_minutes,
				provider=provider,
				origin_place_id=origin_place_id,
				destination_place_id=destination_place_id,
				route_polyline=route_polyline,
				route_coordinates=route_coordinates,
				planner_metadata=planner_metadata
			)
			
			if route_id:
				self._last_route_id = route_id
				logger.debug(f"Stored route {route_id} for agent {agent.agent_id}: {origin_place_id} -> {destination_place_id}")
			
			return route_id
			
		except Exception as e:
			logger.warning(f"Failed to store travel route: {e}")
			return None
