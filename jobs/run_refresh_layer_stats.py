import json
import os
import sys
from datetime import datetime, timezone

from sqlalchemy import create_engine, text

from core.utils.logger import Logger


PRIMITIVE_OPERATIONS = {'count', 'count_distinct', 'count_where', 'sum', 'avg', 'min', 'max', 'latest'}
COMBINATOR_OPS = {'add', 'sub', 'mul', 'div', 'percent', 'percent_change'}
STATS_OPERATIONS = PRIMITIVE_OPERATIONS | {'formula', 'static'}
MAX_EXPRESSION_DEPTH = 6


def _is_identifier(value) -> bool:
    if not value or not isinstance(value, str):
        return False
    if len(value) > 100:
        return False
    return all(c.isalnum() or c == '_' for c in value)


def _build_query(cfg: dict) -> tuple[str, dict] | None:
    op = cfg.get('operation')
    if op not in PRIMITIVE_OPERATIONS:
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


def _to_number(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _execute_primitive(conn, cfg: dict):
    built = _build_query(cfg)
    if built is None:
        raise ValueError(f"config primitiva invalida (operation={cfg.get('operation')})")
    sql, params = built
    return conn.execute(text(sql), params).scalar()


def _evaluate_expression(conn, expr, depth: int = 0):
    if depth > MAX_EXPRESSION_DEPTH:
        raise ValueError('expresion demasiado anidada')
    if not isinstance(expr, dict):
        raise ValueError('expresion debe ser objeto')

    if 'literal' in expr:
        literal = expr['literal']
        if not isinstance(literal, (int, float)):
            raise ValueError('literal debe ser numerico')
        return literal

    if expr.get('operation') in PRIMITIVE_OPERATIONS:
        return _execute_primitive(conn, expr)

    op = expr.get('op')
    if op not in COMBINATOR_OPS:
        raise ValueError(f"combinator invalido: '{op}'")

    left = _to_number(_evaluate_expression(conn, expr.get('left'), depth + 1))
    right = _to_number(_evaluate_expression(conn, expr.get('right'), depth + 1))
    if left is None or right is None:
        return None
    if op == 'add':
        return left + right
    if op == 'sub':
        return left - right
    if op == 'mul':
        return left * right
    if op == 'div':
        return left / right if right != 0 else None
    if op == 'percent':
        return (left / right) * 100 if right != 0 else None
    return ((left - right) / right) * 100 if right != 0 else None


def _execute_stat(conn, cfg: dict):
    op = cfg.get('operation')
    if op == 'static':
        return cfg.get('value')
    if op == 'formula':
        return _evaluate_expression(conn, cfg.get('expression'))
    return _execute_primitive(conn, cfg)


def _format_value(value, fmt) -> str | None:
    if value is None:
        return None
    if not fmt:
        return str(value)
    number = _to_number(value)
    if number is None:
        return str(value)
    if fmt == 'integer':
        return str(int(round(number)))
    if fmt in ('decimal_2', 'currency_mxn'):
        return f'{number:.2f}'
    if fmt == 'percentage':
        return f'{number:.1f}'
    if fmt == 'compact':
        for threshold, suffix in ((1_000_000_000, 'B'), (1_000_000, 'M'), (1_000, 'K')):
            if abs(number) >= threshold:
                return f'{number / threshold:.1f}{suffix}'
        return str(int(number)) if number == int(number) else f'{number:.1f}'
    return str(value)


def _refresh_layer(conn, layer_key: str, stats_config: list) -> tuple[list, list]:
    values = []
    errors = []

    for cfg in stats_config:
        if not isinstance(cfg, dict):
            errors.append('entrada de configuracion invalida')
            continue
        if cfg.get('operation') not in STATS_OPERATIONS:
            errors.append(f"pos={cfg.get('position')}: operation '{cfg.get('operation')}' no soportada")
            continue

        needs_db = cfg.get('operation') != 'static'
        savepoint = conn.begin_nested() if needs_db else None
        try:
            raw = _execute_stat(conn, cfg)
            if savepoint is not None:
                savepoint.commit()
        except Exception as exc:
            if savepoint is not None:
                savepoint.rollback()
            errors.append(f"pos={cfg.get('position')}: {exc}")
            continue

        values.append({
            'posicion': cfg.get('position'),
            'nombre': cfg.get('label'),
            'simbolo': cfg.get('symbol'),
            'valor': _format_value(raw, cfg.get('format')),
        })

    values.sort(key=lambda item: item['posicion'] if isinstance(item['posicion'], int) else 99)
    return values, errors


_SELECT_PENDING = """
    SELECT layer_key, stats_config
    FROM mapalab.layer_stats
    WHERE stats_config IS NOT NULL
      AND jsonb_array_length(stats_config) > 0
      AND (
        :force
        OR values_refreshed_at IS NULL
        OR NOW() - values_refreshed_at >= make_interval(mins => GREATEST(ttl_minutes - 5, 1))
      )
    ORDER BY layer_key
"""


def main() -> int:
    url = _build_url()
    if not url:
        Logger.error('DATAENGINE connection no configurada')
        return 1

    force = '--force' in sys.argv

    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            rows = conn.execute(text(_SELECT_PENDING), {'force': force}).fetchall()

            if not rows:
                Logger.info('📊  Sin capas vencidas por TTL — nada que refrescar')
                return 0

            updated = failed = 0
            degraded = []
            for layer_key, stats_config in rows:
                transaction = conn.begin()
                try:
                    values, errors = _refresh_layer(conn, layer_key, stats_config or [])
                    for detail in errors:
                        Logger.warning(f'   [{layer_key}] {detail}')

                    if not values:
                        transaction.rollback()
                        failed += 1
                        Logger.warning(f'   [{layer_key}] ninguna stat pudo calcularse; se conservan los valores previos')
                        continue

                    conn.execute(
                        text("""
                            UPDATE mapalab.layer_stats
                            SET values = CAST(:values AS jsonb),
                                values_refreshed_at = :now
                            WHERE layer_key = :layer_key
                        """),
                        {
                            'values': json.dumps(values),
                            'now': datetime.now(timezone.utc),
                            'layer_key': layer_key,
                        },
                    )
                    transaction.commit()
                    updated += 1
                    if errors:
                        degraded.append(layer_key)
                except Exception as exc:
                    transaction.rollback()
                    failed += 1
                    Logger.warning(f'   [{layer_key}] refresh fallo: {exc}')

        Logger.info(f'✅  layer_stats: updated={updated}, failed={failed}, parciales={len(degraded)}')
        if degraded:
            Logger.warning(f'⚠️   Capas actualizadas con stats faltantes: {", ".join(degraded)}')
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
