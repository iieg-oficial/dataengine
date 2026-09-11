"""las fechas anuales de las tarjetitas se muestran como año

El visor de mapalab gana un `formato: 'anio'` por campo: en cualquier renglón,
etiqueta, ícono o párrafo de la tarjetita, `2024-01-01` se pinta como `2024`.
Esta migración lo pone donde hace falta, para que nadie tenga que hacerlo capa
por capa.

Dos criterios, uno por tipo de bloque:

- **Renglones de lista** sobre `fecha` cuya etiqueta empieza con «Año»
  —«Año de la información», «Año del cálculo»—. La etiqueta ya declara que se
  quiere el año. Hasta ahora lo resolvía el visor adivinando por el texto de la
  etiqueta, y solo para «Año de la información».
- **Etiquetas de un grupo** sobre `fecha` en capas **anuales**: las que en
  `public.layer_periodicity` solo tienen fechas en 01-01 o en 12-31. Una
  etiqueta no tiene texto que declare nada, así que la granularidad sale del dato.

Las capas mensuales se quedan como están a propósito: ahí el año solo sería
incorrecto. Si `public.layer_periodicity` no existe o está vacía, el segundo
criterio no marca nada y la migración sigue siendo segura.

La llave de la periodicidad es `db_schema:geoserver_layer`, la misma que arma
`mapalab/backend/app/services/periodicity_service.py::_resolve_layer_key`, no el
alias del workspace: con el alias no casan capas como las de `general`, cuyo
esquema es `mapa_base`.

Recorre `mapalab.layers` y `mapalab.catalogo_capas`. Solo agrega el formato donde
falta, así que aplicarla dos veces no cambia nada.

**Borra `mapalab.layer_tree_cache`**, igual que la `0035`: el árbol del visor se
sirve desde esa tabla y sin el DELETE el cambio no llega. El catálogo cachea en
memoria con TTL y se renueva solo.

**Id no numérico a propósito.** En `tamal-rojo` la `0036_layer_geometry_type`
también sale de la `0035`; con un `0036` aquí habría dos revisiones distintas
con el mismo número. Al propagar a rojo hace falta una revisión de merge.

Revision ID: 0035a_formato_anio_tarjetitas
Revises: 0035_curvas_render_catalogo
Create Date: 2026-09-11
"""
import json
import re
from typing import Any

import sqlalchemy as sa
from alembic import op

revision = "0035a_formato_anio_tarjetitas"
down_revision = "0035_curvas_render_catalogo"
branch_labels = None
depends_on = None

COLUMNA = "fecha"
FORMATO = "anio"
ETIQUETA_DE_ANIO = re.compile(r"^\s*a[ñn]o\b", re.IGNORECASE)
LIMITES_DE_ANIO = {(1, 1), (12, 31)}
TABLAS = ("layers", "catalogo_capas")


def _json(valor: Any) -> Any:
    return json.loads(valor) if isinstance(valor, str) else valor


def es_anual(periodicidad: dict | None) -> bool:
    if not periodicidad:
        return False
    fechas = {
        (int(mes), int(dia))
        for meses in periodicidad.values()
        for mes, dias in (meses or {}).items()
        for dia in (dias or [1])
    }
    return bool(fechas) and fechas <= LIMITES_DE_ANIO


def _bloques(valor: Any) -> list:
    if not isinstance(valor, list):
        return []
    if valor and isinstance(valor[0], dict) and isinstance(valor[0].get("items"), list):
        return [item for bloque in valor for item in bloque["items"]]
    return valor


def marcar_config(config: dict, anual: bool) -> int:
    cambios = 0
    for renglon in _bloques(config.get("list")):
        if (
            isinstance(renglon, dict)
            and renglon.get("field") == COLUMNA
            and ETIQUETA_DE_ANIO.match(renglon.get("label") or "")
            and not renglon.get("formato")
        ):
            renglon["formato"] = FORMATO
            cambios += 1
    if not anual:
        return cambios
    for grupo in _bloques(config.get("labelGroups")):
        campos = grupo.get("fields") if isinstance(grupo, dict) else None
        if not isinstance(campos, list):
            continue
        for i, campo in enumerate(campos):
            if campo == COLUMNA:
                campos[i] = {"field": COLUMNA, "formato": FORMATO}
                cambios += 1
            elif isinstance(campo, dict) and campo.get("field") == COLUMNA and not campo.get("formato"):
                campo["formato"] = FORMATO
                cambios += 1
    return cambios


def desmarcar_config(config: dict) -> int:
    cambios = 0
    for renglon in _bloques(config.get("list")):
        if (
            isinstance(renglon, dict)
            and renglon.get("field") == COLUMNA
            and renglon.get("formato") == FORMATO
        ):
            del renglon["formato"]
            cambios += 1
    for grupo in _bloques(config.get("labelGroups")):
        campos = grupo.get("fields") if isinstance(grupo, dict) else None
        if not isinstance(campos, list):
            continue
        for i, campo in enumerate(campos):
            if isinstance(campo, dict) and campo.get("field") == COLUMNA and campo.get("formato") == FORMATO:
                if set(campo) == {"field", "formato"}:
                    campos[i] = COLUMNA
                else:
                    del campo["formato"]
                cambios += 1
    return cambios


def _periodicidades(conn: sa.engine.Connection) -> dict[str, dict]:
    existe = conn.execute(sa.text("SELECT to_regclass('public.layer_periodicity')")).scalar()
    if not existe:
        return {}
    filas = conn.execute(sa.text("SELECT layer_key, periodicity FROM public.layer_periodicity")).all()
    return {llave: _json(periodicidad) for llave, periodicidad in filas}


def _esquemas(conn: sa.engine.Connection) -> dict[str, str]:
    filas = conn.execute(
        sa.text(
            "SELECT alias, COALESCE(NULLIF(db_schema, ''), geoserver_workspace) FROM mapalab.workspaces"
        )
    ).all()
    return dict(filas)


def _recorrer(conn: sa.engine.Connection, transformar) -> None:
    for tabla in TABLAS:
        filas = conn.execute(
            sa.text(
                f"SELECT id, workspace_alias, geoserver_layer, infobox_config "
                f"FROM mapalab.{tabla} WHERE infobox_config IS NOT NULL"
            )
        ).all()
        for id_, alias, capa, config in filas:
            config = _json(config)
            if not isinstance(config, dict):
                continue
            if transformar(config, alias, capa):
                conn.execute(
                    sa.text(
                        f"UPDATE mapalab.{tabla} "
                        f"SET infobox_config = CAST(:config AS jsonb), updated_at = now() "
                        f"WHERE id = :id"
                    ),
                    {"config": json.dumps(config, ensure_ascii=False), "id": id_},
                )
    conn.execute(sa.text("DELETE FROM mapalab.layer_tree_cache"))


def upgrade() -> None:
    conn = op.get_bind()
    periodicidades = _periodicidades(conn)
    esquemas = _esquemas(conn)

    def transformar(config: dict, alias: str | None, capa: str | None) -> int:
        llave = f"{esquemas.get(alias, alias)}:{capa}" if alias and capa else None
        return marcar_config(config, es_anual(periodicidades.get(llave)))

    _recorrer(conn, transformar)


def downgrade() -> None:
    _recorrer(op.get_bind(), lambda config, _alias, _capa: desmarcar_config(config))
