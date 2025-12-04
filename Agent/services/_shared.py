from __future__ import annotations

from typing import Optional

from Agent.agent import Agent
from Agent.models import AgentDTO
from Agent.modules.personal_summary import PersonalSummaryGenerator
from Utils.l2_data.l2_data_parser import L2DataParser


def build_agent_from_dto(dto: AgentDTO) -> Agent:
    """Reconstruct an Agent instance from DTO data without touching databases."""
    l2_row = None
    if dto.l2_data:
        l2_row = L2DataParser.parse_row(dto.l2_data)
    agent = Agent(agent_id=dto.agent_id, l2_data=l2_row, simulation_id=dto.simulation_id)
    if dto.llm_summary:
        agent.llm_summary = dto.llm_summary
    if dto.l2_summary:
        agent.l2_summary = dto.l2_summary
    return agent


def resolve_agent_summary(agent: Agent, dto: AgentDTO) -> str:
    """Return the best summary available for planning or LLM context."""
    if dto.llm_summary:
        return dto.llm_summary
    if dto.l2_summary:
        return dto.l2_summary
    if agent.l2_data:
        generator = PersonalSummaryGenerator()
        try:
            summary = generator.create_comprehensive_l2_summary(agent)
            agent.l2_summary = summary
            return summary
        except Exception:
            pass
    return agent.get_broad_summary()
