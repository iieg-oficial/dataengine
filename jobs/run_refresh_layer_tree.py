import hashlib
import json
import os
import sys
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import create_engine, text

from core.utils.logger import Logger


def main() -> int:
    url = _build_url()
    if not url:
        Logger.error('DATAENGINE connection no configurada')
        return 1

    Logger.info('🌳  Building mapalab.layer_tree_cache...')
    engine = create_engine(url)
    try:
        with engine.begin() as conn:
            workspaces = _fetch_workspaces(conn)
            ws_map = {w['alias']: w for w in workspaces}

            layers = _fetch_layers(conn)
            aliases = _fetch_aliases(conn)
            max_updated = _max_updated_at(conn)
            count = len(layers)

            tree = _build_tree(layers, ws_map, aliases)
            initial_order = _fetch_initial_order(conn)

            etag = _compute_etag(max_updated, count)

            _upsert_cache(conn, etag, tree, initial_order, workspaces, max_updated, count)

        Logger.info(f'✅  layer_tree_cache refreshed: {count} layers, etag={etag}')
        return 0
    except Exception as exc:
        Logger.error(f'❌  Refresh fallo: {exc}')
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


_WORKSPACE_COLS = ['alias', 'geoserver_workspace', 'db_schema', 'label']


def _fetch_workspaces(conn) -> list[dict]:
    rows = conn.execute(text(
        f"SELECT {', '.join(_WORKSPACE_COLS)} FROM mapalab.workspaces ORDER BY alias"
    )).fetchall()
    return [dict(zip(_WORKSPACE_COLS, r)) for r in rows]


_LAYER_COLS = [
    'id', 'slug', 'parent_id', 'label', 'sort_order', 'node_type',
    'hidden_in_menu', 'disabled',
    'workspace_alias', 'geoserver_layer', 'styles', 'cql_filter', 'wms_group',
    'tiled', 'image_format', 'antialias',
    'wfs_available', 'wfs_layer_name', 'downloadable', 'metadata_layer',
    'default_date', 'time_enabled', 'time_style_pattern',
    'raster_periodicity', 'hide_periodicity',
    'default_zoom', 'zoom_range',
    'search_tags', 'searchable_fields',
    'has_municipio', 'has_direccion', 'municipio_field', 'municipio_field_type',
    'direccion_field',
    'infobox_template', 'infobox_config',
    'icon_url', 'icon_overrides',
    'notice', 'badge',
    'highlight_color', 'highlight_shape',
    'geometry_type',
]


def _fetch_layers(conn) -> list[dict]:
    rows = conn.execute(text(
        f"SELECT {', '.join(_LAYER_COLS)} FROM mapalab.layers "
        "WHERE deleted_at IS NULL "
        "ORDER BY parent_id NULLS FIRST, sort_order, id"
    )).fetchall()
    return [dict(zip(_LAYER_COLS, r)) for r in rows]


def _fetch_aliases(conn) -> dict[str, list[str]]:
    rows = conn.execute(text(
        "SELECT layer_id, alias FROM mapalab.layer_aliases ORDER BY layer_id, created_at"
    )).fetchall()
    out: dict[str, list[str]] = {}
    for layer_id, alias in rows:
        out.setdefault(layer_id, []).append(alias)
    return out


def _fetch_initial_order(conn) -> list[str]:
    rows = conn.execute(text(
        'SELECT layer_id FROM mapalab.initial_layer_order ORDER BY sort_order'
    )).fetchall()
    return [r[0] for r in rows]


def _max_updated_at(conn) -> Optional[datetime]:
    return conn.execute(text(
        'SELECT max(updated_at) FROM mapalab.layers WHERE deleted_at IS NULL'
    )).scalar()


