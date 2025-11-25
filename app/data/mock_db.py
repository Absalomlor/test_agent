from __future__ import annotations

import csv
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

from app.config import DB_PATH

BASE_DIR = Path(__file__).resolve().parents[2]
IC_CSV_PATH = BASE_DIR / "ic_data.csv"
PPN_CSV_PATH = BASE_DIR / "ppn_data.csv"

IC_SCHEMA = """
CREATE TABLE IF NOT EXISTS ic_inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pre_event TEXT,
    item_whcode TEXT,
    c_des1 TEXT,
    c_des2 TEXT,
    itemcode TEXT,
    proj_whcode TEXT,
    qtybal REAL,
    unitname TEXT,
    whcode TEXT
);
"""

PPN_SCHEMA = """
CREATE TABLE IF NOT EXISTS ppn_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cost_code TEXT,
    c_des1 TEXT,
    c_des2 TEXT,
    itemcode TEXT,
    pre_event TEXT,
    required_qty REAL,
    start_date TEXT,
    task_id TEXT,
    task_name TEXT,
    unit TEXT
);
"""


def _read_csv_rows(path: Path) -> List[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [dict(row) for row in reader]


def _to_float(value: str) -> float:
    try:
        return float(value.replace(",", "")) if value else 0.0
    except ValueError:
        return 0.0


def _normalize_str(value: str | None) -> str:
    return value.strip() if value else ""


def _convert_date(value: str | None) -> str:
    raw = _normalize_str(value)
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return raw


def _load_ic_rows() -> List[Tuple]:
    raw_rows = _read_csv_rows(IC_CSV_PATH)
    records: List[Tuple] = []
    for row in raw_rows:
        records.append(
            (
                _normalize_str(row.get("pre_event")),
                _normalize_str(row.get("item_whcode")),
                _normalize_str(row.get("c_des1")),
                _normalize_str(row.get("c_des2")),
                _normalize_str(row.get("itemcode")),
                _normalize_str(row.get("proj_whcode")),
                _to_float(_normalize_str(row.get("qtybal"))),
                _normalize_str(row.get("unitname")),
                _normalize_str(row.get("whcode")),
            )
        )
    return records


def _load_ppn_rows() -> List[Tuple]:
    raw_rows = _read_csv_rows(PPN_CSV_PATH)
    records: List[Tuple] = []
    for row in raw_rows:
        records.append(
            (
                _normalize_str(row.get("cost_code")),
                _normalize_str(row.get("material")),
                "",
                _normalize_str(row.get("material_code")),
                _normalize_str(row.get("project_id")),
                _to_float(_normalize_str(row.get("required_qty"))),
                _convert_date(row.get("start_date")),
                _normalize_str(row.get("task_id")),
                _normalize_str(row.get("task_name")),
                _normalize_str(row.get("unit")),
            )
        )
    return records


def _insert_many(conn: sqlite3.Connection, sql: str, rows: Sequence[Tuple]) -> None:
    conn.executemany(sql, rows)


def ensure_db(seed: bool = True) -> Path:
    """Ensure the SQLite database exists with mock data."""

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    initialize = not DB_PATH.exists()

    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(IC_SCHEMA)
        conn.executescript(PPN_SCHEMA)

        if initialize and seed:
            _insert_many(
                conn,
                """
                INSERT OR REPLACE INTO ic_inventory
                (pre_event, item_whcode, c_des1, c_des2, itemcode, proj_whcode, qtybal, unitname, whcode)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                _load_ic_rows(),
            )
            _insert_many(
                conn,
                """
                INSERT INTO ppn_plans
                (cost_code, c_des1, c_des2, itemcode, pre_event, required_qty, start_date, task_id, task_name, unit)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                _load_ppn_rows(),
            )
        conn.commit()

    return DB_PATH


if __name__ == "__main__":
    path = ensure_db()
    print(f"Mock DB ready at {path}")
