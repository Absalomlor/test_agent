from __future__ import annotations

import atexit
from typing import Dict, Optional

from mcp.client.streamable_http import streamablehttp_client
from strands import Agent
from strands.tools.mcp.mcp_client import MCPClient

from app.agents.message_utils import render_message
from app.config import AGENT_SETTINGS, AgentSettings, build_default_model
from app.telemetry.callbacks import build_agent_callback
from app.telemetry.log_store import AgentLogStore


class DomainAgent:
    def __init__(self, key: str, config: AgentSettings, log_store: AgentLogStore) -> None:
        self.key = key
        self.config = config
        self.log_store = log_store
        self._client = MCPClient(lambda: streamablehttp_client(config.server_url))
        self._client.__enter__()
        atexit.register(self._shutdown)
        tools = self._client.list_tools_sync()
        self.agent = Agent(
            system_prompt=config.system_prompt,
            tools=tools,
            model=build_default_model(),
            callback_handler=build_agent_callback(config.name, log_store),
        )

    def _shutdown(self) -> None:
        try:
            self._client.__exit__(None, None, None)
        except Exception:  # pragma: no cover - best effort cleanup
            pass

    def run(self, query: str, context: Optional[str] = None) -> str:
        payload = query if not context else f"{query}\n\nContext: {context}"
        self.log_store.add(self.config.name, "input", payload)
        try:
            result = self.agent(payload)
            message = getattr(result, "message", result)
            content = render_message(message)
            self.log_store.add(self.config.name, "output", content)
            return content
        except Exception as exc:  # pragma: no cover - depends on runtime
            self.log_store.add(self.config.name, "error", str(exc))
            raise


def build_domain_agents(log_store: AgentLogStore) -> Dict[str, DomainAgent]:
    return {key: DomainAgent(key, config, log_store) for key, config in AGENT_SETTINGS.items()}
