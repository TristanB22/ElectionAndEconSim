#!/usr/bin/env python3
"""
Daily planning orchestrator that ties distributions, synthesis, and guardrails together.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional, TYPE_CHECKING

from Database.managers import get_simulations_manager
from Agent.cognitive_modules.structured_planning import PlanningHorizon
from Agent.modules.plan_manager import PlanManager

from .distributions import get_distribution_provider
from .encode import operator_steps_to_plan_steps
from .guardrails import apply_guardrails
from .llm_synthesis import generate_operator_steps
from .models import ActivityBlock
from .profile import stratum_id_for_agent
from .routine import build_weekly_skeleton, sample_daily_template, _week_start

if TYPE_CHECKING:
	from Agent.cognitive_modules.structured_planning import PlanStep


class DailyPlanningOrchestrator:
	def __init__(self, simulation_id: str):
		self.simulation_id = simulation_id
		self.sim_db = get_simulations_manager()
		self.plan_manager = PlanManager(simulation_id)
		self.provider = get_distribution_provider()

	def _ensure_home_known(self, agent) -> None:
		if not hasattr(agent, "knowledge") or agent.knowledge is None:
			return
		if not agent.knowledge.knows("home", min_conf=0.2):
			agent.knowledge.add("home", kind="place", source="residence", confidence=0.9, attrs={"label": "home"})

	def _get_or_create_weekly_skeleton(self, agent, target_day: date):
		week_start = _week_start(target_day)
		existing = self.sim_db.get_agent_weekly_skeleton(self.simulation_id, str(agent.agent_id), week_start)
		if existing and existing.get("skeleton_json"):
			return existing["skeleton_json"], week_start
		skeleton = build_weekly_skeleton(agent, self.simulation_id, week_start)
		self.sim_db.upsert_agent_weekly_skeleton(
			self.simulation_id,
			str(agent.agent_id),
			week_start,
			skeleton,
			{"stratum_id": stratum_id_for_agent(agent)},
		)
		return skeleton, week_start

	def _build_daily_template(self, agent, target_day: date, skeleton):
		template_blocks = sample_daily_template(agent, self.simulation_id, target_day, skeleton)
		self.sim_db.upsert_agent_daily_template(
			self.simulation_id,
			str(agent.agent_id),
			target_day,
			[
				{
					"block_id": b.block_id,
					"operator_group": b.operator_group,
					"start_hour": b.start_hour,
					"duration_minutes": b.duration_minutes,
					"location_hint": b.location_hint,
					"anchor": b.anchor,
				}
				for b in template_blocks
			],
			{"stratum_id": stratum_id_for_agent(agent)},
		)
		return template_blocks

	def _store_plan(self, agent, goal: str, world_context: str, plan_steps: List[PlanStep]) -> Optional[int]:
		return self.plan_manager.create_plan(
			agent_id=str(agent.agent_id),
			plan_type="daily",
			horizon=PlanningHorizon.DAY,
			goal=goal,
			world_context=world_context,
			plan_steps=plan_steps,
		)

	def generate_daily_plan(
		self,
		agent,
		target_day: date,
		goal: str,
		world_context: str,
	) -> tuple[Optional[int], List[PlanStep]]:
		"""
		Generate a daily plan for an agent using ATUS-informed planning.
		
		Returns:
			Tuple of (plan_id, plan_steps) where plan_id is the database ID and 
			plan_steps is the list of PlanStep objects for immediate use.
		"""
		self._ensure_home_known(agent)
		skeleton, week_start = self._get_or_create_weekly_skeleton(agent, target_day)
		template_blocks = self._build_daily_template(agent, target_day, skeleton)
		operator_steps, llm_reasoning, llm_model = generate_operator_steps(agent, goal, world_context, template_blocks, target_day)
		# annotate synthesis metadata into step parameters for logging/frontend
		for _s in operator_steps:
			try:
				params = dict(getattr(_s, 'parameters', {}) or {})
				if 'synth' not in params:
					params['synth'] = llm_model or 'heuristic'
				if getattr(_s, 'source_block', None) is not None and 'source_block' not in params:
					params['source_block'] = _s.source_block
				_s.parameters = params
			except Exception:
				pass
		filtered_steps, issues = apply_guardrails(agent, operator_steps)
		plan_steps = operator_steps_to_plan_steps(filtered_steps)
		plan_id = self._store_plan(agent, goal, world_context, plan_steps)
		if (llm_reasoning or issues) and plan_id:
			self.sim_db.insert_plan_audit(
				plan_id=plan_id,
				audit_type="synthesis" if llm_reasoning else "coherence",
				input_hash=None,
				model_name=llm_model or "guardrails",
				issues=issues,
				edits={"llm_reasoning": llm_reasoning} if llm_reasoning else None,
			)
		return plan_id, plan_steps
