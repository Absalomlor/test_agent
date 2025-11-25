from __future__ import annotations

from app.agents.domain_agents import DomainAgent, build_domain_agents
from app.agents.orchestrator import Orchestrator
from app.telemetry.log_store import AgentLogStore


class AgentRuntime:
    def __init__(self, log_store: AgentLogStore | None = None) -> None:
        self.log_store = log_store or AgentLogStore()
        self.domain_agents: dict[str, DomainAgent] = build_domain_agents(self.log_store)
        self.orchestrator = Orchestrator(self.domain_agents, self.log_store)

    def handle(self, user_message: str) -> str:
        return self.orchestrator.run(user_message)

    def logs(self) -> list[dict[str, str]]:
        return self.log_store.as_dicts()

    def reset_logs(self) -> None:
        self.log_store.clear()

