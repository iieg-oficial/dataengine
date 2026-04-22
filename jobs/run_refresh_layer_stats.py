import json
import os
import sys
from datetime import datetime

from sqlalchemy import create_engine, text

from core.utils.logger import Logger


STATS_OPERATIONS = {'count', 'count_distinct', 'count_where', 'sum', 'avg', 'min', 'max', 'latest'}


def _is_identifier(value) -> bool:
    if not value or not isinstance(value, str):
        return False
    if len(value) > 100:
        return False
    return all(c.isalnum() or c == '_' for c in value)


def _build_query(cfg: dict) -> tuple[str, dict] | None:
    op = cfg.get('operation')
    if op not in STATS_OPERATIONS:
        return None
    schema = cfg.get('schema')
    table = cfg.get('table')
    if not (_is_identifier(schema) and _is_identifier(table)):
        return None

    field = cfg.get('field')
    where_field = cfg.get('where_field')
    where_value = cfg.get('where_value')
    order_field = cfg.get('order_field')

    if op != 'count' and not _is_identifier(field):
        return None
    if where_field and not _is_identifier(where_field):
        return None
    if order_field and not _is_identifier(order_field):
        return None

    fqtn = f'"{schema}"."{table}"'
    params: dict = {}

    if op == 'count':
        sql = f'SELECT COUNT(*) FROM {fqtn}'
    elif op == 'count_distinct':
        sql = f'SELECT COUNT(DISTINCT "{field}") FROM {fqtn}'
    elif op == 'count_where':
        if not where_field or where_value is None:
            return None
        sql = f'SELECT COUNT(*) FROM {fqtn} WHERE "{where_field}" = :where_value'
        params['where_value'] = where_value
    elif op == 'sum':
        sql = f'SELECT SUM("{field}") FROM {fqtn}'
    elif op == 'avg':
        sql = f'SELECT AVG("{field}") FROM {fqtn}'
    elif op == 'min':
        sql = f'SELECT MIN("{field}") FROM {fqtn}'
    elif op == 'max':
        sql = f'SELECT MAX("{field}") FROM {fqtn}'
    elif op == 'latest':
        if not order_field:
            return None
        sql = f'SELECT "{field}" FROM {fqtn} ORDER BY "{order_field}" DESC LIMIT 1'
    else:
        return None
    return sql, params


def main() -> int:
    url = _build_url()
    if not url:
        Logger.error('DATAENGINE connection no configurada')
        return 1

    engine = create_engine(url)
    try:
        with engine.begin() as conn:
            rows = conn.execute(text(
                "SELECT layer_key, stats_config FROM mapalab.layer_stats "
                "WHERE stats_config IS NOT NULL AND jsonb_array_length(stats_config) > 0"
            )).fetchall()

            if not rows:
                Logger.info('📊  No hay stats_config — nada que refrescar')
                return 0

            updated = skipped = failed = 0
            for row in rows:
                layer_key = row[0]
                stats_config = row[1] or []
                values = []
                had_error = False

                for cfg in stats_config:
                    if not isinstance(cfg, dict):
                        continue
                    built = _build_query(cfg)
                    if built is None:
                        Logger.warning(f'   [{layer_key}] pos={cfg.get("position")}: config invalida, skip')
                        had_error = True
                        continue
                    sql, params = built
                    try:
                        result = conn.execute(text(sql), params).scalar()
                    except Exception as exc:
                        Logger.warning(f'   [{layer_key}] pos={cfg.get("position")}: query fallo: {exc}')
                        had_error = True
                        continue

                    values.append({
                        'posicion': cfg.get('position'),
                        'nombre': cfg.get('label'),
                        'simbolo': cfg.get('symbol'),
                        'valor': str(result) if result is not None else None,
                    })

                if had_error and not values:
                    failed += 1
                    continue
                if not values:
                    skipped += 1
                    continue

                conn.execute(
                    text("""
                        UPDATE mapalab.layer_stats
                        SET values = CAST(:values AS jsonb),
                            values_refreshed_at = :now
                        WHERE layer_key = :layer_key
                    """),
                    {'values': json.dumps(values), 'now': datetime.utcnow(), 'layer_key': layer_key},
                )
                updated += 1

        Logger.info(f'✅  layer_stats: updated={updated}, skipped={skipped}, failed={failed}')
        return 0
    except Exception as exc:
        Logger.error(f'❌  Refresh stats fallo: {exc}')
        return 1
    finally:
        engine.dispose()


def _build_url() -> str | None:
    direct = os.getenv('DATAENGINE_URL')
    if direct:
        return direct
    user = os.getenv('MAPALAB_STATS_DB_USER') or os.getenv('DATAENGINE_DB_USER')
    pwd = os.getenv('MAPALAB_STATS_DB_PASSWORD') or os.getenv('DATAENGINE_DB_PASSWORD')
    host = os.getenv('DATAENGINE_DB_HOST')
    port = os.getenv('DATAENGINE_DB_PORT', '5432')
    db = os.getenv('DATAENGINE_DB_NAME')
    sslmode = os.getenv('DATAENGINE_DB_SSLMODE', 'require')
    if not (user and pwd and host and db):
        return None
    return f'postgresql://{user}:{pwd}@{host}:{port}/{db}?sslmode={sslmode}'


if __name__ == '__main__':
    sys.exit(main())
