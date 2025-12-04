#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import json
import os
import logging

from .policy_llm import PolicyLLM
from .knowledge_base import AgentKnowledgeBase
from .opinions import OpinionsStore, PersonOpinion
from Utils.api_manager import APIManager
from Database.managers import get_simulations_manager as get_simulation_data_manager
from Agent.modules.memory_manager import MemoryManager

logger = logging.getLogger(__name__)

@dataclass
class ConversationTurn:
    speaker_id: str
    message: str
    timestamp: datetime
    # Additional fields for LLM output
    intent: Optional[str] = None
    commitment: Optional[str] = None
    trust_delta: float = 0.0
    liking_delta: float = 0.0
    goal_adjustments: List[str] = field(default_factory=list)

@dataclass
class ConversationContext:
    agent_a_id: str
    agent_b_id: str
    channel_id: str
    current_time: datetime
    history: List[ConversationTurn] = field(default_factory=list)
    agent_a_profile: Dict[str, Any] = field(default_factory=dict)
    agent_b_profile: Dict[str, Any] = field(default_factory=dict)
    shared_context: str = ""
    channel_properties: Dict[str, Any] = field(default_factory=dict)

class ConversationManager:
    """
    lightweight conversation engine that fits in a 15-minute tick and persists to mysql and qdrant.
    comments are lowercase.
    """

    def __init__(self, simulation_id: str, api_manager: APIManager):
        self.simulation_id = simulation_id
        self.api_manager = api_manager
        self.policy_llm = PolicyLLM(api_manager=api_manager)
        self.db_manager = get_simulation_data_manager()
        self.memory_managers: Dict[str, MemoryManager] = {} # Agent ID -> MemoryManager

    def _get_memory_manager(self, agent_id: str) -> MemoryManager:
        """Lazily initialize and retrieve memory manager for an agent."""
        if agent_id not in self.memory_managers:
            self.memory_managers[agent_id] = MemoryManager(agent_id)
        return self.memory_managers[agent_id]

    def run_conversation(self, agent_a: Any, agent_b: Any, channel_id: str,
                        context: str, current_time: datetime) -> Optional[List[ConversationTurn]]:
        """
        Runs a short conversation between two agents within a 15-minute tick.
        
        Args:
            agent_a: The initiating agent object.
            agent_b: The responding agent object.
            channel_id: The ID of the channel the conversation is happening on.
            context: Additional context for the conversation.
            current_time: The current simulation datetime.
            
        Returns:
            Optional[List[ConversationTurn]]: A list of conversation turns, or None if failed.
        """
        logger.info(f"Starting conversation between {agent_a.agent_id} and {agent_b.agent_id} on channel {channel_id}")
        
        # Build compact per-agent conversation context
        convo_context = self._build_conversation_context(agent_a, agent_b, channel_id, context, current_time)
        
        try:
            # Call LLM to produce strict JSON turns
            conversation_json = self.policy_llm.decide_conversation(convo_context)
            if not conversation_json or not conversation_json.get("turns"):
                logger.warning(f"LLM returned no valid conversation turns for {agent_a.agent_id}-{agent_b.agent_id}")
                return None
            
            turns_data = conversation_json["turns"]
            conversation_turns = [ConversationTurn(**turn) for turn in turns_data]
            
            # persist header row in conversations
            conversation_id = f"{agent_a.agent_id}_{agent_b.agent_id}_{int(current_time.timestamp())}"
            try:
                self.db_manager.db_manager.execute_query(
                    """
                    INSERT INTO conversations (simulation_id, conversation_id, agent_a_id, agent_b_id, channel_id, status, started_at, context, summary)
                    VALUES (%s,%s,%s,%s,%s,'active',%s,%s,%s)
                    ON DUPLICATE KEY UPDATE summary=VALUES(summary)
                    """,
                    (
                        self.simulation_id,
                        conversation_id,
                        str(agent_a.agent_id),
                        str(agent_b.agent_id),
                        channel_id,
                        current_time,
                        json.dumps({"context": context}),
                        conversation_json.get("summary", "conversation started"),
                    ),
                    database=self.db_manager.sim_db,
                    fetch=False,
                )
            except Exception:
                pass
            
            # Log conversation started event
            self._log_conversation_event("conversation_started", agent_a.agent_id, agent_b.agent_id, channel_id, current_time, {"context": context})
            
            # Process each turn and persist
            for idx, turn in enumerate(conversation_turns, start=1):
                try:
                    self.db_manager.db_manager.execute_query(
                        """
                        INSERT INTO conversation_turns (conversation_id, turn_number, speaker_id, message_text, message_type, timestamp, metadata)
                        VALUES (%s,%s,%s,%s,'text',%s,%s)
                        """,
                        (
                            conversation_id,
                            idx,
                            turn.speaker_id,
                            turn.message,
                            turn.timestamp,
                            json.dumps({
                                "intent": turn.intent,
                                "commitment": turn.commitment,
                                "trust_delta": turn.trust_delta,
                                "liking_delta": turn.liking_delta,
                                "goal_adjustments": turn.goal_adjustments,
                            }),
                        ),
                        database=self.db_manager.sim_db,
                        fetch=False,
                    )
                except Exception:
                    pass
                
                self._log_conversation_event("conversation_turn", turn.speaker_id, turn.speaker_id, channel_id, turn.timestamp, {
                    "message": turn.message,
                    "intent": turn.intent,
                    "commitment": turn.commitment,
                    "trust_delta": turn.trust_delta,
                    "liking_delta": turn.liking_delta,
                    "goal_adjustments": turn.goal_adjustments
                })
                
                # Update opinions and knowledge base
                self._update_agent_state_from_turn(agent_a, agent_b, turn)
                
                # Upsert short summaries & embeddings into Qdrant
                self._upsert_conversation_memory(agent_a, agent_b, channel_id, turn)
                
                # persist commitments
                if turn.commitment:
                    try:
                        self.db_manager.db_manager.execute_query(
                            """
                            INSERT INTO conversation_commitments (conversation_id, agent_id, commitment_text, created_at, status)
                            VALUES (%s,%s,%s,%s,'open')
                            """,
                            (
                                conversation_id,
                                turn.speaker_id,
                                turn.commitment,
                                turn.timestamp,
                            ),
                            database=self.db_manager.sim_db,
                            fetch=False,
                        )
                    except Exception:
                        pass
            
            # Log conversation committed event and close header row
            self._log_conversation_event("conversation_committed", agent_a.agent_id, agent_b.agent_id, channel_id, current_time, {"summary": conversation_json.get("summary", "Conversation concluded.")})
            try:
                self.db_manager.db_manager.execute_query(
                    """
                    UPDATE conversations SET status='completed', ended_at=%s, summary=%s WHERE conversation_id=%s
                    """,
                    (current_time, conversation_json.get("summary", "Conversation concluded."), conversation_id),
                    database=self.db_manager.sim_db,
                    fetch=False,
                )
            except Exception:
                pass
            
            logger.info(f"Conversation between {agent_a.agent_id} and {agent_b.agent_id} completed with {len(conversation_turns)} turns.")
            return conversation_turns
            
        except Exception as e:
            logger.error(f"Error running conversation between {agent_a.agent_id} and {agent_b.agent_id}: {e}", exc_info=True)
            return None

    def _build_conversation_context(self, agent_a: Any, agent_b: Any, channel_id: str,
                                  shared_context: str, current_time: datetime) -> ConversationContext:
        """Builds a compact conversation context for the LLM."""
        # Get personal summaries
        agent_a_summary = getattr(agent_a, 'llm_summary', None) or getattr(agent_a, 'l2_summary', None) or "No summary available"
        agent_b_summary = getattr(agent_b, 'llm_summary', None) or getattr(agent_b, 'l2_summary', None) or "No summary available"
        
        # Get last interactions (from opinions)
        agent_a_opinion_b = agent_a.opinions.get_person_opinion(str(agent_b.agent_id)) if hasattr(agent_a, 'opinions') else None
        agent_b_opinion_a = agent_b.opinions.get_person_opinion(str(agent_a.agent_id)) if hasattr(agent_b, 'opinions') else None
        
        agent_a_profile = {
            "id": str(agent_a.agent_id),
            "name": getattr(agent_a, 'get_name', lambda: f"Agent {agent_a.agent_id}")(),
            "personal_summary": agent_a_summary,
            "current_goals": [g.description for g in getattr(agent_a, 'intent_manager', type('obj', (object,), {'get_active_goals': lambda: []})()).get_active_goals()],
            "opinion_of_b": agent_a_opinion_b.__dict__ if agent_a_opinion_b else {"trust": 0.5, "liking": 0.5}
        }
        
        agent_b_profile = {
            "id": str(agent_b.agent_id),
            "name": getattr(agent_b, 'get_name', lambda: f"Agent {agent_b.agent_id}")(),
            "personal_summary": agent_b_summary,
            "current_goals": [g.description for g in getattr(agent_b, 'intent_manager', type('obj', (object,), {'get_active_goals': lambda: []})()).get_active_goals()],
            "opinion_of_a": agent_b_opinion_a.__dict__ if agent_b_opinion_a else {"trust": 0.5, "liking": 0.5}
        }
        
        # Placeholder for channel properties
        channel_properties = {"id": channel_id, "type": "dm", "latency": 5}
        
        # Retrieve recent conversation history from Qdrant/memory manager
        agent_a_memories = self._get_memory_manager(str(agent_a.agent_id)).search_memories(f"conversation with {agent_b_profile['name']}", k=3)
        agent_b_memories = self._get_memory_manager(str(agent_b.agent_id)).search_memories(f"conversation with {agent_a_profile['name']}", k=3)
        
        history_summary = []
        if agent_a_memories:
            history_summary.append(f"Agent A's recent thoughts about Agent B: {'; '.join([m[0] for m in agent_a_memories])}")
        if agent_b_memories:
            history_summary.append(f"Agent B's recent thoughts about Agent A: {'; '.join([m[0] for m in agent_b_memories])}")
        
        return ConversationContext(
            agent_a_id=str(agent_a.agent_id),
            agent_b_id=str(agent_b.agent_id),
            channel_id=channel_id,
            current_time=current_time,
            agent_a_profile=agent_a_profile,
            agent_b_profile=agent_b_profile,
            shared_context=shared_context + "\n" + "\n".join(history_summary),
            channel_properties=channel_properties
        )

    def _log_conversation_event(self, event_type: str, source_id: str, target_id: str,
                              channel_id: str, timestamp: datetime, metadata: Dict[str, Any]) -> bool:
        """Logs a conversation event to MySQL."""
        return self.db_manager.log_action(
            simulation_id=self.simulation_id,
            agent_id=source_id,
            action_name=f"conversation_{event_type}",
            action_params={"target_id": target_id, "channel_id": channel_id, **metadata},
            events_generated=[],
            journal_entries=[],
            execution_time_ms=0,
            status="success",
            timestamp=timestamp
        )

    def _update_agent_state_from_turn(self, agent_a: Any, agent_b: Any, turn: ConversationTurn) -> None:
        """Updates agents' opinions and knowledge based on a conversation turn."""
        speaker = agent_a if str(agent_a.agent_id) == turn.speaker_id else agent_b
        counterparty = agent_b if str(agent_a.agent_id) == turn.speaker_id else agent_a
        
        # Update opinions
        if hasattr(speaker, 'opinions'):
            speaker.opinions.update_person_opinion(
                str(counterparty.agent_id),
                turn.trust_delta,
                turn.liking_delta,
                turn.timestamp
            )
        
        # Update knowledge base (who knows whom; inferred roles/capabilities)
        if hasattr(speaker, 'knowledge'):
            speaker.knowledge.add(str(counterparty.agent_id), "person", "social", 0.7, properties={"last_convo_topic": turn.intent})
            # If a commitment implies a role (e.g., "I'm a doctor"), add to knowledge
            if turn.commitment and "doctor" in turn.commitment.lower():
                speaker.knowledge.add(f"{counterparty.get_name()}_doctor", "role", "inferred", 0.8, parent_entity_id=str(counterparty.agent_id))
        
        # Update goals (simplified)
        if turn.goal_adjustments and hasattr(speaker, 'intent_manager'):
            for adjustment in turn.goal_adjustments:
                logger.debug(f"Agent {speaker.agent_id} goal adjustment: {adjustment}")

    def _upsert_conversation_memory(self, agent_a: Any, agent_b: Any, channel_id: str, turn: ConversationTurn) -> None:
        """Upserts short summaries & embeddings into Qdrant keyed by (agent_id, counterparty_id, ts)."""
        # Create a summary of the turn for memory
        memory_content = f"Conversation on {channel_id} with {turn.speaker_id}. Message: '{turn.message}'. Intent: {turn.intent}. Commitment: {turn.commitment}."
        
        # Add to speaker's memory
        speaker_mm = self._get_memory_manager(turn.speaker_id)
        speaker_mm.add_memory(
            content=memory_content,
            impact_score=int(turn.trust_delta * 10 + 5), # Scale impact by trust delta
            event={"timestamp": turn.timestamp.timestamp()} # Pass timestamp for memory creation
        )
        
        # Add to counterparty's memory (from their perspective)
        counterparty_id = str(agent_a.agent_id) if str(agent_b.agent_id) == turn.speaker_id else str(agent_b.agent_id)
        counterparty_mm = self._get_memory_manager(counterparty_id)
        counterparty_memory_content = f"Conversation on {channel_id} with {turn.speaker_id}. They said: '{turn.message}'. My interpretation: Intent: {turn.intent}. Commitment: {turn.commitment}."
        counterparty_mm.add_memory(
            content=counterparty_memory_content,
            impact_score=int(turn.trust_delta * 10 + 5), # Scale impact by trust delta
            event={"timestamp": turn.timestamp.timestamp()}
        )


