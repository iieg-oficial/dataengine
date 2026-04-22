import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, text


TRUE_VALUES = {'1', 'true', 't', 'yes', 'sí', 'si', 'y'}
FALSE_VALUES = {'0', 'false', 'f', 'no', 'n'}


def parse_bool(value) -> bool:
    if value is None:
        return True
    s = str(value).strip().lower()
    if s in TRUE_VALUES:
        return True
    if s in FALSE_VALUES:
        return False
    return True


def clean(value):
    if value is None:
        return None
    s = str(value).strip()
    if not s or s.lower() in ('nan', 'none', 'null'):
        return None
    return s


def build_fuentes(row):
    corto = clean(row.get('fuentes_texto_corto'))
    largo = clean(row.get('fuentes_texto_largo'))
    enlace = clean(row.get('fuentes_enlace'))
    if not any([corto, largo, enlace]):
        return None
    result = {}
    if corto: result['corto'] = corto
    if largo: result['largo'] = largo
    if enlace: result['enlace'] = enlace
    return result


def build_metodologia(row):
    texto = clean(row.get('metodologia_texto'))
    enlace = clean(row.get('metodologia_archivo_enlace'))
    if not any([texto, enlace]):
        return None
    result = {}
    if texto: result['texto'] = texto
    if enlace: result['archivo_enlace'] = enlace
    return result


def build_metadato(row):
    items = []
    txt = clean(row.get('metadato_txt'))
    xlsx = clean(row.get('metadato_xlsx'))
    if txt: items.append({'nombre': 'Metadato TXT', 'enlace': txt})
    if xlsx: items.append({'nombre': 'Metadato XLSX', 'enlace': xlsx})
    return items or None


def build_numeralia(row):
    values = []
    for i in range(1, 9):
        valor = clean(row.get(f'numeralia_0{i}_valor'))
        nombre = clean(row.get(f'numeralia_0{i}_nombre'))
        simbolo = clean(row.get(f'numeralia_0{i}_simbolo'))
        if valor or nombre:
            values.append({'posicion': i, 'valor': valor, 'nombre': nombre, 'simbolo': simbolo})
    return values


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()

    url = os.getenv('DATAENGINE_URL') or _build_url()
    if not url:
        print('ERROR: configurar DATAENGINE_URL o DATAENGINE_DB_*', file=sys.stderr)
        return 1

    engine = create_engine(url)
    try:
        with engine.begin() as conn:
            rows = conn.execute(text(
                "SELECT * FROM public.mapalab_card WHERE nombre_capa_geoserver IS NOT NULL "
                "AND nombre_capa_geoserver != ''"
            )).mappings().all()

            metadata_rows = []
            stats_rows = []
            seen = set()

            for row in rows:
                layer_key = clean(row['nombre_capa_geoserver'])
                if not layer_key or layer_key in seen:
                    continue
                seen.add(layer_key)

                workspace = layer_key.split(':', 1)[0] if ':' in layer_key else None
                metadata_rows.append({
                    'layer_key': layer_key,
                    'workspace': workspace,
                    'layer_name_db': clean(row.get('nombre_capa_db')),
                    'layer_name_usuario': clean(row.get('nombre_capa_usuario')),
                    'descripcion': clean(row.get('descripcion')),
                    'fuentes': build_fuentes(dict(row)),
                    'metodologia': build_metodologia(dict(row)),
                    'metadato': build_metadato(dict(row)),
                    'frecuencia': clean(row.get('frecuencia_actualizacion')),
                    'fecha_ultima': clean(row.get('fecha_ultima_actualizacion')),
                    'tipo_mapa': clean(row.get('tipo_mapa')),
                    'tipo_mapa_enlace': clean(row.get('tipo_mapa_enlace')),
                    'texto_leyenda': clean(row.get('texto_leyenda_juridico')),
                    'tarjeta_punto_poligono': clean(row.get('tarjeta_punto_poligono')),
                    'link_final_capa': clean(row.get('link_final_capa')),
                    'downloadable': parse_bool(row.get('capa_descargable')),
                })

                num = build_numeralia(dict(row))
                pie = clean(row.get('nombre_pie_numeralia'))
                if num or pie:
                    stats_rows.append({'layer_key': layer_key, 'values': num, 'pie_numeralia': pie})

            print(f'[migrate] fuente: {len(rows)}, metadata: {len(metadata_rows)}, stats: {len(stats_rows)}')

            if not args.apply:
                print('[migrate] DRY-RUN — usa --apply')
                return 0

            meta_upsert = text("""
                INSERT INTO mapalab.layer_metadata (
                    layer_key, workspace, layer_name_db, layer_name_usuario, descripcion,
                    fuentes, metodologia, metadato, frecuencia, fecha_ultima,
                    tipo_mapa, tipo_mapa_enlace, texto_leyenda, tarjeta_punto_poligono,
                    link_final_capa, downloadable, updated_by
                ) VALUES (
                    :layer_key, :workspace, :layer_name_db, :layer_name_usuario, :descripcion,
                    CAST(:fuentes AS jsonb), CAST(:metodologia AS jsonb), CAST(:metadato AS jsonb),
                    :frecuencia, :fecha_ultima, :tipo_mapa, :tipo_mapa_enlace, :texto_leyenda,
                    :tarjeta_punto_poligono, :link_final_capa, :downloadable, 'bootstrap'
                ) ON CONFLICT (layer_key) DO UPDATE SET
                    workspace = EXCLUDED.workspace,
                    descripcion = EXCLUDED.descripcion,
                    fuentes = EXCLUDED.fuentes,
                    metodologia = EXCLUDED.metodologia,
                    metadato = EXCLUDED.metadato,
                    frecuencia = EXCLUDED.frecuencia,
                    fecha_ultima = EXCLUDED.fecha_ultima,
                    tipo_mapa = EXCLUDED.tipo_mapa,
                    tipo_mapa_enlace = EXCLUDED.tipo_mapa_enlace,
                    texto_leyenda = EXCLUDED.texto_leyenda,
                    tarjeta_punto_poligono = EXCLUDED.tarjeta_punto_poligono,
                    link_final_capa = EXCLUDED.link_final_capa,
                    downloadable = EXCLUDED.downloadable,
                    updated_at = NOW()
            """)

            stats_upsert = text("""
                INSERT INTO mapalab.layer_stats (layer_key, stats_config, values, pie_numeralia)
                VALUES (:layer_key, '[]'::jsonb, CAST(:values AS jsonb), :pie_numeralia)
                ON CONFLICT (layer_key) DO UPDATE SET
                    values = EXCLUDED.values,
                    pie_numeralia = EXCLUDED.pie_numeralia
            """)

            for row in metadata_rows:
                payload = {**row}
                for k in ('fuentes', 'metodologia', 'metadato'):
                    payload[k] = json.dumps(payload[k]) if payload[k] else None
                conn.execute(meta_upsert, payload)

            for row in stats_rows:
                conn.execute(stats_upsert, {
                    'layer_key': row['layer_key'],
                    'values': json.dumps(row['values']),
                    'pie_numeralia': row['pie_numeralia'],
                })

        print(f'[migrate] OK — {len(metadata_rows)} metadata + {len(stats_rows)} stats')
        return 0
    finally:
        engine.dispose()


def _build_url() -> str | None:
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
