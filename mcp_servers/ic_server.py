from __future__ import annotations

from fastmcp import FastMCP

from app.config import IC_SERVER_PORT
from app.data.repository import InventoryRepository

inventory_repo = InventoryRepository()

mcp = FastMCP(
    name="IC Warehouse Server",
    instructions=(
        "Tools for querying the IC warehouse mock DB."
        " Use them to answer stock, material code, and warehouse balance questions."
    ),
)


@mcp.tool(name="get_material", description="Search materials in the IC warehouse database")
def get_material(
    project_id: str | None = None,
    text_query: str | None = None,
    itemcode: str | None = None,
    whcode: str | None = None,
    limit: int = 25,
) -> list[dict]:
    """Return materials that match any of the provided filters."""

    return inventory_repo.search_materials(
        project_id=project_id,
        text_query=text_query,
        itemcode=itemcode,
        whcode=whcode,
        limit=limit,
    )


@mcp.tool(name="low_materrial", description="List materials with quantity below the threshold")
def low_materrial(
    threshold: float,
    project_id: str | None = None,
    whcode: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """Return inventory records where qtybal is below the provided threshold."""

    return inventory_repo.low_stock(
        threshold=threshold,
        project_id=project_id,
        whcode=whcode,
        limit=limit,
    )


def run() -> None:
    mcp.run(transport="http", host="127.0.0.1", port=IC_SERVER_PORT)


if __name__ == "__main__":
    run()
