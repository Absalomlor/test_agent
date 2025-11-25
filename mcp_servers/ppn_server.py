from __future__ import annotations

from fastmcp import FastMCP

from app.config import PPN_SERVER_PORT
from app.data.repository import PlanRepository

plan_repo = PlanRepository()

mcp = FastMCP(
    name="PPN Planning Server",
    instructions="Tools for querying mock project plans, tasks, and material usage.",
)


@mcp.tool(name="get_plan", description="Retrieve plan tasks filtered by project, task, or cost code")
def get_plan(
    project_id: str | None = None,
    task_id: str | None = None,
    cost_code: str | None = None,
    limit: int = 50,
) -> list[dict]:
    return plan_repo.get_plan(project_id=project_id, task_id=task_id, cost_code=cost_code, limit=limit)


@mcp.tool(name="get_material_use", description="Summarize material usage for a project or task")
def get_material_use(project_id: str, task_id: str | None = None) -> dict:
    return plan_repo.get_material_usage(project_id=project_id, task_id=task_id)


def run() -> None:
    mcp.run(transport="http", host="127.0.0.1", port=PPN_SERVER_PORT)


if __name__ == "__main__":
    run()

