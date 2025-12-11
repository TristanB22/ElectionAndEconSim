from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import json
import re
from .simulation_config import SimulationConfig

class LLMSimulationParser:
    """Use the most intelligent model to parse natural language into simulation config"""
    
    def __init__(self, api_manager):
        self.api_manager = api_manager
    
    def parse_query(self, query: str) -> SimulationConfig:
        """Parse natural language query using LLM to generate configuration"""
        
        # Create the prompt for the LLM
        prompt = self._create_parsing_prompt(query)
        
        # Get response from most intelligent model
        response, _, model_name, _ = self.api_manager.make_request(
            prompt=prompt,
            intelligence_level=3,  # Use your highest intelligence level
            max_tokens=2000,
            temperature=0.1  # Low temperature for consistent parsing
        )
        
        if not response:
            raise ValueError("Failed to get response from LLM")
        
        # Parse the JSON response
        try:
            config_data = json.loads(response)
            return self._create_config_from_llm_response(config_data, query)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse LLM response as JSON: {e}")
    
    def _create_parsing_prompt(self, query: str) -> str:
        return f"""You are an expert simulation configuration generator for an economic agent-based simulation system.

USER QUERY: {query}

Based on this query, generate a complete simulation configuration in valid JSON format. The configuration should include:

{{
  "name": "Descriptive name for the simulation",
  "description": "Detailed description of what this simulation will do",
  "simulation_type": "Type of simulation (e.g., 'retail_day', 'global_economy', 'sector_analysis')",
  "start_datetime": "YYYY-MM-DDTHH:MM:SS format for simulation start",
  "end_datetime": "YYYY-MM-DDTHH:MM:SS format for simulation end", 
  "tick_granularity": "Time granularity (must be one of: '5m', '15m', '30m', '1h', '2h', '4h', '6h', '12h', '1d', '1w', '1M')",
  "world_context": "Description of the world context for agents",
  "firms_to_include": ["List of firm IDs to include"],
  "agent_count": "Number of agents to create",
  "agent_selection_criteria": {{
    "age_range": [min_age, max_age],
    "income_range": [min_income, max_income],
    "education_levels": ["list", "of", "education", "levels"],
    "geographic_preference": "geographic area preference"
  }},
  "initial_conditions": {{
    "economic_climate": "description of economic conditions",
    "market_conditions": "description of market state",
    "policy_environment": "description of policy context"
  }},
  "economic_policies": {{
    "tax_rates": "tax policy description",
    "interest_rates": "monetary policy description",
    "regulations": "regulatory environment description"
  }},
  "agent_goals": {{
    "default_goal": "Default goal for all agents",
    "specific_goals": {{"agent_type": "specific goal"}}
  }},
  "simulation_objectives": ["List of objectives to achieve"],
  "custom_parameters": {{"Any additional parameters"}}
}}

IMPORTANT RULES:
1. Return ONLY valid JSON, no additional text
2. Use realistic dates and times
3. Make agent_count reasonable (3-1000 depending on scope)
4. Include relevant firms if specific industries mentioned
5. Make world_context detailed and realistic
6. Use appropriate tick_granularity for the simulation duration

Generate the configuration now:"""
    
    def _create_config_from_llm_response(self, config_data: Dict[str, Any], original_query: str) -> SimulationConfig:
        """Convert LLM response to SimulationConfig object"""
        
        # Parse datetime strings
        start_dt = datetime.fromisoformat(config_data["start_datetime"])
        end_dt = datetime.fromisoformat(config_data["end_datetime"])
        
        return SimulationConfig(
            name=config_data["name"],
            description=config_data["description"],
            simulation_type=config_data["simulation_type"],
            start_datetime=start_dt,
            end_datetime=end_dt,
            tick_granularity=config_data.get("tick_granularity", "15m"),
            world_context=config_data["world_context"],
            firms_to_include=config_data.get("firms_to_include", []),
            agent_count=config_data.get("agent_count", 3),
            agent_selection_criteria=config_data.get("agent_selection_criteria", {}),
            initial_conditions=config_data.get("initial_conditions", {}),
            economic_policies=config_data.get("economic_policies", {}),
            agent_goals=config_data.get("agent_goals", {}),
            simulation_objectives=config_data.get("simulation_objectives", []),
            custom_parameters=config_data.get("custom_parameters", {})
        )
