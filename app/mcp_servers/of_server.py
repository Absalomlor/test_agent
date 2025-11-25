from __future__ import annotations

from datetime import date
from typing import Optional

from fastmcp import FastMCP

from app.config import OF_SERVER_PORT
from app.data.repository import InventoryRepository

inventory_repo = InventoryRepository()

mcp = FastMCP(
    name="Operations Finance Server",
    instructions="Generate petty cash and purchase request forms with structured payloads.",
)


def _iso_today() -> str:
    return date.today().isoformat()


@mcp.tool(name="pretty_cash_fillform", description="Prepare a petty cash form payload")
def pretty_cash_fillform(
    amount: float,
    description: str,
    request_date: Optional[str] = None,
) -> dict:
    payload = {
        "form": "petty_cash",
        "request_date": request_date or _iso_today(),
        "amount": amount,
        "description": description,
    }
    return {"status": "ready", "payload": payload}


@mcp.tool(name="pr_fillform", description="Prepare a purchase request form")
def pr_fillform(
    material_name: str,
    quantity: float,
    material_code: Optional[str] = None,
    request_date: Optional[str] = None,
    unit: Optional[str] = None,
) -> dict:
    resolved_code = material_code
    resolved_unit = unit

    if not resolved_code or not resolved_unit:
        match = inventory_repo.get_material_by_keyword(material_name)
        if match:
            resolved_code = resolved_code or match["itemcode"]
            resolved_unit = resolved_unit or match.get("unitname")

    payload = {
        "form": "purchase_request",
        "request_date": request_date or _iso_today(),
        "material_name": material_name,
        "material_code": resolved_code,
        "quantity": quantity,
        "unit": resolved_unit,
    }

    return {
        "status": "ready" if resolved_code else "missing_material_code",
        "payload": payload,
        "resolution_hint": None if resolved_code else "Call get_material in IC server to confirm the code.",
    }


def run() -> None:
    mcp.run(transport="http", host="127.0.0.1", port=OF_SERVER_PORT)


if __name__ == "__main__":
    run()

