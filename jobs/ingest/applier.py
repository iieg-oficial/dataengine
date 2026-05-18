import json
from typing import Any

from sqlalchemy.engine import Connection
from sqlalchemy import text

from .columns import BOOL_COLUMNS, JSONB_COLUMNS, PK_COLUMN


def _coerce(col: str, value: Any) -> Any:
    if col in JSONB_COLUMNS and value is not None:
        return json.dumps(value, ensure_ascii=False)
    return value


def _placeholder(col: str) -> str:
    if col in JSONB_COLUMNS:
        return f"CAST(:{col} AS jsonb)"
    return f":{col}"


def _expected_placeholder(col: str) -> str:
    if col in JSONB_COLUMNS:
        return f"CAST(:_expected_{col} AS jsonb)"
    return f":_expected_{col}"


def _apply_insert(conn: Connection, change: dict, updated_by: str) -> str:
    values = dict(change["values"])
    values[PK_COLUMN] = change[PK_COLUMN]
    values["updated_by"] = updated_by

    cols = list(values.keys())
    placeholders = ", ".join(_placeholder(c) if c != "updated_by" else ":updated_by" for c in cols)
    col_list = ", ".join(cols)
    payload = {c: _coerce(c, v) for c, v in values.items()}

    sql = text(
        f"INSERT INTO mapalab.layer_metadata ({col_list}) VALUES ({placeholders}) "
        f"ON CONFLICT ({PK_COLUMN}) DO NOTHING"
    )
    result = conn.execute(sql, payload)
    return "inserted" if (result.rowcount or 0) > 0 else "conflict"


def _apply_update(conn: Connection, change: dict, updated_by: str) -> tuple[int, int]:
    approved = [d for d in change["diffs"] if d.get("apply", False)]
    if not approved:
        return (0, 0)

    set_clauses = []
    where_clauses = [f"{PK_COLUMN} = :_pk"]
    payload: dict[str, Any] = {"_pk": change[PK_COLUMN], "updated_by": updated_by}

    for d in approved:
        col = d["column"]
        set_clauses.append(f"{col} = {_placeholder(col)}")
        payload[col] = _coerce(col, d["to"])
        where_clauses.append(f"{col} IS NOT DISTINCT FROM {_expected_placeholder(col)}")
        payload[f"_expected_{col}"] = _coerce(col, d["from"])

    set_clauses.append("updated_by = :updated_by")
    set_clauses.append("updated_at = NOW()")

    sql = text(
        "UPDATE mapalab.layer_metadata SET "
        + ", ".join(set_clauses)
        + " WHERE "
        + " AND ".join(where_clauses)
    )
    result = conn.execute(sql, payload)
    affected = result.rowcount or 0
    return (len(approved), affected)


def apply_plan(conn: Connection, plan: dict) -> dict:
    updated_by = f"ingest:{plan['dependencia']}:{plan['source']}"[:100]

    inserts_ok = 0
    inserts_conflict = 0
    updates_applied = 0
    updates_columns = 0
    updates_conflict = 0
    skipped = 0

    for change in plan["changes"]:
        if change["op"] == "insert":
            if not change.get("apply", True):
                skipped += 1
                continue
            status = _apply_insert(conn, change, updated_by)
            if status == "inserted":
                inserts_ok += 1
            else:
                inserts_conflict += 1
        elif change["op"] == "update":
            cols_approved, affected = _apply_update(conn, change, updated_by)
            if cols_approved == 0:
                skipped += 1
                continue
            updates_columns += cols_approved
            if affected > 0:
                updates_applied += 1
            else:
                updates_conflict += 1

    return {
        "inserts_applied": inserts_ok,
        "inserts_conflict": inserts_conflict,
        "updates_applied": updates_applied,
        "updates_columns_changed": updates_columns,
        "updates_conflict": updates_conflict,
        "changes_skipped": skipped,
        "updated_by": updated_by,
    }
