import pandas as pd
from dataclasses import dataclass


@dataclass
class MapalabCardMapper:
    dict_map_columns = {
        "Tema": "tema",
        "Subtema": "subtema",
        "Link final de la capa": "link_final_capa",
        "Capa Descargable": "capa_descargable",
        "Capa finalizada en Geoserver": "capa_finalizada_geoserver",
        "Nombre de la capa en BD": "nombre_capa_db",
        "Nombre de la capa en GeoServer": "nombre_capa_geoserver",
        "Nombre de la capa para el usuario": "nombre_capa_usuario",
        "Descripción (número de caracteres recomendado 255-300)": "descripcion",
        "Frecuencia de actualización": "frecuencia_actualizacion",
        "Fecha de última actualización IIEG": "fecha_ultima_actualizacion",
        "Numeralia 01 - Valor": "numeralia_01_valor",
        "Numeralia 01 - Nombre": "numeralia_01_nombre",
        "Numeralia 01 - Simbolo": "numeralia_01_simbolo",
        "Numeralia 02 - Valor": "numeralia_02_valor",
        "Numeralia 02 - Nombre": "numeralia_02_nombre",
        "Numeralia 02 - Simbolo": "numeralia_02_simbolo",
        "Numeralia 03 - Valor": "numeralia_03_valor",
        "Numeralia 03 - Nombre": "numeralia_03_nombre",
        "Numeralia 03 - Simbolo": "numeralia_03_simbolo",
        "Numeralia 04 - Valor": "numeralia_04_valor",
        "Numeralia 04 - Nombre": "numeralia_04_nombre",
        "Numeralia 04 - Simbolo": "numeralia_04_simbolo",
        "Numeralia 05 - Valor": "numeralia_05_valor",
        "Numeralia 05 - Nombre": "numeralia_05_nombre",
        "Numeralia 05 - Simbolo": "numeralia_05_simbolo",
        "Numeralia 06 - Valor": "numeralia_06_valor",
        "Numeralia 06 - Nombre": "numeralia_06_nombre",
        "Numeralia 06 - Simbolo": "numeralia_06_simbolo",
        "Numeralia 07 - Valor": "numeralia_07_valor",
        "Numeralia 07 - Nombre": "numeralia_07_nombre",
        "Numeralia 07 - Simbolo": "numeralia_07_simbolo",
        "Numeralia 08 - Valor": "numeralia_08_valor",
        "Numeralia 08 - Nombre": "numeralia_08_nombre",
        "Numeralia 08 - Simbolo": "numeralia_08_simbolo",
        "Nota al pie de numeralia (rango de fechas que comprende)": "nombre_pie_numeralia",
        "Metodología texto corto/ fórmula (número de caracteres)": "metodologia_texto",
        "Metodología archivo/enlace": "metodologia_archivo_enlace",
        "Fuentes (texto largo)": "fuentes_texto_largo",
        "Fuente (Texto corto Descargable PDF)": "fuentes_texto_corto",
        "Fuentes (enlace)": "fuentes_enlace",
        "Tipo de mapa (IIEG/INEGI)": "tipo_mapa",
        "Texto Leyenda Jurídico": "texto_leyenda_juridico",
        "Tipo de mapa (enlace)": "tipo_mapa_enlace",
        "Metadato .txt": "metadato_txt",
        "Metadato .xlsx": "metadato_xlsx",
        "Tarjeta de punto/poligono": "tarjeta_punto_poligono",
    }

    def clean_csv(self, df: pd.DataFrame) -> pd.DataFrame:
        df.columns = df.columns.str.strip()
        df = df.rename(columns=self.dict_map_columns)

        if 'fecha_ultima_actualizacion' in df.columns:
            df['fecha_ultima_actualizacion'] = df['fecha_ultima_actualizacion'].astype(str).str.strip()
            df['fecha_ultima_actualizacion'] = df['fecha_ultima_actualizacion'].apply(
                lambda v: pd.to_datetime(v, format='%d/%m/%Y', errors='coerce').strftime('%Y-%m-%d')
                if '/' in str(v) else (v if v and v not in ('', 'nan', 'None', 'NaT') else None)
            )

        valid_columns = set(self.dict_map_columns.values())
        for col in list(df.columns):
            if col not in valid_columns:
                df.drop(col, axis=1, inplace=True)

        return df
