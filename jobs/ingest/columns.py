from typing import Any


TRUE_VALUES = {"1", "true", "t", "yes", "sí", "si", "y"}
FALSE_VALUES = {"0", "false", "f", "no", "n"}

SCALAR_COLUMNS = (
    "layer_key",
    "workspace",
    "layer_name_db",
    "layer_name_usuario",
    "descripcion",
    "frecuencia",
    "fecha_ultima",
    "tipo_mapa",
    "tipo_mapa_enlace",
    "texto_leyenda",
    "tarjeta_punto_poligono",
    "link_final_capa",
)

JSONB_COLUMNS = ("fuentes", "metodologia", "metadato")
BOOL_COLUMNS = ("downloadable",)
PK_COLUMN = "layer_key"


def clean(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    if not s or s.lower() in ("nan", "none", "null"):
        return None
    return s


def parse_bool(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    s = str(value).strip().lower()
    if s in TRUE_VALUES:
        return True
    if s in FALSE_VALUES:
        return False
    return None


def build_fuentes(row: dict) -> dict | None:
    corto = clean(row.get("fuentes_corto"))
    largo = clean(row.get("fuentes_largo"))
    enlace = clean(row.get("fuentes_enlace"))
    if not any([corto, largo, enlace]):
        return None
    result: dict[str, str] = {}
    if corto:
        result["corto"] = corto
    if largo:
        result["largo"] = largo
    if enlace:
        result["enlace"] = enlace
    return result


def build_metodologia(row: dict) -> dict | None:
    texto = clean(row.get("metodologia_texto"))
    enlace = clean(row.get("metodologia_archivo_enlace"))
    if not any([texto, enlace]):
        return None
    result: dict[str, str] = {}
    if texto:
        result["texto"] = texto
    if enlace:
        result["archivo_enlace"] = enlace
    return result


def build_metadato(row: dict) -> list[dict] | None:
    items: list[dict] = []
    txt = clean(row.get("metadato_txt"))
    xlsx = clean(row.get("metadato_xlsx"))
    if txt:
        items.append({"nombre": "Metadato TXT", "enlace": txt})
    if xlsx:
        items.append({"nombre": "Metadato XLSX", "enlace": xlsx})
    return items or None


def normalize_row(raw: dict) -> dict:
    out: dict[str, Any] = {}
    for col in SCALAR_COLUMNS:
        out[col] = clean(raw.get(col))
    out["fuentes"] = build_fuentes(raw)
    out["metodologia"] = build_metodologia(raw)
    out["metadato"] = build_metadato(raw)
    for col in BOOL_COLUMNS:
        out[col] = parse_bool(raw.get(col))
    return out


def expected_headers() -> list[str]:
    return [
        *SCALAR_COLUMNS,
        "fuentes_corto",
        "fuentes_largo",
        "fuentes_enlace",
        "metodologia_texto",
        "metodologia_archivo_enlace",
        "metadato_txt",
        "metadato_xlsx",
        *BOOL_COLUMNS,
    ]


def unknown_columns(headers: list[str]) -> list[str]:
    valid = set(expected_headers())
    return [h for h in headers if h and h not in valid]
