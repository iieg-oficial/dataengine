import json
import math
import os
import unicodedata
from collections import defaultdict
from typing import Any, Optional
from urllib.parse import urlencode
from urllib.request import urlopen

import h3
from sqlalchemy import create_engine, text

from core.utils.logger import Logger


RESOLUCIONES: tuple[int, ...] = (3, 4, 6, 7)

CAMPOS_FECHA: tuple[str, ...] = ('fecha', 'anio', 'ano', 'fecha_hecho')
CAMPOS_MUNICIPIO: tuple[str, ...] = ('municipio', 'nombre_municipio', 'mun')

RASTER_WORKSPACES = frozenset({'raster', 'lluvia', 'temperatura'})

SRID_DESTINO = 6368
TIMEOUT_SEGUNDOS = 300


def main() -> int:
    url = _build_url()
    if not url:
        Logger.error('DATAENGINE connection no configurada')
        return 1

    geoserver = (os.getenv('GEOSERVER_URL') or '').rstrip('/')
    if not geoserver:
        Logger.error('GEOSERVER_URL no configurada')
        return 1

    Logger.info('⬢  Precalculando el hexbin H3 de las capas de puntos...')
    engine = create_engine(url)
    procesadas = 0
    fallidas: list[str] = []

    try:
        with engine.begin() as conn:
            capas = _fetch_layers(conn)
            municipios = _municipios(conn)

        for capa in capas:
            typename = _typename(capa)
            if not typename:
                continue
            try:
                with engine.begin() as conn:
                    celdas, conteos = _procesar(geoserver, capa, typename, municipios)
                    if not conteos:
                        continue
                    _guardar(conn, capa['id'], celdas, conteos)
                procesadas += 1
                Logger.info(f"   {capa['id']}: {len(celdas)} celdas, {len(conteos)} conteos")
            except Exception as exc:
                fallidas.append(f'{typename} ({exc})')

        Logger.info(f'✅  {procesadas} capas precalculadas')
        if fallidas:
            Logger.warning(f'⚠️  {len(fallidas)} fallaron: {"; ".join(fallidas)}')
        return 0
    except Exception as exc:
        Logger.error(f'❌  Refresh del hexbin fallo: {exc}')
        return 1
    finally:
        engine.dispose()


def _build_url() -> Optional[str]:
    direct = os.getenv('DATAENGINE_URL')
    if direct:
        return direct
    user = os.getenv('DATAENGINE_DB_USER')
    pwd = os.getenv('DATAENGINE_DB_PASSWORD')
    host = os.getenv('DATAENGINE_DB_HOST')
    port = os.getenv('DATAENGINE_DB_PORT', '5432')
    db = os.getenv('DATAENGINE_DB_NAME')
    sslmode = os.getenv('DATAENGINE_DB_SSLMODE', 'require')
    if not (user and pwd and host and db):
        return None
    return f'postgresql://{user}:{pwd}@{host}:{port}/{db}?sslmode={sslmode}'


def _fetch_layers(conn) -> list[dict[str, Any]]:
    cols = ['id', 'workspace_alias', 'geoserver_workspace', 'geoserver_layer',
            'wfs_layer_name', 'cql_filter']
    rows = conn.execute(text("""
        SELECT l.id, l.workspace_alias, w.geoserver_workspace, l.geoserver_layer,
               l.wfs_layer_name, l.cql_filter
          FROM mapalab.layers l
          LEFT JOIN mapalab.workspaces w ON w.alias = l.workspace_alias
         WHERE l.deleted_at IS NULL
           AND l.node_type = 'leaf'
           AND l.geometry_type = 'point'
           AND l.wfs_available
           AND l.geoserver_layer IS NOT NULL
         ORDER BY l.id
    """)).fetchall()
    capas = [dict(zip(cols, r)) for r in rows]
    return [c for c in capas if str(c.get('workspace_alias') or '') not in RASTER_WORKSPACES]


def _typename(capa: dict[str, Any]) -> str:
    workspace = capa.get('geoserver_workspace') or ''
    declarado = capa.get('wfs_layer_name') or ''
    if declarado:
        return declarado if ':' in declarado else f'{workspace}:{declarado}'
    layer = capa.get('geoserver_layer') or ''
    if not (workspace and layer):
        return ''
    return f'{workspace}:{layer}'


def _normalizar(texto: str) -> str:
    limpio = unicodedata.normalize('NFD', str(texto or ''))
    sin_acentos = ''.join(c for c in limpio if not unicodedata.combining(c))
    return sin_acentos.lower().strip()


def _municipios(conn) -> dict[str, str]:
    rows = conn.execute(text('SELECT clave_geo, nombre FROM mapalab.municipios')).fetchall()
    return {_normalizar(nombre): str(clave) for clave, nombre in rows}


def _ows(geoserver: str, typename: str, params: dict[str, str]) -> Any:
    workspace = typename.split(':')[0]
    url = f'{geoserver}/{workspace}/ows?{urlencode(params)}'
    with urlopen(url, timeout=TIMEOUT_SEGUNDOS) as respuesta:
        return json.loads(respuesta.read().decode('utf-8'))


