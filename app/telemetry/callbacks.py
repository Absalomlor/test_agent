from __future__ import annotations

from typing import Any, Dict, Set

from app.telemetry.log_store import AgentLogStore


def build_agent_callback(agent_name: str, log_store: AgentLogStore):
    """Capture streaming events emitted by Strands agents."""

    seen_tools: Set[str] = set()

    def handler(**kwargs: Dict[str, Any]) -> None:
        if "data" in kwargs:
            chunk = kwargs["data"].strip()
            if chunk:
                log_store.add(agent_name, "process", chunk)
        elif "current_tool_use" in kwargs:
            tool = kwargs["current_tool_use"]
            tool_id = tool.get("toolUseId")
            if tool_id and tool_id not in seen_tools:
                seen_tools.add(tool_id)
                log_store.add(
                    agent_name,
                    "tool",
                    f"Calling tool {tool.get('name')}",
                    payload={"tool": tool},
                )

    return handler

