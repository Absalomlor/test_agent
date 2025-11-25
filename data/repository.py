from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import DB_PATH
from app.data.mock_db import ensure_db


class BaseRepository:
    def __init__(self, db_path: Path = DB_PATH) -> None:
        ensure_db()
        self.db_path = db_path

    def _query(self, sql: str, params: tuple[Any, ...]) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]


class InventoryRepository(BaseRepository):
    def search_materials(
        self,
        project_id: Optional[str] = None,
        text_query: Optional[str] = None,
        itemcode: Optional[str] = None,
        whcode: Optional[str] = None,
        limit: int = 25,
    ) -> List[Dict[str, Any]]:
        clauses = []
        params: list[Any] = []

        if project_id:
            clauses.append("pre_event = ?")
            params.append(project_id)
        if itemcode:
            clauses.append("itemcode = ?")
            params.append(itemcode)
        if whcode:
            clauses.append("whcode = ?")
            params.append(whcode)
        if text_query:
            like = f"%{text_query.lower()}%"
            clauses.append("(lower(c_des1) LIKE ? OR lower(c_des2) LIKE ? OR lower(itemcode) LIKE ?)")
            params.extend([like, like, like])

        where_sql = " AND ".join(clauses) if clauses else "1=1"
        sql = f"SELECT * FROM ic_inventory WHERE {where_sql} ORDER BY qtybal DESC LIMIT ?"
        params.append(limit)
        return self._query(sql, tuple(params))

    def low_stock(
        self,
        threshold: float,
        project_id: Optional[str] = None,
        whcode: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        clauses = ["qtybal <= ?"]
        params: list[Any] = [threshold]

        if project_id:
            clauses.append("pre_event = ?")
            params.append(project_id)
        if whcode:
            clauses.append("whcode = ?")
            params.append(whcode)

        sql = (
            "SELECT * FROM ic_inventory WHERE " + " AND ".join(clauses) + " ORDER BY qtybal ASC LIMIT ?"
        )
        params.append(limit)
        return self._query(sql, tuple(params))

    def get_material_by_keyword(self, keyword: str) -> Optional[Dict[str, Any]]:
        rows = self.search_materials(text_query=keyword, limit=1)
        return rows[0] if rows else None


class PlanRepository(BaseRepository):
    def get_plan(
        self,
        project_id: Optional[str] = None,
        task_id: Optional[str] = None,
        cost_code: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        clauses = []
        params: list[Any] = []

        if project_id:
            clauses.append("pre_event = ?")
            params.append(project_id)
        if task_id:
            clauses.append("task_id = ?")
            params.append(task_id)
        if cost_code:
            clauses.append("cost_code = ?")
            params.append(cost_code)

        where_sql = " AND ".join(clauses) if clauses else "1=1"
        sql = f"SELECT * FROM ppn_plans WHERE {where_sql} ORDER BY start_date LIMIT ?"
        params.append(limit)
        return self._query(sql, tuple(params))

    def get_material_usage(
        self,
        project_id: str,
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        clauses = ["pre_event = ?"]
        params: list[Any] = [project_id]

        if task_id:
            clauses.append("task_id = ?")
            params.append(task_id)

        where_sql = " AND ".join(clauses)
        detail_sql = f"SELECT * FROM ppn_plans WHERE {where_sql} ORDER BY task_id"
        detail = self._query(detail_sql, tuple(params))

        total_qty = sum(row["required_qty"] for row in detail)
        material_breakdown: Dict[str, float] = {}
        for row in detail:
            material_breakdown[row["itemcode"]] = material_breakdown.get(row["itemcode"], 0) + row["required_qty"]

        return {
            "project_id": project_id,
            "task_id": task_id,
            "total_required_qty": total_qty,
            "materials": material_breakdown,
            "detail": detail,
        }


def get_repositories() -> tuple[InventoryRepository, PlanRepository]:
    inventory = InventoryRepository()
    plan = PlanRepository()
    return inventory, plan

