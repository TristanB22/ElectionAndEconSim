from __future__ import annotations

from typing import Any, Dict, Tuple

from Agent.models import AgentDTO
from Agent.modules.personal_summary import PersonalSummaryGenerator
from ._shared import build_agent_from_dto


def generate_personal_summary(dto: AgentDTO) -> Tuple[str, str, Dict[str, Any]]:
    """
    Generate a personal summary using the standard LLM pipeline.

    Returns:
        Tuple[str, str, Dict[str, any]]: (summary, reasoning, metadata)

    Raises:
        RuntimeError: if the LLM call fails.
    """
    agent = build_agent_from_dto(dto)
    generator = PersonalSummaryGenerator()
    summary, reasoning, metadata = generator.create_llm_summary(agent)
    if not summary or summary == "LLM API not available":
        raise RuntimeError(f"Failed to generate LLM summary for agent {dto.agent_id}")
    return summary, reasoning, metadata
