from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import json

@dataclass
class SimulationConfig:
    """LLM-generated simulation configuration"""
    # Core simulation parameters
    name: str
    description: str
    simulation_type: str  # "retail_day", "global_economy", "sector_analysis", etc.
    
    # Time configuration
    start_datetime: datetime
    end_datetime: datetime
    world_context: str
    
    # Optional parameters with defaults
    tick_granularity: str = "15m"
    firms_to_include: List[str] = field(default_factory=list)
    agent_count: int = 3
    agent_selection_criteria: Dict[str, Any] = field(default_factory=dict)
    
    # Economic parameters
    initial_conditions: Dict[str, Any] = field(default_factory=dict)
    economic_policies: Dict[str, Any] = field(default_factory=dict)
    
    # Goals and objectives
    agent_goals: Dict[str, str] = field(default_factory=dict)
    simulation_objectives: List[str] = field(default_factory=list)
    
    # Advanced settings
    custom_parameters: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "simulation_type": self.simulation_type,
            "start_datetime": self.start_datetime.isoformat(),
            "end_datetime": self.end_datetime.isoformat(),
            "tick_granularity": self.tick_granularity,
            "world_context": self.world_context,
            "firms_to_include": self.firms_to_include,
            "agent_count": self.agent_count,
            "agent_selection_criteria": self.agent_selection_criteria,
            "initial_conditions": self.initial_conditions,
            "economic_policies": self.economic_policies,
            "agent_goals": self.agent_goals,
            "simulation_objectives": self.simulation_objectives,
            "custom_parameters": self.custom_parameters
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SimulationConfig':
        """Create SimulationConfig from dictionary"""
        # Parse datetime strings
        start_dt = datetime.fromisoformat(data["start_datetime"])
        end_dt = datetime.fromisoformat(data["end_datetime"])
        
        return cls(
            name=data["name"],
            description=data["description"],
            simulation_type=data["simulation_type"],
            start_datetime=start_dt,
            end_datetime=end_dt,
            tick_granularity=data.get("tick_granularity", "15m"),
            world_context=data["world_context"],
            firms_to_include=data.get("firms_to_include", []),
            agent_count=data.get("agent_count", 3),
            agent_selection_criteria=data.get("agent_selection_criteria", {}),
            initial_conditions=data.get("initial_conditions", {}),
            economic_policies=data.get("economic_policies", {}),
            agent_goals=data.get("agent_goals", {}),
            simulation_objectives=data.get("simulation_objectives", []),
            custom_parameters=data.get("custom_parameters", {})
        )
