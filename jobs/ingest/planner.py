import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.engine import Connection
from sqlalchemy import text

from .columns import (
    BOOL_COLUMNS,
    JSONB_COLUMNS,
    PK_COLUMN,
    SCALAR_COLUMNS,
    normalize_row,
)


MERGEABLE_COLUMNS = (
    *(c for c in SCALAR_COLUMNS if c != PK_COLUMN),
    *JSONB_COLUMNS,
    *BOOL_COLUMNS,
)


def _normalize_for_compare(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True, ensure_ascii=False)
    return value


def _fetch_existing(conn: Connection, layer_keys: list[str]) -> dict[str, dict]:
    if not layer_keys:
        return {}
    cols = ", ".join((PK_COLUMN, *MERGEABLE_COLUMNS))
    result = conn.execute(
        text(f"SELECT {cols} FROM mapalab.layer_metadata WHERE {PK_COLUMN} = ANY(:keys)"),
        {"keys": layer_keys},
    ).mappings().all()
    return {row[PK_COLUMN]: dict(row) for row in result}


def build_plan(
    conn: Connection,
    dependencia: str,
    source_label: str,
    rows: list[dict],
) -> dict:
    normalized: list[dict] = []
    seen: set[str] = set()
    duplicates: list[str] = []
    missing_pk = 0

    for raw in rows:
        norm = normalize_row(raw)
        key = norm.get(PK_COLUMN)
        if not key:
            missing_pk += 1
            continue
        if key in seen:
            duplicates.append(key)
            continue
        seen.add(key)
        normalized.append(norm)

    existing = _fetch_existing(conn, list(seen))

    changes: list[dict] = []
    for norm in normalized:
        key = norm[PK_COLUMN]
        current = existing.get(key)
        if current is None:
            values = {k: v for k, v in norm.items() if v is not None}
            changes.append({
                "op": "insert",
                PK_COLUMN: key,
                "values": values,
                "apply": True,
            })
            continue

        diffs = []
        for col in MERGEABLE_COLUMNS:
            new_val = norm.get(col)
            if new_val is None:
                continue
            old_val = current.get(col)
            if _normalize_for_compare(new_val) == _normalize_for_compare(old_val):
                continue
            diffs.append({
                "column": col,
                "from": old_val,
                "to": new_val,
                "apply": True,
            })

        if diffs:
            changes.append({
                "op": "update",
                PK_COLUMN: key,
                "diffs": diffs,
            })

    return {
        "version": 1,
        "dependencia": dependencia,
        "source": source_label,
        "target_table": "mapalab.layer_metadata",
        "pk_column": PK_COLUMN,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "stats": {
            "rows_in_source": len(rows),
            "rows_with_pk": len(normalized) + len(duplicates),
            "rows_unique": len(normalized),
            "rows_missing_pk": missing_pk,
            "rows_duplicate_pk": len(duplicates),
            "inserts": sum(1 for c in changes if c["op"] == "insert"),
            "updates": sum(1 for c in changes if c["op"] == "update"),
        },
        "duplicates_skipped": duplicates,
        "changes": changes,
    }


def summarize(plan: dict) -> str:
    s = plan["stats"]
    lines = [
        f"[ingest] dependencia: {plan['dependencia']}",
        f"[ingest] fuente: {plan['source']}",
        f"[ingest] filas en archivo: {s['rows_in_source']}",
        f"[ingest]   con PK: {s['rows_with_pk']}, sin PK: {s['rows_missing_pk']}, duplicadas: {s['rows_duplicate_pk']}",
        f"[ingest] cambios propuestos: {s['inserts']} insert, {s['updates']} update",
    ]
    return "\n".join(lines)
