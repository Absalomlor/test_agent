from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

from dotenv import load_dotenv
from strands.models import BedrockModel

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
load_dotenv(PROJECT_ROOT / ".env")

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# CSV File Paths 
AGING_REPORT_PATH = DATA_DIR / "Aging Stock Balance by Material.csv"
ACTUAL_COST_PATH = DATA_DIR / "Export Actual Cost.xlsx - Excel Worksheet.csv"
EXPENSE_CODE_PATH = DATA_DIR / "ap_expensother.csv"
PPN_DATA_PATH = DATA_DIR / "ppn_data.csv"

# Server Configuration
MAIN_SERVER_PORT = 8101

DEFAULT_MODEL_ID = os.getenv("STRANDS_MODEL_ID", "anthropic.claude-sonnet-4-20250514-v1:0")
DEFAULT_REGION = os.getenv("BEDROCK_REGION") or os.getenv("AWS_REGION", "us-west-2")
DEFAULT_TEMPERATURE = float(os.getenv("STRANDS_MODEL_TEMPERATURE", "0.2"))

def mcp_url(port: int) -> str:
    return f"http://127.0.0.1:{port}/mcp/"

@dataclass(frozen=True)
class AgentSettings:
    name: str
    tool_name: str
    tool_description: str
    system_prompt: str
    server_port: int

    @property
    def server_url(self) -> str:
        return mcp_url(self.server_port)

AGENT_SETTINGS: Dict[str, AgentSettings] = {
    # 1. Reporter Agent (ปรับ Prompt ให้เช็ค Column ก่อนเสมอ)
    "reporter_agent": AgentSettings(
        name="Reporter",
        tool_name="reporter_agent",
        tool_description="Agent for generating reports from aging stock and actual cost data.",
        system_prompt=("""
            SYSTEM ROLE: Reporter Agent.
            OBJECTIVE: Analyze business reports (Aging Stock, Actual Cost) based on user queries.
            
            WORKFLOW (MUST FOLLOW STRICTLY):
            1. **Identify Report**: Decide which report is relevant (Aging Stock or Actual Cost).
            2. **Inspect Structure**: Call 'get_report_columns' for that report to understand available fields.
               (DO NOT guess column names. Always check first.)
            3. **Fetch Data**: Call 'read_report'.
               - If the user asks for specific fields, pass them in the 'columns' argument.
               - If general, fetch default columns.
            4. **Analyze**: Summarize the returned data in Thai. Highlight key figures like Total Quantity or High Cost items.
            
            OUTPUT RULES:
            - Provide a professional summary in Thai.
            - If data is empty, state clearly that no records were found.
        """),
        server_port=MAIN_SERVER_PORT,
    ),

    # 2. PPN Agent (ปรับ Prompt ให้เลือก Tool ให้ถูกระหว่าง Search กับ Summary)
    "ppn_agent": AgentSettings(
        name="PPN Planner",
        tool_name="ppn_agent",
        tool_description="Agent for project planning and material usage tracking.",
        system_prompt=("""
            SYSTEM ROLE: PPN Planning Agent.
            OBJECTIVE: Provide insights on project tasks and material requirements.
            
            WORKFLOW (MUST FOLLOW STRICTLY):
            1. **Analyze Intent**:
               - If the user asks about a specific project/task/activity -> You need 'get_plan'.
               - If the user asks for "Total Usage", "Material Summary", or "How much material used" -> You need 'get_material_use'.
            2. **Execute Tool**: Call the appropriate tool identified in Step 1.
               - For 'get_plan', use the user's keyword as the query.
            3. **Synthesize**:
               - For Plans: List the tasks found, start dates, and status.
               - For Materials: Present a summary table or list of materials and their total required quantities.
            
            OUTPUT RULES:
            - Report findings in Thai.
            - Format lists clearly (e.g., bullet points).
        """),
        server_port=MAIN_SERVER_PORT,
    ),

    # 3. OF Agent (อันเดิมที่ดีอยู่แล้ว)
    "of_agent": AgentSettings(
        name="Operations Finance",
        tool_name="of_agent",
        tool_description="Agent for processing expenses into a structured JSON format.",
        system_prompt=("""
            SYSTEM ROLE: Operations Finance (OF) Agent.
            OBJECTIVE: Convert user text into a strict JSON format with a valid expense code.
            
            WORKFLOW (MUST FOLLOW STRICTLY):
            1. Receive input text.
            2. Call tool 'phase_structure' to get the initial JSON template.
               (The 'expense_code' field will initially contain an instruction text).
            3. Call tool 'get_expense_code' using the description to find the matching code (e.g., 'A0111').
            4. **CRITICAL STEP**: UPDATE the JSON from Step 2 by replacing the 'expense_code' value with the actual code found in Step 3.
            
            OUTPUT RULES:
            - DO NOT explain the steps.
            - DO NOT output the code alone.
            - YOUR FINAL ANSWER MUST BE ONLY THE COMPLETE JSON OBJECT.
        """),
        server_port=MAIN_SERVER_PORT,
    ),
}

COORDINATOR_PROMPT = ("""
    SYSTEM NAME: Mango Orchestrator.
    MISSION: Route user requests to the correct specialist:
    - Reporter: For stock aging or cost reports.
    - PPN: For project plans and material usage.
    - OF: For processing expenses and finding expense codes.
    
    Coordinate the results and answer in Thai.
""")

def build_default_model() -> BedrockModel:
    return BedrockModel(
        model_id=DEFAULT_MODEL_ID,
        region_name=DEFAULT_REGION,
        temperature=DEFAULT_TEMPERATURE,
    )