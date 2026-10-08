import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.utils.secretos import leer_secreto

from sqlalchemy import create_engine

from ingest.applier import apply_plan
from ingest.columns import unknown_columns
from ingest.planner import build_plan, summarize
from ingest.reader import read_csv


def _build_url() -> str | None:
    direct = os.getenv("DATAENGINE_URL")
    if direct:
        return direct
    user = os.getenv("DATAENGINE_DB_USER")
    pwd = leer_secreto("DATAENGINE_DB_PASSWORD")
    host = os.getenv("DATAENGINE_DB_HOST")
    port = os.getenv("DATAENGINE_DB_PORT", "5432")
    db = os.getenv("DATAENGINE_DB_NAME")
    sslmode = os.getenv("DATAENGINE_DB_SSLMODE", "require")
    if not (user and pwd and host and db):
        return None
    return f"postgresql://{user}:{pwd}@{host}:{port}/{db}?sslmode={sslmode}"


def _review_plan_interactive(plan: dict) -> dict:
    if not sys.stdin.isatty():
        print("[ingest] --review requiere TTY interactivo", file=sys.stderr)
        sys.exit(2)

    for change in plan["changes"]:
        key = change[plan["pk_column"]]
        if change["op"] == "insert":
            print(f"\n[INSERT] {key}")
            for k, v in change["values"].items():
                print(f"    {k} = {v}")
            ans = input("Aplicar? [y/N]: ").strip().lower()
            change["apply"] = ans == "y"
        else:
            print(f"\n[UPDATE] {key}")
            for d in change["diffs"]:
                print(f"    {d['column']}:")
                print(f"        from: {d['from']}")
                print(f"        to:   {d['to']}")
                ans = input("    Aplicar este cambio? [y/N]: ").strip().lower()
                d["apply"] = ans == "y"
    return plan


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ingesta de metadatos a mapalab.layer_metadata desde CSV"
    )
    parser.add_argument("--dependencia", help="Nombre logico de la dependencia origen")
    parser.add_argument("--source", help="Path local o URL al CSV")
    parser.add_argument("--plan-out", help="Guarda el plan generado en este archivo JSON")
    parser.add_argument("--plan-in", help="Lee un plan previamente generado")
    parser.add_argument("--review", action="store_true", help="Revision interactiva TTY")
    parser.add_argument("--apply", action="store_true", help="Aplica los cambios (sin esto = dry-run)")
    args = parser.parse_args()

    if not args.plan_in and not args.source:
        parser.error("Se requiere --source o --plan-in")
    if not args.plan_in and not args.dependencia:
        parser.error("--dependencia es obligatorio cuando se usa --source")

    url = _build_url()
    if not url:
        print("ERROR: configurar DATAENGINE_URL o DATAENGINE_DB_*", file=sys.stderr)
        return 1

    engine = create_engine(url)

    try:
        if args.plan_in:
            with open(args.plan_in, encoding="utf-8") as f:
                plan = json.load(f)
            print(f"[ingest] plan leido: {args.plan_in}")
        else:
            headers, rows = read_csv(args.source)
            unknown = unknown_columns(headers)
            if unknown:
                print(f"ERROR: columnas no reconocidas en el CSV: {unknown}", file=sys.stderr)
                return 2
            with engine.connect() as conn:
                plan = build_plan(conn, args.dependencia, args.source, rows)

        print(summarize(plan))

        if args.review:
            plan = _review_plan_interactive(plan)

        if args.plan_out:
            with open(args.plan_out, "w", encoding="utf-8") as f:
                json.dump(plan, f, ensure_ascii=False, indent=2, default=str)
            print(f"[ingest] plan guardado: {args.plan_out}")

        if not args.apply:
            print("[ingest] DRY-RUN — usa --apply para escribir")
            return 0

        with engine.begin() as conn:
            result = apply_plan(conn, plan)

        print(
            f"[ingest] OK — inserts: {result['inserts_applied']} "
            f"(conflict {result['inserts_conflict']}), "
            f"updates: {result['updates_applied']} "
            f"({result['updates_columns_changed']} cols, conflict {result['updates_conflict']}), "
            f"skipped: {result['changes_skipped']}"
        )
        print(f"[ingest] updated_by: {result['updated_by']}")
        return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
