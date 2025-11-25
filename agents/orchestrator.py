from __future__ import annotations

from typing import Dict

from strands import Agent, tool

from app.agents.domain_agents import DomainAgent
from app.agents.message_utils import render_message
from app.config import COORDINATOR_PROMPT, build_default_model
from app.telemetry.callbacks import build_agent_callback
from app.telemetry.log_store import AgentLogStore


class Orchestrator:
    def __init__(self, domain_agents: Dict[str, DomainAgent], log_store: AgentLogStore) -> None:
        self.domain_agents = domain_agents
        self.log_store = log_store
        tools = [self._wrap_domain_agent(agent) for agent in domain_agents.values()]
        self.agent = Agent(
            system_prompt=COORDINATOR_PROMPT,
            tools=tools,
            model=build_default_model(),
            callback_handler=build_agent_callback("Orchestrator", log_store),
        )

    def _wrap_domain_agent(self, domain_agent: DomainAgent):
        @tool(name=domain_agent.config.tool_name, description=domain_agent.config.tool_description)
        def _delegate(query: str, context: str | None = None) -> str:
            return domain_agent.run(query, context)

        return _delegate

    def run(self, user_message: str) -> str:
        self.log_store.add("User", "input", user_message)
        result = self.agent(user_message)
        message = getattr(result, "message", result)
        content = render_message(message)
        self.log_store.add("Orchestrator", "output", content)
        return content
