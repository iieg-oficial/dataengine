import json
import os
import re
import sys
from datetime import datetime, timezone

from sqlalchemy import create_engine, text

from core.utils.logger import Logger
from core.utils.secretos import leer_secreto


PRIMITIVE_OPERATIONS = {'count', 'count_distinct', 'count_where', 'sum', 'avg', 'min', 'max', 'latest'}
OPERATIONS_WITHOUT_FIELD = {'count', 'count_where'}
COMBINATOR_OPS = {'add', 'sub', 'mul', 'div', 'percent', 'percent_change'}
STATS_OPERATIONS = PRIMITIVE_OPERATIONS | {'formula', 'static'}
MAX_EXPRESSION_DEPTH = 6
FILTER_OPS = {'eq', 'in', 'gte', 'lte', 'between', 'is_not_null'}
CONTEXT_KEYS = {'municipio', 'municipio.claves', 'municipio.nombres', 'fecha.inicio', 'fecha.fin'}
MUNICIPIO_FIELD_TOKEN = '@municipio'
MUNICIPIO_CONTEXT_BY_TYPE = {'clave': '{{municipio.claves}}', 'nombre': '{{municipio.nombres}}'}
SQL_COMPARATORS = {'eq': '=', 'gte': '>=', 'lte': '<='}
MAX_FILTERS = 6
STATS_ROLE = 'mapalab_stats'

_PLACEHOLDER = re.compile(r'^\{\{([a-z_.]+)\}\}$')


def _is_identifier(value) -> bool:
    if not value or not isinstance(value, str):
        return False
    if len(value) > 100:
        return False
    return all(c.isalnum() or c == '_' for c in value)


def _placeholder_key(value) -> str | None:
    if not isinstance(value, str):
        return None
    match = _PLACEHOLDER.match(value.strip())
    return match.group(1) if match else None


def _resolve_context(value, context: dict | None) -> tuple[object, bool]:
    key = _placeholder_key(value)
    if key is None:
        return value, True
    if key not in CONTEXT_KEYS:
        return None, False
    resolved = (context or {}).get(key)
    if resolved is None:
        return None, False
    if isinstance(resolved, (list, tuple)) and not resolved:
        return None, False
    return resolved, True


def _valid_filters(raw, context: dict | None) -> list[dict] | None:
    if raw is None:
        return []
    if not isinstance(raw, list) or len(raw) > MAX_FILTERS:
        return None
    for item in raw:
        if not isinstance(item, dict):
            return None
        field = item.get('field')
        if field != MUNICIPIO_FIELD_TOKEN and not _is_identifier(field):
            return None
        if item.get('op') not in FILTER_OPS:
            return None
    return raw


def _build_conditions(filters: list[dict], context: dict | None, params: dict) -> list[str]:
    conditions: list[str] = []
    for i, item in enumerate(filters):
        field = item['field']
        op = item['op']
        if op == 'is_not_null':
            conditions.append(f'"{field}" IS NOT NULL')
            continue

        value = item.get('value')
        if value is None:
            continue

        if op == 'between':
            bounds = value if isinstance(value, list) else [value]
            resolved = [_resolve_context(v, context) for v in bounds]
            if len(resolved) != 2 or not all(ok for _, ok in resolved):
                continue
            low, high = f'f{i}_lo', f'f{i}_hi'
            params[low], params[high] = resolved[0][0], resolved[1][0]
            conditions.append(f'"{field}" BETWEEN :{low} AND :{high}')
            continue

        if op == 'in':
            raw = value if isinstance(value, list) else [value]
            expanded = []
            for entry in raw:
                item_value, ok = _resolve_context(entry, context)
                if not ok:
                    continue
                if isinstance(item_value, (list, tuple)):
                    expanded.extend(item_value)
                else:
                    expanded.append(item_value)
            if not expanded:
                continue
            names = []
            for j, entry in enumerate(expanded):
                name = f'f{i}_{j}'
                params[name] = entry
                names.append(f':{name}')
            conditions.append(f'"{field}" IN ({", ".join(names)})')
            continue

        resolved, ok = _resolve_context(value, context)
        if not ok:
            continue
        name = item.get('param') or f'f{i}'
        params[name] = resolved
        conditions.append(f'"{field}" {SQL_COMPARATORS[op]} :{name}')
    return conditions