def _propiedades(geoserver: str, typename: str) -> tuple[str, Optional[str], Optional[str]]:
    datos = _ows(geoserver, typename, {
        'service': 'WFS', 'version': '2.0.0', 'request': 'DescribeFeatureType',
        'typeNames': typename, 'outputFormat': 'application/json',
    })
    props = datos.get('featureTypes', [{}])[0].get('properties', [])
    nombres = [p.get('name') for p in props if p.get('name')]

    geometria = next(
        (p['name'] for p in props
         if str(p.get('type', '')).startswith('gml:') or p.get('localType') in ('Point', 'MultiPoint')),
        'geom',
    )
    fecha = next((n for n in nombres if _normalizar(n) in CAMPOS_FECHA), None)
    municipio = next((n for n in nombres if _normalizar(n) in CAMPOS_MUNICIPIO), None)
    return geometria, fecha, municipio


def _features(geoserver: str, typename: str, campos: list[str], cql: Optional[str]) -> list[dict]:
    params = {
        'service': 'WFS', 'version': '2.0.0', 'request': 'GetFeature',
        'typeNames': typename, 'outputFormat': 'application/json',
        'srsName': 'EPSG:3857', 'propertyName': ','.join(campos),
    }
    if cql:
        params['CQL_FILTER'] = cql
    return _ows(geoserver, typename, params).get('features') or []


SEMI_CIRCUNFERENCIA = 20037508.34


def _a_lonlat(x: float, y: float) -> tuple[float, float]:
    lon = x * 180.0 / SEMI_CIRCUNFERENCIA
    lat = math.degrees(math.atan(math.exp(y * math.pi / SEMI_CIRCUNFERENCIA)) * 2 - math.pi / 2)
    return lon, lat


def _anio_de(valor: Any) -> Optional[int]:
    texto = str(valor or '')[:4]
    return int(texto) if texto.isdigit() else None


def _procesar(geoserver: str, capa: dict[str, Any], typename: str,
              municipios: dict[str, str]) -> tuple[dict, dict]:
    geometria, campo_fecha, campo_muni = _propiedades(geoserver, typename)
    campos = [geometria] + [c for c in (campo_fecha, campo_muni) if c]
    features = _features(geoserver, typename, campos, capa.get('cql_filter'))

    celdas: dict[tuple[int, str], str] = {}
    conteos: dict[tuple[int, str, Optional[int], Optional[str]], int] = defaultdict(int)

    for feature in features:
        geom = feature.get('geometry') or {}
        if geom.get('type') != 'Point':
            continue
        x, y = (geom.get('coordinates') or [None, None])[:2]
        if x is None or y is None:
            continue
        lon, lat = _a_lonlat(x, y)

        props = feature.get('properties') or {}
        anio = _anio_de(props.get(campo_fecha)) if campo_fecha else None
        clave = municipios.get(_normalizar(props.get(campo_muni))) if campo_muni else None

        for resolucion in RESOLUCIONES:
            cell = h3.latlng_to_cell(lat, lon, resolucion)
            celdas.setdefault((resolucion, cell), _wkt_de(cell))
            conteos[(resolucion, cell, anio, clave)] += 1
            if anio is not None or clave is not None:
                conteos[(resolucion, cell, None, None)] += 1

    return celdas, dict(conteos)


def _wkt_de(cell: str) -> str:
    anillo = list(h3.cell_to_boundary(cell))
    if anillo and anillo[0] != anillo[-1]:
        anillo.append(anillo[0])
    puntos = ', '.join(f'{lon} {lat}' for lat, lon in anillo)
    return f'POLYGON(({puntos}))'


def _guardar(conn, layer_key: str, celdas: dict, conteos: dict) -> None:
    for (resolucion, cell), wkt in celdas.items():
        conn.execute(text("""
            INSERT INTO mapalab.hexbin_cells (resolution, h3_index, geom)
            VALUES (:res, :cell, ST_Transform(ST_GeomFromText(:wkt, 4326), :srid))
            ON CONFLICT (resolution, h3_index) DO NOTHING
        """), {'res': resolucion, 'cell': cell, 'wkt': wkt, 'srid': SRID_DESTINO})

    conn.execute(text('DELETE FROM mapalab.hexbin_counts WHERE layer_key = :key'),
                 {'key': layer_key})

    filas = [{'key': layer_key, 'res': res, 'cell': cell, 'anio': anio,
              'clave': clave, 'total': total}
             for (res, cell, anio, clave), total in conteos.items()]

    for i in range(0, len(filas), 1000):
        conn.execute(text("""
            INSERT INTO mapalab.hexbin_counts
                (layer_key, resolution, h3_index, anio, clave_municipio, total)
            VALUES (:key, :res, :cell, :anio, :clave, :total)
        """), filas[i:i + 1000])


if __name__ == '__main__':
    raise SystemExit(main())
