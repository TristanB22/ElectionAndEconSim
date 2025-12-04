#!/usr/bin/env python3
"""
Plan Manager for World_Sim

This module handles the creation, storage, and retrieval of agent plans
using the database tables instead of storing plans in memory.
"""

from __future__ import annotations
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

from Agent.cognitive_modules.structured_planning import PlanStep, PlanningHorizon
from Database.managers import get_simulations_manager


class PlanStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class PlanManager:
    """Manages agent plans using database storage instead of memory."""
    
    def __init__(self, simulation_id: str):
        self.simulation_id = simulation_id
    
    def create_plan(
        self,
        agent_id: str,
        plan_type: str,
        horizon: PlanningHorizon,
        goal: str,
        world_context: str,
        plan_steps: List[PlanStep]
    ) -> Optional[int]:
        """
        Create a new plan and store it in the database.
        
        Args:
            agent_id: ID of the agent creating the plan
            plan_type: Type of plan (e.g., "daily", "shopping", "work")
            horizon: Planning horizon (hour, day, week, month, year)
            goal: The goal this plan aims to achieve
            world_context: Context about the world for this plan
            plan_steps: List of PlanStep objects
            
        Returns:
            Plan ID if successful, None otherwise
        """
        try:
            db = get_simulations_manager()
            
            # Insert plan record
            plan_result = db.execute_query("""
                INSERT INTO plans (
                    simulation_id, agent_id, plan_type, horizon, goal, world_context,
                    status, total_steps, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                self.simulation_id, agent_id, plan_type, horizon.value, goal, world_context,
                PlanStatus.DRAFT.value, len(plan_steps), datetime.now()
            ), fetch=False)
            
            # Get the plan ID - use a more reliable method
            plan_id_result = db.execute_query("""
                SELECT id FROM plans 
                WHERE simulation_id = %s AND agent_id = %s AND goal = %s 
                ORDER BY created_at DESC LIMIT 1
            """, (self.simulation_id, agent_id, goal), fetch=True)
            
            if not plan_id_result or not plan_id_result.success or not plan_id_result.data:
                print(f"Warning: Could not retrieve plan ID after creation")
                return None
            
            plan_id = plan_id_result.data[0]["id"]
            
            # Insert plan steps
            for i, step in enumerate(plan_steps):
                self._insert_plan_step(plan_id, i + 1, step, agent_id)
            
            # Update plan status to active
            db.execute_query("""
                UPDATE plans SET status = %s WHERE id = %s
            """, (PlanStatus.ACTIVE.value, plan_id), fetch=False)
            
            return plan_id
            
        except Exception as e:
            print(f"Error creating plan: {e}")
            return None
    
    def _insert_plan_step(self, plan_id: int, step_order: int, step: PlanStep, agent_id: str) -> bool:
        """Insert a single plan step into the database."""
        try:
            db = get_simulations_manager()
            
            # Parse step parameters based on action type
            travel_dest = None
            exchange_counterparty = None
            exchange_sku = None
            exchange_quantity = None
            wait_minutes = None
            param_key_1 = None
            param_value_1 = None
            param_key_2 = None
            param_value_2 = None
            
            if step.action == "Travel":
                travel_dest = step.parameters.get("to")
            elif step.action == "Exchange":
                exchange_counterparty = step.parameters.get("counterparty")
                receive = step.parameters.get("receive", {})
                if receive:
                    for sku, qty in receive.items():
                        exchange_sku = sku
                        exchange_quantity = qty
                        break
            elif step.action == "Wait":
                wait_minutes = step.parameters.get("minutes")
            
            # Store any additional parameters in generic fields
            remaining_params = {k: v for k, v in step.parameters.items() 
                              if k not in ["to", "counterparty", "receive", "minutes"]}
            if remaining_params:
                items = list(remaining_params.items())
                if len(items) >= 1:
                    param_key_1, param_value_1 = items[0]
                if len(items) >= 2:
                    param_key_2, param_value_2 = items[1]
            
            db.execute_query("""
                INSERT INTO plan_steps (
                    simulation_id, agent_id, plan_id, step_order, target_time, action, location, status,
                    travel_destination, exchange_counterparty, exchange_sku, exchange_quantity,
                    wait_minutes, param_key_1, param_value_1, param_key_2, param_value_2
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                self.simulation_id, agent_id, plan_id, step_order, step.target_time, step.action, step.location, StepStatus.PENDING.value,
                travel_dest, exchange_counterparty, exchange_sku, exchange_quantity,
                wait_minutes, param_key_1, str(param_value_1) if param_value_1 else None,
                param_key_2, str(param_value_2) if param_value_2 else None
            ), fetch=False)
            
            return True
            
        except Exception as e:
            print(f"Error inserting plan step: {e}")
            return False
    
    def get_plan(self, plan_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a plan and its steps from the database."""
        try:
            db = get_simulations_manager()
            
            # Get plan metadata
            plan_result = db.execute_query("""
                SELECT * FROM plans WHERE id = %s
            """, (plan_id,), fetch=True)
            
            if not plan_result or not plan_result.success or not plan_result.data:
                return None
            
            plan = plan_result.data[0]
            
            # Get plan steps
            steps_result = db.execute_query("""
                SELECT * FROM plan_steps 
                WHERE plan_id = %s 
                ORDER BY step_order
            """, (plan_id,), fetch=True)
            
            plan["steps"] = steps_result.data if (steps_result and steps_result.success and steps_result.data) else []
            return plan
            
        except Exception as e:
            print(f"Error retrieving plan: {e}")
            return None
    
    def get_agent_plans(self, agent_id: str, status: Optional[PlanStatus] = None) -> List[Dict[str, Any]]:
        """Get all plans for a specific agent, optionally filtered by status."""
        try:
            db = get_simulations_manager()
            
            if status:
                plans_result = db.execute_query("""
                    SELECT * FROM plans 
                    WHERE simulation_id = %s AND agent_id = %s AND status = %s
                    ORDER BY created_at DESC
                """, (self.simulation_id, agent_id, status.value), fetch=True)
            else:
                plans_result = db.execute_query("""
                    SELECT * FROM plans 
                    WHERE simulation_id = %s AND agent_id = %s
                    ORDER BY created_at DESC
                """, (self.simulation_id, agent_id), fetch=True)
            
            if plans_result and plans_result.success and plans_result.data:
                return plans_result.data
            return []
            
        except Exception as e:
            print(f"Error retrieving agent plans: {e}")
            return []
    
    def update_plan_status(self, plan_id: int, status: PlanStatus) -> bool:
        """Update the status of a plan."""
        try:
            db = get_simulations_manager()
            
            update_data = [status.value, datetime.now()]
            update_fields = ["status = %s", "updated_at = %s"]
            
            # Add timestamp fields based on status
            if status == PlanStatus.EXECUTING:
                update_fields.append("started_at = %s")
                update_data.append(datetime.now())
            elif status in [PlanStatus.COMPLETED, PlanStatus.FAILED]:
                update_fields.append("completed_at = %s")
                update_data.append(datetime.now())
            
            update_data.append(plan_id)
            
            db.execute_query(f"""
                UPDATE plans SET {', '.join(update_fields)} WHERE id = %s
            """, tuple(update_data), fetch=False)
            
            return True
            
        except Exception as e:
            print(f"Error updating plan status: {e}")
            return False
    
    def update_step_status(self, step_id: int, status: StepStatus, execution_time_ms: Optional[int] = None, error_message: Optional[str] = None) -> bool:
        """Update the status of a plan step."""
        try:
            db = get_simulations_manager()
            
            update_data = [status.value, datetime.now()]
            update_fields = ["status = %s", "executed_at = %s"]
            
            if execution_time_ms is not None:
                update_fields.append("execution_time_ms = %s")
                update_data.append(execution_time_ms)
            
            if error_message:
                update_fields.append("error_message = %s")
                update_data.append(error_message)
            
            update_data.append(step_id)
            
            db.execute_query(f"""
                UPDATE plan_steps SET {', '.join(update_fields)} WHERE id = %s
            """, tuple(update_data), fetch=False)
            
            return True
            
        except Exception as e:
            print(f"Error updating step status: {e}")
            return False
    
    def get_plan_progress(self, plan_id: int) -> Dict[str, int]:
        """Get the progress statistics for a plan."""
        try:
            db = get_simulations_manager()
            
            result = db.execute_query("""
                SELECT 
                    COUNT(*) as total_steps,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_steps,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_steps,
                    SUM(CASE WHEN status = 'executing' THEN 1 ELSE 0 END) as executing_steps
                FROM plan_steps 
                WHERE plan_id = %s
            """, (plan_id,), fetch=True)
            
            if result and result.success and result.data:
                stats = result.data[0]
                return {
                    "total_steps": stats["total_steps"] or 0,
                    "completed_steps": stats["completed_steps"] or 0,
                    "failed_steps": stats["failed_steps"] or 0,
                    "executing_steps": stats["executing_steps"] or 0
                }
            
            return {"total_steps": 0, "completed_steps": 0, "failed_steps": 0, "executing_steps": 0}
            
        except Exception as e:
            print(f"Error getting plan progress: {e}")
            return {"total_steps": 0, "completed_steps": 0, "failed_steps": 0, "executing_steps": 0}
    
    def convert_db_step_to_planstep(self, db_step: Dict[str, Any]) -> PlanStep:
        """Convert a database step record back to a PlanStep object."""
        # Reconstruct parameters from structured fields
        parameters = {}
        
        if db_step.get("travel_destination"):
            parameters["to"] = db_step["travel_destination"]
        
        if db_step.get("exchange_counterparty"):
            parameters["counterparty"] = db_step["exchange_counterparty"]
            if db_step.get("exchange_sku") and db_step.get("exchange_quantity"):
                parameters["receive"] = {db_step["exchange_sku"]: db_step["exchange_quantity"]}
        
        if db_step.get("wait_minutes"):
            parameters["minutes"] = db_step["wait_minutes"]
        
        # Add generic parameters
        if db_step.get("param_key_1") and db_step.get("param_value_1"):
            parameters[db_step["param_key_1"]] = db_step["param_value_1"]
        if db_step.get("param_key_2") and db_step.get("param_value_2"):
            parameters[db_step["param_key_2"]] = db_step["param_value_2"]
        
        return PlanStep(
            target_time=db_step["target_time"],
            action=db_step["action"],
            location=db_step["location"],
            parameters=parameters
        )
