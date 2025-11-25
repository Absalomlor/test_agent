from __future__ import annotations

from typing import Dict, List

from strands import Agent, tool

from app.agents.sub_agents import DomainAgent
from app.agents.message_utils import render_message
from app.config import COORDINATOR_PROMPT, build_default_model
from app.telemetry.callbacks import build_agent_callback
from app.telemetry.log_store import AgentLogStore


class Orchestrator:
    def __init__(self, domain_agents: Dict[str, DomainAgent], log_store: AgentLogStore) -> None:
        self.log_store = log_store
        
        # Refactor 1: แปลง Agent เป็น Tool ด้วยวิธีที่อ่านง่ายขึ้น
        # เราเปลี่ยนจากการเรียกฟังก์ชันซ้อนๆ กันมาใช้ List Comprehension ที่ชัดเจน
        tools = [self._as_tool(agent) for agent in domain_agents.values()]

        self.agent = Agent(
            system_prompt=COORDINATOR_PROMPT,
            tools=tools,
            model=build_default_model(),
            callback_handler=build_agent_callback("Orchestrator", log_store),
        )

    def _as_tool(self, domain_agent: DomainAgent):
        """
        Helper function เพื่อแปลง DomainAgent ให้เป็น Tool ที่ Strands เข้าใจ
        โดยดึง Metadata (name, description) มาจาก config ของ Agent โดยตรง
        """
        @tool(name=domain_agent.config.tool_name, description=domain_agent.config.tool_description)
        def agent_wrapper(query: str, context: str | None = None) -> str:
            # Delegate การทำงานไปที่ DomainAgent.run โดยตรง
            return domain_agent.run(query, context)
        
        return agent_wrapper

    def run(self, user_message: str) -> str:
        # บันทึก Input (ในอนาคตเราสามารถย้ายไปทำใน Callback ได้เพื่อให้โค้ดส่วนนี้ Clean ขึ้น)
        self.log_store.add("User", "input", user_message)
        
        # เรียกใช้งาน Agent หลัก
        result = self.agent(user_message)
        
        # แปลงผลลัพธ์ให้อยู่ในรูปแบบข้อความ (String)
        content = render_message(result)
        
        # บันทึก Output
        self.log_store.add("Orchestrator", "output", content)
        
        return content