def _effective_filters(cfg: dict, filters: list[dict]) -> list[dict]:
    where_field = cfg.get('where_field')
    where_value = cfg.get('where_value')
    if where_field and where_value is not None:
        legacy = {'field': where_field, 'op': 'eq', 'value': where_value, 'param': 'where_value'}
        return [legacy] + filters
    return filters


_LAYER_BINDING_SQL = """
    WITH RECURSIVE cadena AS (
        SELECT id, parent_id, municipio_field, municipio_field_type
        FROM mapalab.layers
        WHERE workspace_alias || ':' || geoserver_layer = :layer_key
          AND deleted_at IS NULL
        UNION ALL
        SELECT p.id, p.parent_id, p.municipio_field, p.municipio_field_type
        FROM mapalab.layers p
        JOIN cadena c ON c.parent_id = p.id
        WHERE p.deleted_at IS NULL
    )
    SELECT municipio_field, municipio_field_type
    FROM cadena
    WHERE municipio_field IS NOT NULL
    LIMIT 1
"""


def load_layer_binding(conn, layer_key: str) -> dict | None:
    row = conn.execute(text(_LAYER_BINDING_SQL), {'layer_key': layer_key}).first()
    if not row:
        return None
    return {'municipio_field': row[0], 'municipio_field_type': row[1]}


def _bind_filter(item: dict, binding: dict | None) -> dict | None:
    bound = dict(item)
    if bound.get('field') == MUNICIPIO_FIELD_TOKEN:
        field = (binding or {}).get('municipio_field')
        if not field:
            return None
        bound['field'] = field
    if _placeholder_key(bound.get('value')) == 'municipio':
        replacement = MUNICIPIO_CONTEXT_BY_TYPE.get((binding or {}).get('municipio_field_type'))
        if not replacement:
            return None
        bound['value'] = replacement
    return bound


def _bind_expression(expr: dict, binding: dict | None) -> dict:
    bound = dict(expr)
    if bound.get('filters'):
        bound['filters'] = [
            f for f in (_bind_filter(f, binding) for f in bound['filters']) if f is not None
        ]
    for side in ('left', 'right'):
        if isinstance(bound.get(side), dict):
            bound[side] = _bind_expression(bound[side], binding)
    return bound


def bind_layer_fields(stats_config, binding: dict | None) -> list:
    bound_config = []
    for cfg in stats_config or []:
        if not isinstance(cfg, dict):
            bound_config.append(cfg)
            continue
        item = dict(cfg)
        if item.get('filters'):
            item['filters'] = [
                f for f in (_bind_filter(f, binding) for f in item['filters']) if f is not None
            ]
        if item.get('operation') == 'formula' and isinstance(item.get('expression'), dict):
            item['expression'] = _bind_expression(item['expression'], binding)
        bound_config.append(item)
    return bound_config


def _build_query(cfg: dict, context: dict | None = None) -> tuple[str, dict] | None:
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

    if op not in OPERATIONS_WITHOUT_FIELD and not _is_identifier(field):
        return None
    if field is not None and not _is_identifier(field):
        return None
    if where_field and not _is_identifier(where_field):
        return None
    if order_field and not _is_identifier(order_field):
        return None

    filters = _valid_filters(cfg.get('filters'), context)
    if filters is None:
        return None
    if op == 'count_where' and not filters and (not where_field or where_value is None):
        return None
    if op == 'latest' and not order_field:
        return None

    fqtn = f'"{schema}"."{table}"'
    params: dict = {}
    conditions = _build_conditions(_effective_filters(cfg, filters), context, params)
    where = f' WHERE {" AND ".join(conditions)}' if conditions else ''

    if op in ('count', 'count_where'):
        sql = f'SELECT COUNT(*) FROM {fqtn}{where}'
    elif op == 'count_distinct':
        sql = f'SELECT COUNT(DISTINCT "{field}") FROM {fqtn}{where}'
    elif op in ('sum', 'avg', 'min', 'max'):
        sql = f'SELECT {op.upper()}("{field}") FROM {fqtn}{where}'
    elif op == 'latest':
        sql = f'SELECT "{field}" FROM {fqtn}{where} ORDER BY "{order_field}" DESC LIMIT 1'
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


