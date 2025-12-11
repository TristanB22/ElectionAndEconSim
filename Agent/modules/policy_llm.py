#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from typing import Dict, Any, List, Optional
import jsonschema
import logging

from Utils.api_manager import APIManager

logger = logging.getLogger(__name__)

class PolicyLLM:
    """
    wrapper around llm for strict-json policies. validates against schemas and returns errors on invalid.
    comments are lowercase.
    """

    def __init__(self, api_manager: Optional[APIManager] = None):
        self.api_manager = api_manager or APIManager()
        self.schemas = self._load_schemas()

    def _load_schemas(self) -> Dict[str, Any]:
        """Loads JSON schemas from the schemas directory."""
        schemas_dir = os.path.join(os.path.dirname(__file__), "schemas")
        loaded_schemas = {}
        for filename in os.listdir(schemas_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(schemas_dir, filename)
                with open(filepath, 'r') as f:
                    schema_name = filename.replace(".json", "")
                    loaded_schemas[schema_name] = json.load(f)
        return loaded_schemas

    def _validate_json(self, data: Dict[str, Any], schema_name: str) -> bool:
        """Validates JSON data against a specified schema."""
        schema = self.schemas.get(schema_name)
        if not schema:
            logger.error(f"Schema '{schema_name}' not found for validation.")
            return False
        try:
            jsonschema.validate(instance=data, schema=schema)
            return True
        except jsonschema.exceptions.ValidationError as e:
            logger.error(f"JSON validation failed for schema '{schema_name}': {e.message}")
            return False
        except Exception as e:
            logger.error(f"An unexpected error occurred during JSON validation: {e}")
            return False

    def decide_day_plan(self, situation_card: Dict[str, Any], affordances: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Outsources daily planning to an LLM.
        Returns strict JSON action plan.
        """
        prompt = self._build_plan_prompt(situation_card, affordances)
        try:
            response_text, *_ = self.api_manager.make_request(prompt, intelligence_level=3, max_tokens=2000, temperature=0.7)
            plan_json = json.loads(response_text)
            if self._validate_json(plan_json, "action_plan"):
                return plan_json
            else:
                logger.warning("LLM returned invalid action plan JSON.")
                return None
        except Exception as e:
            logger.error(f"Error in decide_day_plan: {e}", exc_info=True)
            return None

    def decide_action(self, situation_card: Dict[str, Any], affordances: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Outsources action selection to an LLM.
        Returns strict JSON action.
        """
        # Similar to decide_day_plan but for a single action
        prompt = self._build_action_prompt(situation_card, affordances)
        try:
            response_text, *_ = self.api_manager.make_request(prompt, intelligence_level=2, max_tokens=500, temperature=0.5)
            action_json = json.loads(response_text)
            # if self._validate_json(action_json, "action_single"):
            #     return action_json
            # else:
            #     logger.warning("LLM returned invalid action JSON.")
            #     return None
            return action_json
        except Exception as e:
            logger.error(f"Error in decide_action: {e}", exc_info=True)
            return None

    def decide_conversation(self, convo_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Outsources conversation replies to an LLM.
        Returns strict JSON conversation turns.
        """
        prompt = self._build_conversation_prompt(convo_context)
        try:
            response_text, *_ = self.api_manager.make_request(prompt, intelligence_level=2, max_tokens=1000, temperature=0.8)
            conversation_json = json.loads(response_text)
            if self._validate_json(conversation_json, "conversation"):
                return conversation_json
            else:
                logger.warning("LLM returned invalid conversation JSON.")
                return None
        except Exception as e:
            logger.error(f"Error in decide_conversation: {e}", exc_info=True)
            return None

    def propose_artifact(self, situation_card: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Outsources artifact proposals to an LLM.
        Returns strict JSON artifact idea.
        """
        prompt = self._build_artifact_proposal_prompt(situation_card)
        try:
            response_text, *_ = self.api_manager.make_request(prompt, intelligence_level=3, max_tokens=1000, temperature=0.7)
            artifact_idea_json = json.loads(response_text)
            if self._validate_json(artifact_idea_json, "artifact_idea"):
                return artifact_idea_json
            else:
                logger.warning("LLM returned invalid artifact idea JSON.")
                return None
        except Exception as e:
            logger.error(f"Error in propose_artifact: {e}", exc_info=True)
            return None

    def _build_plan_prompt(self, situation_card: Dict[str, Any], affordances: Dict[str, Any]) -> str:
        """Constructs the prompt for daily planning."""
        # This prompt needs to be carefully crafted to guide the LLM
        # to produce valid JSON and respect constraints.
        
        # Extract relevant info from situation_card
        agent_profile = situation_card.get("agent_profile", {})
        goals = situation_card.get("goals", [])
        constraints = situation_card.get("constraints", {})
        traits = situation_card.get("traits", {})
        knowledge = situation_card.get("knowledge_snapshot", [])
        opinions = situation_card.get("opinions_excerpt", {})
        recent_events = situation_card.get("recent_events", [])
        
        # Format affordances for the prompt
        formatted_affordances = []
        for op_type, caps in affordances.items():
            for cap in caps:
                props_str = str(cap.props)
                formatted_affordances.append(f"- {op_type}: {cap.target_id} (props: {props_str})")

        prompt = f"""
        You are an AI agent in a simulation. Your task is to create a daily plan in strict JSON format.
        
        AGENT PROFILE:
        {json.dumps(agent_profile, indent=2)}
        
        CURRENT GOALS: {', '.join(goals)}
        
        CONSTRAINTS (budgets, etc.):
        {json.dumps(constraints, indent=2)}
        
        YOUR TRAITS:
        {json.dumps(traits, indent=2)}
        
        YOUR KNOWLEDGE (what you know about the world):
        {json.dumps(knowledge, indent=2)}
        
        YOUR OPINIONS (about people and places):
        {json.dumps(opinions, indent=2)}
        
        RECENT EVENTS:
        {json.dumps(recent_events, indent=2)}
        
        AVAILABLE AFFORDANCES (actions you can take, filtered by your knowledge):
        {chr(10).join(formatted_affordances)}
        
        INSTRUCTIONS:
        1. Select actions that respect your budgets (time, attention, cash), memberships, and knowledge.
        2. Prefer familiar places/people unless your goals or curiosity (trait) justify novelty.
        3. Account for your risk_aversion (trait) when choosing actions.
        4. Output ONLY a strict JSON object matching the "action_plan.json" schema.
        5. Include a one-sentence rationale for your plan.
        
        SCHEMA:
        {json.dumps(self.schemas.get("action_plan"), indent=2)}
        
        YOUR PLAN (strict JSON only):
        """
        return prompt

    def _build_action_prompt(self, situation_card: Dict[str, Any], affordances: Dict[str, Any]) -> str:
        """Constructs the prompt for single action decision."""
        # This would be a more focused version of the plan prompt for a single step.
        # For simplicity, it can reuse parts of the plan prompt.
        return self._build_plan_prompt(situation_card, affordances) # Reusing for now

    def _build_conversation_prompt(self, convo_context: Dict[str, Any]) -> str:
        """Constructs the prompt for conversation decisions."""
        prompt = f"""
        You are participating in a conversation in a simulation. Your task is to generate the next turn(s) in the conversation in strict JSON format.
        
        CONVERSATION CONTEXT:
        {json.dumps(convo_context, indent=2)}
        
        INSTRUCTIONS:
        1. Simulate a short exchange within a 15-minute time slot.
        2. Output ONLY a strict JSON object matching the "conversation.json" schema.
        3. Include turns, potential commitments, and relationship/trust deltas.
        4. Adjust intent/goals as appropriate.
        
        SCHEMA:
        {json.dumps(self.schemas.get("conversation"), indent=2)}
        
        YOUR CONVERSATION TURNS (strict JSON only):
        """
        return prompt

    def _build_artifact_proposal_prompt(self, situation_card: Dict[str, Any]) -> str:
        """Constructs the prompt for artifact proposals."""
        prompt = f"""
        You are an innovative agent in a simulation. Your task is to propose a new artifact (e.g., channel, product, organization) in strict JSON format.
        
        YOUR CURRENT SITUATION:
        {json.dumps(situation_card, indent=2)}
        
        INSTRUCTIONS:
        1. Propose an ArtifactIdea constrained by your available time, capital, talent, compliance, and infrastructure (implied by situation_card).
        2. Output ONLY a strict JSON object matching the "artifact_idea.json" schema.
        
        SCHEMA:
        {json.dumps(self.schemas.get("artifact_idea"), indent=2)}
        
        YOUR ARTIFACT IDEA (strict JSON only):
        """
        return prompt