def _resolve_acervo_icon(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    if raw.startswith('/acervo/') or raw.startswith('/api/') or '://' in raw:
        return raw
    return f'/acervo/{raw.lstrip("/")}'


def _layer_to_wms_config(layer: dict, ws_map: dict[str, dict]) -> Optional[dict]:
    alias = layer.get('workspace_alias')
    if not alias:
        return None
    ws = ws_map.get(alias)
    if not ws:
        return None
    return {
        'workspace': alias,
        'geoserverLayer': layer.get('geoserver_layer'),
        'geoserverWorkspace': ws['geoserver_workspace'],
        'styles': layer.get('styles') or '',
        'cqlFilter': layer.get('cql_filter') or '',
        'wmsGroup': layer.get('wms_group'),
        'tiled': bool(layer.get('tiled')),
        'format': layer.get('image_format') or 'image/png',
        'antialias': layer.get('antialias') or 'text',
        'wfsAvailable': layer.get('wfs_available'),
        'wfsLayerName': layer.get('wfs_layer_name'),
        'timeEnabled': layer.get('time_enabled'),
        'timeStylePattern': layer.get('time_style_pattern'),
        'metadataLayer': layer.get('metadata_layer'),
    }


def _layer_to_search_meta(layer: dict) -> Optional[dict]:
    has_any = (
        layer.get('search_tags') or layer.get('searchable_fields')
        or layer.get('has_municipio') or layer.get('has_direccion')
    )
    if not has_any:
        return None
    meta: dict[str, Any] = {}
    if layer.get('search_tags'):
        meta['tags'] = layer['search_tags']
    if layer.get('searchable_fields'):
        meta['searchableFields'] = layer['searchable_fields']
    if layer.get('has_municipio'):
        meta['hasMunicipio'] = True
        if layer.get('municipio_field'):
            meta['municipioField'] = layer['municipio_field']
        if layer.get('municipio_field_type'):
            meta['municipioFieldType'] = layer['municipio_field_type']
    if layer.get('has_direccion'):
        meta['hasDireccion'] = True
        if layer.get('direccion_field'):
            meta['direccionField'] = layer['direccion_field']
    return meta


def _layer_to_node(layer: dict, ws_map: dict[str, dict], aliases: dict[str, list[str]]) -> dict:
    label = layer['label']
    if layer.get('disabled'):
        label = f'*{label}'

    node: dict[str, Any] = {
        'id': layer['id'],
        'label': label,
        'nodeType': layer['node_type'],
        'sortOrder': layer['sort_order'],
        'children': [],
    }

    if layer.get('slug'):
        node['slug'] = layer['slug']

    layer_aliases = aliases.get(layer['id'])
    if layer_aliases:
        node['aliases'] = layer_aliases

    if layer['node_type'] == 'category':
        node['isCategory'] = True
    elif layer['node_type'] == 'label':
        node['isLabel'] = True
    elif layer['node_type'] == 'group':
        node['forceGroup'] = True

    if layer['node_type'] == 'tema' and layer.get('icon_url'):
        node['iconUrl'] = _resolve_acervo_icon(layer['icon_url'])

    if layer['node_type'] == 'tema' and isinstance(layer.get('icon_overrides'), dict):
        node['iconOverrides'] = {
            k: _resolve_acervo_icon(v) for k, v in layer['icon_overrides'].items()
        }

    if layer.get('hidden_in_menu'):
        node['hiddenInMenu'] = True

    wms = _layer_to_wms_config(layer, ws_map)
    if wms:
        node['wmsConfig'] = wms

    if layer.get('downloadable') is False:
        node['downloadable'] = False

    if layer.get('default_date') is not None:
        node['defaultDate'] = layer['default_date']
    if layer.get('default_zoom') is not None:
        node['defaultZoom'] = layer['default_zoom']
    if layer.get('zoom_range') is not None:
        node['zoomRange'] = layer['zoom_range']
    if layer.get('raster_periodicity') is not None:
        node['rasterPeriodicity'] = layer['raster_periodicity']
    if layer.get('hide_periodicity'):
        node['hidePeriodicity'] = True

    search_meta = _layer_to_search_meta(layer)
    if search_meta:
        node['searchMeta'] = search_meta

    if layer.get('infobox_config') is not None:
        node['littleCard'] = layer['infobox_config']

    notice = layer.get('notice')
    if notice and isinstance(notice, dict) and notice.get('enabled'):
        node['notice'] = notice

    badge = layer.get('badge')
    if badge and isinstance(badge, dict) and badge.get('enabled'):
        node['badge'] = badge

    if layer.get('highlight_color'):
        node['highlightColor'] = layer['highlight_color']

    if layer.get('highlight_shape'):
        node['highlightShape'] = layer['highlight_shape']

    if layer.get('geometry_type'):
        node['geometryType'] = layer['geometry_type']

    return node


def _inherit_little_card(nodes_by_id: dict, layers: list[dict]) -> None:
    """Propaga `littleCard` desde el ancestro `group` mas cercano hacia los descendientes que no tengan uno propio.

    El campo `inheritedFrom` queda como pista de origen (no se renderiza, util para debugging).
    """
    parent_of: dict[str, Optional[str]] = {layer['id']: layer.get('parent_id') for layer in layers}
    type_of: dict[str, str] = {layer['id']: layer['node_type'] for layer in layers}
    own_card: dict[str, bool] = {
        layer['id']: layer.get('infobox_config') is not None for layer in layers
    }

    def find_group_ancestor_card(layer_id: str) -> Optional[tuple[str, dict]]:
        cur = parent_of.get(layer_id)
        while cur is not None:
            ancestor_node = nodes_by_id.get(cur)
            if ancestor_node is None:
                break
            if type_of.get(cur) == 'group' and ancestor_node.get('littleCard') is not None:
                return cur, ancestor_node['littleCard']
            cur = parent_of.get(cur)
        return None

    for layer in layers:
        if own_card.get(layer['id']):
            continue
        if layer['node_type'] not in ('leaf', 'group'):
            continue
        found = find_group_ancestor_card(layer['id'])
        if found is None:
            continue
        ancestor_id, card = found
        node = nodes_by_id[layer['id']]
        node['littleCard'] = card
        node['inheritedFrom'] = ancestor_id


def _build_tree(layers: list[dict], ws_map: dict[str, dict], aliases: dict[str, list[str]]) -> list[dict]:
    nodes_by_id: dict[str, dict] = {}
    roots: list[dict] = []

    for layer in layers:
        nodes_by_id[layer['id']] = _layer_to_node(layer, ws_map, aliases)

    _inherit_little_card(nodes_by_id, layers)

    for layer in layers:
        node = nodes_by_id[layer['id']]
        parent_id = layer.get('parent_id')
        if parent_id is None:
            roots.append(node)
        else:
            parent = nodes_by_id.get(parent_id)
            if parent is not None:
                parent['children'].append(node)

    return roots


def _compute_etag(max_updated_at: Optional[datetime], count: int) -> str:
    ts = max_updated_at.isoformat() if max_updated_at else 'empty'
    digest = hashlib.md5(f'{ts}|{count}'.encode()).hexdigest()[:16]
    return f'W/"{digest}"'


def _upsert_cache(
    conn, etag: str, tree: list, initial_order: list, workspaces: list,
    max_updated: Optional[datetime], count: int,
) -> None:
    conn.execute(
        text("""
            INSERT INTO mapalab.layer_tree_cache
                (id, etag, tree, initial_order, workspaces, source_max_updated_at, layer_count, updated_at)
            VALUES
                (1, :etag, CAST(:tree AS jsonb), CAST(:initial AS jsonb), CAST(:ws AS jsonb), :max_updated, :count, NOW())
            ON CONFLICT (id) DO UPDATE SET
                etag = EXCLUDED.etag,
                tree = EXCLUDED.tree,
                initial_order = EXCLUDED.initial_order,
                workspaces = EXCLUDED.workspaces,
                source_max_updated_at = EXCLUDED.source_max_updated_at,
                layer_count = EXCLUDED.layer_count,
                updated_at = NOW()
        """),
        {
            'etag': etag,
            'tree': json.dumps(tree),
            'initial': json.dumps(initial_order),
            'ws': json.dumps(workspaces),
            'max_updated': max_updated,
            'count': count,
        },
    )


if __name__ == '__main__':
    sys.exit(main())
