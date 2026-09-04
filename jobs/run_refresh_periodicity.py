import os
import sys

from sqlalchemy import create_engine, text

from core.periodicidad.sugerencias import sugerencias_de
from core.utils.logger import Logger


def main() -> int:
    url = os.getenv('DATAENGINE_URL') or _build_url_from_parts()
    if not url:
        Logger.error('DATAENGINE_URL no configurado')
        return 1

    Logger.info('🔄  Refreshing public.layer_periodicity...')
    engine = create_engine(url)
    try:
        with engine.begin() as conn:
            conn.execute(text('SELECT public.refresh_layer_periodicity()'))
            count = conn.execute(
                text('SELECT COUNT(*) FROM public.layer_periodicity')
            ).scalar()
        Logger.info(f'✅  layer_periodicity refreshed ({count} layers)')

        escritas = _refresh_sugerencias(engine)
        Logger.info(f'✅  sugerencias de ficha actualizadas ({escritas} capas)')
        return 0
    except Exception as exc:
        Logger.error(f'❌  Refresh fallo: {exc}')
        return 1
    finally:
        engine.dispose()


SQL_PERIODICIDAD_POR_FICHA = """
SELECT DISTINCT m.layer_key, p.periodicity
FROM mapalab.layer_metadata m
JOIN mapalab.layers l
  ON l.workspace_alias || ':' || l.geoserver_layer = m.layer_key
 AND l.deleted_at IS NULL
JOIN mapalab.workspaces w ON w.alias = l.workspace_alias
JOIN public.layer_periodicity p
  ON p.layer_key = w.db_schema || ':' || l.geoserver_layer
"""

SQL_GUARDAR_SUGERENCIA = """
UPDATE mapalab.layer_metadata
SET fecha_ultima_sugerida = :fecha,
    frecuencia_sugerida = :frecuencia,
    sugerencias_actualizadas_en = NOW()
WHERE layer_key = :layer_key
"""


def _refresh_sugerencias(engine) -> int:
    escritas = 0
    with engine.begin() as conn:
        filas = conn.execute(text(SQL_PERIODICIDAD_POR_FICHA)).fetchall()
        for layer_key, periodicidad in filas:
            fecha, frecuencia = sugerencias_de(periodicidad or {})
            if not fecha and not frecuencia:
                continue
            conn.execute(
                text(SQL_GUARDAR_SUGERENCIA),
                {'layer_key': layer_key, 'fecha': fecha, 'frecuencia': frecuencia},
            )
            escritas += 1
    return escritas


def _build_url_from_parts() -> str | None:
    user = os.getenv('DATAENGINE_DB_USER')
    pwd = os.getenv('DATAENGINE_DB_PASSWORD')
    host = os.getenv('DATAENGINE_DB_HOST')
    port = os.getenv('DATAENGINE_DB_PORT', '5432')
    db = os.getenv('DATAENGINE_DB_NAME')
    sslmode = os.getenv('DATAENGINE_DB_SSLMODE', 'require')
    if not (user and pwd and host and db):
        return None
    return f'postgresql://{user}:{pwd}@{host}:{port}/{db}?sslmode={sslmode}'


if __name__ == '__main__':
    sys.exit(main())