_ALLOWED_SCHEMAS_SQL = """
    SELECT DISTINCT db_schema
    FROM mapalab.workspaces
    WHERE db_schema IS NOT NULL AND db_schema <> 'mapalab'
"""


def load_allowed_schemas(conn) -> frozenset[str]:
    return frozenset(row[0] for row in conn.execute(text(_ALLOWED_SCHEMAS_SQL)))


def _execute_primitive(conn, cfg: dict, schemas: frozenset[str]):
    if cfg.get('schema') not in schemas:
        raise ValueError(f"schema '{cfg.get('schema')}' fuera de mapalab.workspaces")
    built = _build_query(cfg)
    if built is None:
        raise ValueError(f"config primitiva invalida (operation={cfg.get('operation')})")
    sql, params = built
    return conn.execute(text(sql), params).scalar()


def _evaluate_expression(conn, expr, schemas: frozenset[str], depth: int = 0):
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
        return _execute_primitive(conn, expr, schemas)

    op = expr.get('op')
    if op not in COMBINATOR_OPS:
        raise ValueError(f"combinator invalido: '{op}'")

    left = _to_number(_evaluate_expression(conn, expr.get('left'), schemas, depth + 1))
    right = _to_number(_evaluate_expression(conn, expr.get('right'), schemas, depth + 1))
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


def _execute_stat(conn, cfg: dict, schemas: frozenset[str]):
    op = cfg.get('operation')
    if op == 'static':
        return cfg.get('value')
    if op == 'formula':
        return _evaluate_expression(conn, cfg.get('expression'), schemas)
    return _execute_primitive(conn, cfg, schemas)


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


def _refresh_layer(
    conn, layer_key: str, stats_config: list, schemas: frozenset[str]
) -> tuple[list, list]:
    values = []
    errors = []

    binding = load_layer_binding(conn, layer_key)

    for cfg in bind_layer_fields(stats_config, binding):
        if not isinstance(cfg, dict):
            errors.append('entrada de configuracion invalida')
            continue
        if cfg.get('operation') not in STATS_OPERATIONS:
            errors.append(f"pos={cfg.get('position')}: operation '{cfg.get('operation')}' no soportada")
            continue

        needs_db = cfg.get('operation') != 'static'
        savepoint = conn.begin_nested() if needs_db else None
        try:
            if savepoint is not None:
                conn.execute(text(f'SET LOCAL ROLE {STATS_ROLE}'))
            raw = _execute_stat(conn, cfg, schemas)
            if savepoint is not None:
                conn.execute(text('RESET ROLE'))
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
            schemas = load_allowed_schemas(conn)

            if not rows:
                Logger.info('📊  Sin capas vencidas por TTL — nada que refrescar')
                return 0

            updated = failed = 0
            degraded = []
            for layer_key, stats_config in rows:
                transaction = conn.begin()
                try:
                    values, errors = _refresh_layer(conn, layer_key, stats_config or [], schemas)
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
    pwd = leer_secreto('MAPALAB_STATS_DB_PASSWORD') or leer_secreto('DATAENGINE_DB_PASSWORD')
    host = os.getenv('DATAENGINE_DB_HOST')
    port = os.getenv('DATAENGINE_DB_PORT', '5432')
    db = os.getenv('DATAENGINE_DB_NAME')
    sslmode = os.getenv('DATAENGINE_DB_SSLMODE', 'require')
    if not (user and pwd and host and db):
        return None
    return f'postgresql://{user}:{pwd}@{host}:{port}/{db}?sslmode={sslmode}'


if __name__ == '__main__':
    sys.exit(main())
