from __future__ import annotations

from Agent.agent import Agent


def get_policy_llm(agent: Agent):
    """
    Retrieve the policy LLM helper for the agent, creating it on demand.
    """
    return agent.policy_llm
