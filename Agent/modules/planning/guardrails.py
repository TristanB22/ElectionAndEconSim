#!/usr/bin/env python3
"""
Simple guardrails for generated operator steps.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .models import OperatorStep


def ensure_knowledge(agent, steps: List[OperatorStep]) -> Tuple[List[OperatorStep], List[str]]:
	if not hasattr(agent, "knowledge") or agent.knowledge is None:
		return steps, []
	issues: List[str] = []
	filtered: List[OperatorStep] = []
	for step in steps:
		if step.operator == "Travel":
			dest = step.parameters.get("to")
			if dest and not agent.knowledge.knows(dest, min_conf=0.3) and dest != "home":
				issues.append(f"unknown_place:{dest}")
				continue
		if step.operator == "Exchange":
			counterparty = step.parameters.get("counterparty")
			if counterparty and not agent.knowledge.knows(counterparty, min_conf=0.3):
				issues.append(f"unknown_firm:{counterparty}")
				continue
		filtered.append(step)
	return filtered, issues


def order_by_time(steps: List[OperatorStep]) -> List[OperatorStep]:
	return sorted(steps, key=lambda s: s.start_time)


def apply_guardrails(agent, steps: List[OperatorStep]) -> Tuple[List[OperatorStep], List[str]]:
	stable_steps = order_by_time(steps)
	stable_steps, knowledge_issues = ensure_knowledge(agent, stable_steps)
	return stable_steps, knowledge_issues
