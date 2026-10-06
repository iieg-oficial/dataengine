import json
import os
import sys
from typing import Any, Optional
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from sqlalchemy import create_engine, text

from core.utils.logger import Logger
from core.utils.secretos import leer_secreto


POINT = 'point'
LINE = 'line'
POLYGON = 'polygon'
RASTER = 'raster'

RASTER_WORKSPACES = frozenset({'raster', 'lluvia', 'temperatura'})

OGC_A_TIPO: dict[str, str] = {
    'point': POINT,
    'multipoint': POINT,
    'linestring': LINE,
    'multilinestring': LINE,
    'curve': LINE,
    'multicurve': LINE,
    'polygon': POLYGON,
    'multipolygon': POLYGON,
    'surface': POLYGON,
    'multisurface': POLYGON,
}

TIMEOUT_SEGUNDOS = 30


def main() -> int:
    url = _build_url()
    if not url:
        Logger.error('DATAENGINE connection no configurada')
        return 1

    geoserver = (os.getenv('GEOSERVER_URL') or '').rstrip('/')
    if not geoserver:
        Logger.error('GEOSERVER_URL no configurada')
        return 1

    Logger.info('📐  Clasificando la geometria del catalogo de capas...')
    engine = create_engine(url)
    try:
        with engine.begin() as conn:
            capas = _fetch_layers(conn)
            tipos = _clasificar(capas, geoserver)
            actualizadas = _guardar(conn, tipos)
            _borrar_cache(conn)

        resumen = _resumen(capas, tipos)
        Logger.info(f'✅  {actualizadas} capas actualizadas: {resumen}')

        sin_tipo = [c['id'] for c in capas if tipos.get(c['id']) is None]
        if sin_tipo:
            Logger.warning(f'⚠️  {len(sin_tipo)} sin clasificar: {", ".join(sorted(sin_tipo))}')
        return 0
    except Exception as exc:
        Logger.error(f'❌  Backfill fallo: {exc}')
        return 1
    finally:
        engine.dispose()


def _build_url() -> Optional[str]:
    direct = os.getenv('DATAENGINE_URL')
    if direct:
        return direct
    user = os.getenv('DATAENGINE_DB_USER')
    pwd = leer_secreto('DATAENGINE_DB_PASSWORD')
    host = os.getenv('DATAENGINE_DB_HOST')
    port = os.getenv('DATAENGINE_DB_PORT', '5432')
    db = os.getenv('DATAENGINE_DB_NAME')
    sslmode = os.getenv('DATAENGINE_DB_SSLMODE', 'require')
    if not (user and pwd and host and db):
        return None
    return f'postgresql://{user}:{pwd}@{host}:{port}/{db}?sslmode={sslmode}'


_LAYER_COLS = [
    'id', 'workspace_alias', 'geoserver_workspace', 'geoserver_layer',
    'wfs_layer_name', 'raster_periodicity', 'geometry_type',
]


def _fetch_layers(conn) -> list[dict[str, Any]]:
    rows = conn.execute(text("""
        SELECT l.id, l.workspace_alias, w.geoserver_workspace, l.geoserver_layer,
               l.wfs_layer_name, l.raster_periodicity, l.geometry_type
          FROM mapalab.layers l
          LEFT JOIN mapalab.workspaces w ON w.alias = l.workspace_alias
         WHERE l.deleted_at IS NULL
           AND l.node_type = 'leaf'
           AND l.geoserver_layer IS NOT NULL
         ORDER BY l.id
    """)).fetchall()
    return [dict(zip(_LAYER_COLS, r)) for r in rows]


def _es_raster(capa: dict[str, Any]) -> bool:
    if capa.get('raster_periodicity'):
        return True
    return str(capa.get('workspace_alias') or '') in RASTER_WORKSPACES


def _typename(capa: dict[str, Any]) -> str:
    workspace = capa.get('geoserver_workspace') or ''
    declarado = capa.get('wfs_layer_name') or ''
    if declarado:
        return declarado if ':' in declarado else f'{workspace}:{declarado}'
    layer = capa.get('geoserver_layer') or ''
    if not (workspace and layer):
        return ''
    return f'{workspace}:{layer}'


def _tipo_de_propiedades(propiedades: list[dict[str, Any]]) -> Optional[str]:
    for propiedad in propiedades:
        local = str(propiedad.get('localType') or '').lower()
        if local in OGC_A_TIPO:
            return OGC_A_TIPO[local]
        tipo = str(propiedad.get('type') or '')
        if tipo.startswith('gml:'):
            resto = tipo.split(':', 1)[1].lower()
            if resto in OGC_A_TIPO:
                return OGC_A_TIPO[resto]
    return None


def _describe_feature_type(geoserver: str, type_name: str) -> Optional[str]:
    workspace = type_name.split(':', 1)[0]
    params = {
        'service': 'WFS',
        'version': '2.0.0',
        'request': 'DescribeFeatureType',
        'typeNames': type_name,
        'outputFormat': 'application/json',
    }
    url = f'{geoserver}/{workspace}/wfs?{urlencode(params)}'
    try:
        with urlopen(url, timeout=TIMEOUT_SEGUNDOS) as respuesta:
            datos = json.loads(respuesta.read().decode('utf-8'))
    except (URLError, OSError, ValueError) as exc:
        Logger.warning(f'   {type_name}: {exc}')
        return None

    tipos = datos.get('featureTypes') or []
    if not tipos:
        return None
    return _tipo_de_propiedades(tipos[0].get('properties') or [])


def _clasificar(capas: list[dict[str, Any]], geoserver: str) -> dict[str, Optional[str]]:
    memoria: dict[str, Optional[str]] = {}
    tipos: dict[str, Optional[str]] = {}

    for capa in capas:
        if _es_raster(capa):
            tipos[capa['id']] = RASTER
            continue

        type_name = _typename(capa)
        if not type_name:
            tipos[capa['id']] = None
            continue

        if type_name not in memoria:
            memoria[type_name] = _describe_feature_type(geoserver, type_name)
        tipos[capa['id']] = memoria[type_name]

    Logger.info(f'   {len(memoria)} DescribeFeatureType para {len(capas)} capas')
    return tipos


def _guardar(conn, tipos: dict[str, Optional[str]]) -> int:
    cambios = [
        {'id': layer_id, 'tipo': tipo}
        for layer_id, tipo in tipos.items()
        if tipo is not None
    ]
    if not cambios:
        return 0
    resultado = conn.execute(
        text("""
            UPDATE mapalab.layers
               SET geometry_type = :tipo,
                   updated_at = now()
             WHERE id = :id
               AND geometry_type IS DISTINCT FROM :tipo
        """),
        cambios,
    )
    return resultado.rowcount if resultado.rowcount is not None else len(cambios)


def _borrar_cache(conn) -> None:
    conn.execute(text('DELETE FROM mapalab.layer_tree_cache'))


def _resumen(capas: list[dict[str, Any]], tipos: dict[str, Optional[str]]) -> str:
    conteo: dict[str, int] = {}
    for capa in capas:
        clave = tipos.get(capa['id']) or 'sin clasificar'
        conteo[clave] = conteo.get(clave, 0) + 1
    return ', '.join(f'{clave}={valor}' for clave, valor in sorted(conteo.items()))


if __name__ == '__main__':
    sys.exit(main())
