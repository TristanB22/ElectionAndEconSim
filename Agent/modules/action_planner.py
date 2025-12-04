#!/usr/bin/env python3
"""
Action Planner Module
Provides advanced action planning functionality for agents.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import json

@dataclass
class PlanStep:
    op: str
    params: Dict[str, Any]


@dataclass
class Plan:
    steps: List[PlanStep]
    rationale: str


class ActionPlanner:
    """
    Advanced action planner for agents with sophisticated planning capabilities.
    """
    
    def __init__(self, agent):
        """
        Initialize the action planner module.
        
        Args:
            agent: The agent instance this planner belongs to
        """
        self.agent = agent
        self.planning_history = []
        
    def create_plan(self, goal: str, context: Dict[str, Any] = None) -> Optional[Plan]:
        try:
            ctx = context or {}
            caps = ctx.get("capabilities", {})
            allowed_ops = ["Travel", "Exchange", "Consume", "Work", "Transfer", "Communicate"]
            prompt = f"""
You can ONLY use these operators: {allowed_ops}.
World notes: {ctx.get('world_notes','one firm, travel has zero cost')}.
Goal: {goal}
Return STRICT JSON: {{"rationale": "...", "steps": [{{"op":"...", "params":{{...}}}}, ...]}}
Use targets that exist in capabilities keys: {list(caps.keys())}
"""
            response, *_ = self.agent.action.api_manager.make_request(
                prompt=prompt, intelligence_level=2, max_tokens=300, temperature=0.2
            )
            try:
                data = json.loads(response)
            except Exception:
                data = {"rationale": "fallback", "steps": []}
            sketch = [PlanStep(op=s.get("op",""), params=s.get("params",{})) for s in data.get("steps", [])]
            plan = Plan(steps=sketch, rationale=data.get("rationale", ""))
            # Deterministic binding and dry-run validation
            bound: List[PlanStep] = []
            interp = self.agent.environment.interpreter if hasattr(self.agent, 'environment') else None
            for step in plan.steps:
                if step.op == "Travel" and step.params.get("to") in ("nearest_store", "store"):
                    if caps.get("Travel"):
                        step.params["to"] = caps["Travel"][0].target_id
                if step.op == "Exchange":
                    cp = step.params.get("counterparty")
                    if cp in (None, "nearest_store", "store") and caps.get("Exchange"):
                        step.params["counterparty"] = caps["Exchange"][0].target_id
                if interp:
                    dr = interp.dry_run(str(self.agent.agent_id), step.op, step.params, firm_id=step.params.get("counterparty"))
                    if not dr.ok:
                        continue
                bound.append(step)
            final_plan = Plan(steps=bound, rationale=plan.rationale)
            self.planning_history.append({"goal": goal, "rationale": final_plan.rationale, "steps": [s.__dict__ for s in final_plan.steps]})
            return final_plan
        except Exception as e:
            print(f"Error creating action plan: {e}")
            return None
    
    def get_planning_history(self) -> List[Dict[str, Any]]:
        """Get the planning history."""
        return self.planning_history.copy()
    
    def clear_planning_history(self):
        """Clear the planning history."""
        self.planning_history.clear()
