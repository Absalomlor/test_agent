from __future__ import annotations

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
        
        # Initialize MCP Client
        # เราเปิด connection แบบ Explicit แต่ลบ atexit ออกเพื่อให้ Runtime เป็นผู้จัดการ
        self._client = MCPClient(lambda: streamablehttp_client(config.server_url))
        self._client.__enter__()
        
        # ดึง Tools แบบ Synchronous (เพิ่ม Error Handling เพื่อความปลอดภัย)
        try:
            tools = self._client.list_tools_sync()
        except Exception as e:
            print(f"Warning: Could not list tools for {key} at {config.server_url}: {e}")
            tools = []

        self.agent = Agent(
            system_prompt=config.system_prompt,
            tools=tools,
            model=build_default_model(),
            callback_handler=build_agent_callback(config.name, log_store),
        )

    def close(self) -> None:
        """
        สั่งปิด MCP Client Connection อย่างถูกวิธี
        Runtime ควรเรียกใช้ฟังก์ชันนี้เมื่อจบการทำงาน
        """
        try:
            self._client.__exit__(None, None, None)
        except Exception:
            pass

    def run(self, query: str, context: Optional[str] = None) -> str:
        payload = query if not context else f"{query}\n\nContext: {context}"
        
        # บันทึก Input (Process Log)
        self.log_store.add(self.config.name, "input", payload)
        
        try:
            # ใช้ render_message ตัวใหม่ที่แก้ไปแล้ว
            result = self.agent(payload)
            content = render_message(result)
            
            # บันทึก Output
            self.log_store.add(self.config.name, "output", content)
            return content
        except Exception as exc:
            self.log_store.add(self.config.name, "error", str(exc))
            raise

def build_domain_agents(log_store: AgentLogStore) -> Dict[str, DomainAgent]:
    return {key: DomainAgent(key, config, log_store) for key, config in AGENT_SETTINGS.items()}