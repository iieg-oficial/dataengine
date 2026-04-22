import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session


VALID_NODE_TYPES = {'tema', 'category', 'label', 'group', 'leaf'}


def infer_node_type(node: dict, depth: int) -> str:
    if depth == 0:
        return 'tema'
    if node.get('isCategory'):
        return 'category'
    if node.get('isLabel'):
        return 'label'
    if node.get('forceGroup'):
        return 'group'
    return 'leaf'


def strip_leading_star(label: str) -> tuple[str, bool]:
    if label.startswith('*'):
        return label.lstrip('* ').strip(), True
    return label, False


def _extract_layer_name(wms: dict) -> str | None:
    layer_name = wms.get('layerName')
    if layer_name and ':' in layer_name:
        return layer_name.split(':', 1)[1]
    return layer_name


def flatten_tree(nodes: list[dict], parent_id: str | None, depth: int, out: list[dict]) -> None:
    for sort_order, node in enumerate(nodes):
        label_raw = node.get('label', '')
        label_clean, disabled = strip_leading_star(label_raw)
        node_type = infer_node_type(node, depth)

        if node_type not in VALID_NODE_TYPES:
            raise ValueError(f"node_type invalido '{node_type}' para id={node.get('id')}")

        wms = node.get('wmsConfig') or {}
        search_meta = node.get('searchMeta') or {}

        out.append({
            'id': node['id'],
            'parent_id': parent_id,
            'label': label_clean,
            'sort_order': sort_order,
            'node_type': node_type,
            'hidden_in_menu': bool(node.get('hiddenInMenu', False)),
            'disabled': disabled,
            'workspace_alias': wms.get('workspace') or None,
            'geoserver_layer': _extract_layer_name(wms),
            'styles': wms.get('styles', '') or '',
            'cql_filter': wms.get('cqlFilter', '') or '',
            'wms_group': wms.get('wmsGroup'),
            'wfs_available': bool(wms.get('wfsAvailable', True)),
            'wfs_layer_name': wms.get('wfsLayerName'),
            'downloadable': bool(node.get('downloadable', True)),
            'metadata_layer': wms.get('metadataLayer'),
            'default_date': node.get('defaultDate'),
            'time_enabled': bool(wms.get('timeEnabled', False)),
            'time_style_pattern': wms.get('timeStylePattern'),
            'raster_periodicity': node.get('rasterPeriodicity'),
            'hide_periodicity': bool(node.get('hidePeriodicity', False)),
            'default_zoom': node.get('defaultZoom'),
            'zoom_range': node.get('zoomRange'),
            'search_tags': search_meta.get('tags'),
            'searchable_fields': search_meta.get('searchableFields'),
            'has_municipio': bool(search_meta.get('hasMunicipio', False)),
            'has_direccion': bool(search_meta.get('hasDireccion', False)),
            'municipio_field': search_meta.get('municipioField'),
            'direccion_field': search_meta.get('direccionField'),
            'infobox_config': node.get('littleCard'),
        })

        children = node.get('children') or []
        flatten_tree(children, node['id'], depth + 1, out)


def sort_rows(rows: list[dict]) -> list[dict]:
    by_id = {r['id']: r for r in rows}
    visited: set[str] = set()
    order: list[dict] = []

    def visit(rid: str, stack: set[str]) -> None:
        if rid in visited:
            return
        if rid in stack:
            raise ValueError(f'Ciclo en {rid}')
        stack.add(rid)
        row = by_id.get(rid)
        if row is None:
            stack.remove(rid)
            return
        if row['parent_id']:
            visit(row['parent_id'], stack)
        visited.add(rid)
        order.append(row)
        stack.remove(rid)

    for r in rows:
        visit(r['id'], set())
    return order


