from __future__ import annotations
from datetime import datetime
from fastmcp import FastMCP
from app.config import MAIN_SERVER_PORT
from app.data.repository import DataRepository

# Initialize Logic
repo = DataRepository()

mcp = FastMCP(
    name="Mango Unified Server",
    instructions="Centralized server for Reporter, PPN, and OF tools.",
)

# --- Shared Tools ---
@mcp.tool(name="today", description="Get current date and time.")
def today() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# --- Reporter Tools ---
@mcp.tool(name="get_report", description="List all available report names.")
def get_report() -> list[str]:
    return repo.get_report_names()

@mcp.tool(name="get_report_columns", description="Get column names for a specific report.")
def get_report_columns(report_name: str) -> list[str]:
    return repo.get_report_columns(report_name)

@mcp.tool(name="read_report", description="Read data from a report. Optionally specify columns.")
def read_report(report_name: str, columns: list[str] | None = None) -> list[dict]:
    return repo.read_report(report_name, columns)

# --- PPN Tools ---
@mcp.tool(name="get_plan_columns", description="Get column names for PPN plan data.")
def get_plan_columns() -> list[str]:
    return repo.get_plan_columns()

@mcp.tool(name="get_plan", description="Search for project plan details by keyword.")
def get_plan(query: str) -> list[dict]:
    return repo.get_plan(query)

@mcp.tool(name="get_material_use", description="Get summary of material usage.")
def get_material_use() -> list[dict]:
    return repo.get_material_use()

# --- OF Tools ---
@mcp.tool(name="phase_structure", description="Parse expense text into JSON structure.")
def phase_structure(text: str) -> dict:
    return repo.phase_structure(text)

@mcp.tool(name="get_expense_code", description="Find expense code from description.")
def get_expense_code(description: str) -> list[dict]:
    return repo.get_expense_code(description)

def run() -> None:
    print(f"Starting Unified MCP Server on port {MAIN_SERVER_PORT}...")
    mcp.run(transport="http", host="127.0.0.1", port=MAIN_SERVER_PORT)

if __name__ == "__main__":
    run()