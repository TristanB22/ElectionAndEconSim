#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
import logging

from .channels import ChannelSpec, register_channel_actions
from .channel_registry import get_global_channel_registry
from .policy_llm import PolicyLLM
from Utils.api_manager import APIManager
from Database.managers import get_simulations_manager as get_simulation_data_manager

logger = logging.getLogger(__name__)

@dataclass
class ArtifactIdea:
    id: str
    artifact_type: str # media_channel|platform|organization|product|protocol|meme
    concept: str # short description
    target_users: List[str] # e.g., ["young adults", "local businesses"]
    affordances: List[str] # e.g., ["post", "dm", "organize_event"]
    creator_agent_id: str
    proposed_at: datetime
    initial_capital_cost: float = 0.0
    initial_time_cost_hours: float = 0.0
    status: str = "proposed" # proposed|prototyped|evaluated|published|killed
    prototype_spec: Optional[Dict[str, Any]] = None # For channels, this would be a ChannelSpec dict
    evaluation_metrics: Dict[str, Any] = field(default_factory=dict)
    published_spec_id: Optional[str] = None

class InnovationEngine:
    """
    compile -> prototype -> evaluate -> publish for new channels.
    comments are lowercase.
    """

    def __init__(self, simulation_id: str, api_manager: APIManager):
        self.simulation_id = simulation_id
        self.api_manager = api_manager
        self.policy_llm = PolicyLLM(api_manager=api_manager)
        self.channel_registry = get_global_channel_registry()
        self.db_manager = get_simulation_data_manager()
        self._ideas: Dict[str, ArtifactIdea] = {} # id -> ArtifactIdea

    def propose_artifact(self, agent: Any, situation_card: Dict[str, Any]) -> Optional[ArtifactIdea]:
        """
        Agent proposes a new artifact (e.g., channel, product) using the LLM.
        """
        logger.info(f"Agent {agent.agent_id} proposing new artifact.")
        try:
            artifact_idea_json = self.policy_llm.propose_artifact(situation_card)
            if not artifact_idea_json:
                logger.warning(f"LLM returned no valid artifact idea for agent {agent.agent_id}.")
                return None
            
            idea_id = str(uuid.uuid4())
            new_idea = ArtifactIdea(
                id=idea_id,
                artifact_type=artifact_idea_json["artifact_type"],
                concept=artifact_idea_json["concept"],
                target_users=artifact_idea_json.get("target_users", []),
                affordances=artifact_idea_json.get("affordances", []),
                creator_agent_id=str(agent.agent_id),
                proposed_at=datetime.now(),
                initial_capital_cost=artifact_idea_json.get("initial_capital_cost", 0.0),
                initial_time_cost_hours=artifact_idea_json.get("initial_time_cost_hours", 0.0)
            )
            self._ideas[idea_id] = new_idea
            self._log_innovation_event("artifact_proposed", new_idea)
            logger.info(f"Agent {agent.agent_id} proposed new artifact: {new_idea.concept} ({new_idea.artifact_type})")
            return new_idea
        except Exception as e:
            logger.error(f"Error proposing artifact for agent {agent.agent_id}: {e}", exc_info=True)
            return None

    def compile_channel(self, idea: ArtifactIdea) -> Optional[ChannelSpec]:
        """
        Compiles an ArtifactIdea of type 'media_channel' into a ChannelSpec (prototype caps).
        """
        if idea.artifact_type != "media_channel":
            logger.warning(f"Idea {idea.id} is not a media_channel, cannot compile.")
            return None
        
        # This is a simplified compilation. In a real system, LLM might help define parameters.
        # For now, we'll create a basic ChannelSpec from the idea.
        channel_id = f"prototype_{idea.id[:8]}"
        prototype_spec = ChannelSpec(
            id=channel_id,
            topology="dm", # Default to DM for simplicity
            targeting={"scope": "local", "creator_id": idea.creator_agent_id},
            costs={"money": idea.initial_capital_cost / 10, "time": idea.initial_time_cost_hours / 10, "social_capital": 0.0, "compute": 0.001},
            friction={"signup_steps": 0, "rate_limit_per_day": 50},
            credibility_baseline=0.5,
            latency_s=10,
            caps={"daily_slots": 100, "group_size": 2},
            diffusion={"homophily": 0.7, "tail": 0.1}
        )
        idea.prototype_spec = prototype_spec.__dict__
        idea.status = "prototyped"
        self._log_innovation_event("artifact_prototyped", idea)
        logger.info(f"Idea {idea.id} prototyped as channel {channel_id}.")
        return prototype_spec

    def evaluate(self, idea: ArtifactIdea) -> bool:
        """
        Evaluates a prototyped artifact based on simulated telemetry.
        Returns True if evaluation passes, False otherwise.
        """
        if idea.status != "prototyped":
            logger.warning(f"Idea {idea.id} is not in 'prototyped' status, cannot evaluate.")
            return False
        
        # Simulate telemetry (placeholder)
        usage_count = 10 + (datetime.now() - idea.proposed_at).days * 5 # Simple growth
        retention_rate = 0.6 + (uuid.uuid4().int % 100 / 1000.0) # Some randomness
        
        idea.evaluation_metrics = {
            "usage_count": usage_count,
            "retention_rate": retention_rate,
            "cost_vs_benefit": (usage_count * retention_rate) / (idea.initial_capital_cost + idea.initial_time_cost_hours) if (idea.initial_capital_cost + idea.initial_time_cost_hours) > 0 else 1.0
        }
        
        # Define evaluation thresholds
        min_usage = 20
        min_retention = 0.5
        
        if usage_count >= min_usage and retention_rate >= min_retention:
            idea.status = "evaluated_pass"
            self._log_innovation_event("artifact_evaluated", idea, {"result": "pass"})
            logger.info(f"Idea {idea.id} evaluation PASSED. Usage: {usage_count}, Retention: {retention_rate:.2f}")
            return True
        else:
            idea.status = "evaluated_fail"
            self._log_innovation_event("artifact_evaluated", idea, {"result": "fail"})
            logger.info(f"Idea {idea.id} evaluation FAILED. Usage: {usage_count}, Retention: {retention_rate:.2f}")
            return False

    def publish(self, idea: ArtifactIdea) -> bool:
        """
        Publishes an evaluated artifact, lifting caps and registering it.
        """
        if idea.status != "evaluated_pass" or not idea.prototype_spec:
            logger.warning(f"Idea {idea.id} not ready for publication (status: {idea.status}, prototype_spec: {bool(idea.prototype_spec)}).")
            return False
        
        # Create a full ChannelSpec from the prototype, lifting caps
        published_spec_dict = idea.prototype_spec.copy()
        published_spec_dict["id"] = f"published_{idea.id[:8]}" # New ID for published version
        published_spec_dict["caps"]["daily_slots"] = 10000 # Lift caps
        published_spec_dict["friction"]["rate_limit_per_day"] = 1000 # Lift caps
        
        published_spec = ChannelSpec(**published_spec_dict)
        
        try:
            self.channel_registry.register_channel(published_spec)
            # Register actions for the published channel
            # This requires the world's action registry, which is not directly available here.
            # A better design would be to pass the action_registry to the InnovationEngine or have a global accessor.
            # For now, we'll assume a global action_registry is accessible or passed.
            # Placeholder:
            # register_channel_actions(world.registry, published_spec)
            
            idea.status = "published"
            idea.published_spec_id = published_spec.id
            self._log_innovation_event("artifact_published", idea, {"published_channel_id": published_spec.id})
            logger.info(f"Idea {idea.id} PUBLISHED as channel {published_spec.id}.")
            return True
        except Exception as e:
            logger.error(f"Error publishing idea {idea.id}: {e}", exc_info=True)
            return False

    def kill_artifact(self, idea: ArtifactIdea, reason: str) -> None:
        """
        Marks an artifact idea as killed.
        """
        idea.status = "killed"
        self._log_innovation_event("artifact_killed", idea, {"reason": reason})
        logger.info(f"Idea {idea.id} KILLED: {reason}")

    def _log_innovation_event(self, event_type: str, idea: ArtifactIdea, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Logs an innovation event to MySQL."""
        full_metadata = {
            "idea_id": idea.id,
            "artifact_type": idea.artifact_type,
            "concept": idea.concept,
            "status": idea.status,
            "creator_agent_id": idea.creator_agent_id,
            "proposed_at": idea.proposed_at.isoformat(),
            "prototype_spec": idea.prototype_spec,
            "evaluation_metrics": idea.evaluation_metrics,
            "published_spec_id": idea.published_spec_id,
            **(metadata or {})
        }
        return self.db_manager.log_action(
            simulation_id=self.simulation_id,
            agent_id=idea.creator_agent_id,
            action_name=f"innovation_{event_type}",
            action_params=full_metadata,
            events_generated=[],
            journal_entries=[],
            execution_time_ms=0,
            status="success",
            timestamp=datetime.now()
        )