_UPSERT_LAYER = text("""
INSERT INTO mapalab.layers (
    id, parent_id, label, sort_order, node_type, hidden_in_menu, disabled,
    workspace_alias, geoserver_layer, styles, cql_filter, wms_group,
    wfs_available, wfs_layer_name, downloadable, metadata_layer,
    default_date, time_enabled, time_style_pattern, raster_periodicity, hide_periodicity,
    default_zoom, zoom_range, search_tags, searchable_fields,
    has_municipio, has_direccion, municipio_field, direccion_field, infobox_config, updated_by
) VALUES (
    :id, :parent_id, :label, :sort_order, :node_type, :hidden_in_menu, :disabled,
    :workspace_alias, :geoserver_layer, :styles, :cql_filter, :wms_group,
    :wfs_available, :wfs_layer_name, :downloadable, :metadata_layer,
    CAST(:default_date AS jsonb), :time_enabled, :time_style_pattern,
    CAST(:raster_periodicity AS jsonb), :hide_periodicity,
    CAST(:default_zoom AS jsonb), CAST(:zoom_range AS jsonb),
    :search_tags, :searchable_fields,
    :has_municipio, :has_direccion, :municipio_field, :direccion_field,
    CAST(:infobox_config AS jsonb), :updated_by
)
ON CONFLICT (id) DO UPDATE SET
    parent_id = EXCLUDED.parent_id,
    label = EXCLUDED.label,
    sort_order = EXCLUDED.sort_order,
    node_type = EXCLUDED.node_type,
    hidden_in_menu = EXCLUDED.hidden_in_menu,
    disabled = EXCLUDED.disabled,
    workspace_alias = EXCLUDED.workspace_alias,
    geoserver_layer = EXCLUDED.geoserver_layer,
    styles = EXCLUDED.styles,
    cql_filter = EXCLUDED.cql_filter,
    wms_group = EXCLUDED.wms_group,
    wfs_available = EXCLUDED.wfs_available,
    wfs_layer_name = EXCLUDED.wfs_layer_name,
    downloadable = EXCLUDED.downloadable,
    metadata_layer = EXCLUDED.metadata_layer,
    default_date = EXCLUDED.default_date,
    time_enabled = EXCLUDED.time_enabled,
    time_style_pattern = EXCLUDED.time_style_pattern,
    raster_periodicity = EXCLUDED.raster_periodicity,
    hide_periodicity = EXCLUDED.hide_periodicity,
    default_zoom = EXCLUDED.default_zoom,
    zoom_range = EXCLUDED.zoom_range,
    search_tags = EXCLUDED.search_tags,
    searchable_fields = EXCLUDED.searchable_fields,
    has_municipio = EXCLUDED.has_municipio,
    has_direccion = EXCLUDED.has_direccion,
    municipio_field = EXCLUDED.municipio_field,
    direccion_field = EXCLUDED.direccion_field,
    infobox_config = EXCLUDED.infobox_config,
    updated_at = NOW(),
    updated_by = EXCLUDED.updated_by
""")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()

    if not args.input.exists():
        print(f'ERROR: {args.input} no existe', file=sys.stderr)
        return 1

    data = json.loads(args.input.read_text())
    trees = data.get('layers') or []
    initial_order = data.get('initial_order') or []

    flat: list[dict] = []
    flatten_tree(trees, None, 0, flat)
    flat_sorted = sort_rows(flat)

    print(f'[seed] temas: {len(trees)}, total filas: {len(flat_sorted)}, initial_order: {len(initial_order)}')

    if not args.apply:
        print('[seed] DRY-RUN — usa --apply para persistir')
        return 0

    url = os.getenv('DATAENGINE_URL') or _build_url()
    if not url:
        print('ERROR: configurar DATAENGINE_URL o MAPALAB_CARD_DB_*', file=sys.stderr)
        return 1

    engine = create_engine(url)
    try:
        with engine.begin() as conn:
            for row in flat_sorted:
                payload = dict(row)
                for k in ('default_date', 'raster_periodicity', 'default_zoom', 'zoom_range', 'infobox_config'):
                    payload[k] = json.dumps(payload[k]) if payload[k] is not None else None
                payload['updated_by'] = 'bootstrap'
                conn.execute(_UPSERT_LAYER, payload)

            conn.execute(text('DELETE FROM mapalab.initial_layer_order'))
            for sort_order, layer_id in enumerate(initial_order):
                conn.execute(
                    text('INSERT INTO mapalab.initial_layer_order (layer_id, sort_order) VALUES (:lid, :so) ON CONFLICT (layer_id) DO UPDATE SET sort_order = EXCLUDED.sort_order'),
                    {'lid': layer_id, 'so': sort_order},
                )
        print(f'[seed] OK — {len(flat_sorted)} capas + {len(initial_order)} initial_order')
        return 0
    finally:
        engine.dispose()


def _build_url() -> str | None:
    user = os.getenv('MAPALAB_CARD_DB_USER')
    pwd = os.getenv('MAPALAB_CARD_DB_PASSWORD')
    host = os.getenv('MAPALAB_CARD_DB_HOST')
    port = os.getenv('MAPALAB_CARD_DB_PORT', '5432')
    db = os.getenv('MAPALAB_CARD_DB_NAME')
    sslmode = os.getenv('MAPALAB_CARD_DB_SSLMODE', 'require')
    if not (user and pwd and host and db):
        return None
    return f'postgresql://{user}:{pwd}@{host}:{port}/{db}?sslmode={sslmode}'


if __name__ == '__main__':
    sys.exit(main())
