from __future__ import annotations
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional

from Utils.api_manager import APIManager

class PlanningHorizon(str, Enum):
	HOUR = "hour"
	DAY = "day"
	WEEK = "week"
	MONTH = "month"
	YEAR = "year"

@dataclass
class PlanStep:
	target_time: str
	action: str
	location: str
	parameters: Dict[str, Any] = field(default_factory=dict)

	@classmethod
	def from_dict(cls, data: Dict[str, Any]) -> 'PlanStep':
		return cls(
			target_time=data.get("target_time", "unknown"),
			action=data.get("action", "unknown"),
			location=data.get("location", "unknown"),
			parameters=data.get("parameters", {}) if isinstance(data.get("parameters", {}), dict) else {}
		)


def run_gpt_prompt_structured_planning(
	agent_summary: str,
	goal: str,
	horizon: str,
	world_context: str,
	api_key: str = None,
) -> Optional[List[Dict[str, Any]]]:
	"""
	LLM-based structured planning helper used as a fallback when the
	ATUS-based DailyPlanningOrchestrator is unavailable or when a non-daily
	planning horizon is requested.
	"""
	# Create API manager instance
	try:
		api_manager = APIManager(api_key)
	except ValueError as e:
		print(f"Failed to initialize API manager: {e}")
		return None

	header = (
		f"You are an AI planner for an agent-based simulation. Generate a structured plan at the horizon: {horizon}.\n\n"
		f"AGENT GOAL: {goal}\n\n"
		f"AGENT PROFILE: {agent_summary}...\n\n"
		f"WORLD CONTEXT: {world_context}\n\n"
		"CONSTRAINTS:\n"
		"- Return ONLY a valid JSON array of steps (no prose), where each step is an object with exactly these fields:\n"
		"  - \"target_time\": string (e.g., \"09:00 AM\" for day/hour horizons)\n"
		"  - \"action\": one of [\"Travel\", \"Exchange\", \"ReturnHome\", \"Wait\"]\n"
		"  - \"location\": short string label (e.g., \"home\", \"store\")\n"
		"  - \"parameters\": object with a small keyset depending on action\n\n"
		"ACTION PARAMETER RULES:\n"
		"- Travel: parameters = {\"to\": \"<place_id_or_label>\"}\n"
		"- Exchange: parameters = {\"counterparty\": \"893427615\", \"receive\": {\"<SKU>\": 1}} where SKU is one of [MILK_GAL, EGGS_12, BREAD_WHT]\n"
		"- ReturnHome: parameters = {}\n"
		"- Wait: parameters = {\"minutes\": 10} (optional)\n\n"
		"CRITICAL: Use exact SKU names from the list above. Do not use generic terms like 'groceries'.\n\n"
		"OUTPUT EXAMPLE (array only):\n"
	)
	# Non-f-string block containing JSON braces safely
	example = (
		"[\n"
		"  {\"target_time\": \"08:30 AM\", \"action\": \"Travel\", \"location\": \"in_transit\", \"parameters\": {\"to\": \"store\"}},\n"
		"  {\"target_time\": \"09:05 AM\", \"action\": \"Exchange\", \"location\": \"store\", \"parameters\": {\"counterparty\": \"893427615\", \"receive\": {\"MILK_GAL\": 1}}},\n"
		"  {\"target_time\": \"09:20 AM\", \"action\": \"ReturnHome\", \"location\": \"home\", \"parameters\": {}}\n"
		"]\n"
	)
	prompt = header + example

	try:
		response, _, model_name, _ = api_manager.make_request(
			prompt=prompt,
			intelligence_level=3,
			max_tokens=10000,
			temperature=0.3
		)
		if response:
			try:
				plan_data = json.loads(response)
				if isinstance(plan_data, list):
					print(f"Generated plan using {model_name}")
					return plan_data
				else:
					print(f"LLM response is not a list: {type(plan_data)}")
					return None
			except json.JSONDecodeError as e:
				print(f"Failed to parse LLM response as JSON: {e}")
				print(f"Raw response: {response}")
				return None
		return None
	except Exception as e:
		print(f"Error generating structured plan: {e}")
		return None

class StructuredPlanner:
	def __init__(self, simulation_id: str):
		self.simulation_id = simulation_id
		self.plan_manager = None
		try:
			from Agent.modules.plan_manager import PlanManager
			self.plan_manager = PlanManager(simulation_id)
		except ImportError:
			print("Warning: PlanManager not available, falling back to in-memory plans")
	
	def create_plan(
		self,
		agent: 'Agent',
		goal: str,
		horizon: PlanningHorizon,
		world_context: str,
	) -> Optional[int]:
		"""
		Create a structured plan and store it in the database.
		
		Args:
			agent: The agent creating the plan
			goal: The goal to achieve
			horizon: Planning horizon (hour, day, week, month, year)
			world_context: Context about the world for planning
			
		Returns:
			Plan ID if successful, None otherwise
		"""
		if horizon == PlanningHorizon.DAY:
			try:
				from Agent.modules.planning.orchestrator import DailyPlanningOrchestrator
				orchestrator = DailyPlanningOrchestrator(self.simulation_id)
				target_date = getattr(agent, "current_simulation_date", None)
				if not target_date:
					world = getattr(agent, "world", None)
					if world and hasattr(world, "now"):
						target_date = world.now().date()
				if not target_date:
					target_date = datetime.utcnow().date()
				plan_id, plan_steps = orchestrator.generate_daily_plan(
					agent=agent,
					target_day=target_date,
					goal=goal,
					world_context=world_context,
				)
				if plan_id:
					return plan_id
			except Exception as exc:
				print(f"ATUS-based DailyPlanningOrchestrator failed: {exc}")
				import traceback
				traceback.print_exc()
				# Fall through to legacy LLM planning as fallback

		agent_summary = agent.llm_summary or agent.get_broad_summary()
		api_key = None
		if hasattr(agent, 'action') and agent.action and hasattr(agent.action, 'api_manager'):
			api_key = agent.action.api_manager.api_key
		
		# Generate plan using legacy LLM-based structured planning
		plan_data = run_gpt_prompt_structured_planning(
			agent_summary=agent_summary,
			goal=goal,
			horizon=horizon.value,
			world_context=world_context,
			api_key=api_key
		)
		
		if not plan_data:
			return None
		
		# Convert to PlanStep objects
		plan_steps = [PlanStep.from_dict(step) for step in plan_data]
		
		# Store in database if PlanManager is available
		if self.plan_manager:
			plan_id = self.plan_manager.create_plan(
				agent_id=str(agent.agent_id),
				plan_type="daily",  # Default type, could be made configurable
				horizon=horizon,
				goal=goal,
				world_context=world_context,
				plan_steps=plan_steps
			)
			return plan_id
		else:
			# Fallback to in-memory (for backward compatibility)
			print("Warning: Using in-memory plan storage (PlanManager not available)")
			return None
	
	def get_plan(self, plan_id: int) -> Optional[List[PlanStep]]:
		"""Retrieve a plan from the database and convert to PlanStep objects."""
		if not self.plan_manager:
			return None
		
		plan_data = self.plan_manager.get_plan(plan_id)
		if not plan_data:
			return None
		
		# Convert database steps back to PlanStep objects
		plan_steps = []
		for step_data in plan_data.get("steps", []):
			plan_step = self.plan_manager.convert_db_step_to_planstep(step_data)
			plan_steps.append(plan_step)
		
		return plan_steps
