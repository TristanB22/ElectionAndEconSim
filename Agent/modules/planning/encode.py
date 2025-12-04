#!/usr/bin/env python3
"""
Conversion helpers for OperatorStep -> PlanStep.
"""

from __future__ import annotations

from typing import List

from typing import List, TYPE_CHECKING

from .models import OperatorStep

if TYPE_CHECKING:
	from Agent.cognitive_modules.structured_planning import PlanStep


def operator_steps_to_plan_steps(operator_steps: List[OperatorStep]) -> List[PlanStep]:
	from Agent.cognitive_modules.structured_planning import PlanStep
	plan_steps: List[PlanStep] = []
	for step in operator_steps:
		params = dict(step.parameters or {})
		# ensure source_block is persisted in parameters for logging/traceability
		if getattr(step, "source_block", None) is not None and "source_block" not in params:
			params["source_block"] = step.source_block
		plan_steps.append(PlanStep(
			target_time=step.start_time,
			action=step.operator,
			location=step.location,
			parameters=params,
		))
	return plan_steps
