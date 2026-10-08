"""declarar el campo de municipio en las capas que ya lo tienen en su tabla

Las migraciones `0023`, `0040`, `0041` y `0042` dejaron el dato en la base, pero
ninguna declaro nada en `mapalab.layers`: sin `has_municipio`, `municipio_field`
y `municipio_field_type`, el visor sigue recortando esas capas con el `BBOX` de
la seleccion, que es un rectangulo y arrastra features de municipios vecinos.

Esa configuracion se edita normalmente desde mariachi, pero son mas de 180 capas
y hacerlas a mano en cada entorno no es realista ni reproducible. Va aqui, que es
donde vive el DDL del schema `mapalab`.

**No trae una lista de ids**, porque los ids y el catalogo cambian entre
entornos: recorre las capas vivas, resuelve su tabla via `mapalab.workspaces` y
elige el campo comprobando **los valores**, no el nombre de la columna.

Esa comprobacion es la parte importante, y sale de dos casos reales:

- `mapa_base.cabeceras_municipales` tenia una columna llamada `clave_municipio`
  con la clave **sin prefijo de estado** —`01`, `02`— que no empata con ninguna
  clave de cinco digitos. Por nombre habria pasado como buena y la capa se
  habria vaciado al elegir municipio.
- En trece capas —aeropuertos, cuerpos de agua, rutas de eventos— la columna
  `nombre` es el nombre **del propio elemento**, no el del municipio.

Por eso cada candidata se acepta solo si al menos el 90 % de sus valores
distintos empata contra `mapalab.municipios`: por `clave_geo` para las de clave,
y por nombre normalizado —sin acentos, sin mayusculas— para las de nombre. Se
prefiere siempre la clave, que sobrevive a un rename del municipio.

Es idempotente: solo toca las capas que aun no declaran nada.

Despues de aplicarla hay que recargar el catalogo de GeoServer y correr
`run_refresh_layer_tree.py`, o el visor seguira leyendo el arbol viejo.

Revision ID: 0043_declarar_municipio_en_capas
Revises: 0042_puntos_clave_municipio
Create Date: 2026-08-24
"""
from alembic import op
import sqlalchemy as sa


revision = "0043_declarar_municipio_en_capas"
down_revision = "0042_puntos_clave_municipio"
branch_labels = None
depends_on = None

_UMBRAL = 0.9

_CANDIDATAS: tuple[tuple[str, str], ...] = (
    ("clave_municipio", "clave"),
    ("clave_geo", "clave"),
    ("municipio", "nombre"),
    ("nombre", "nombre"),
)

_NORMALIZA = "lower(trim(translate({col}, 'áéíóúüñÁÉÍÓÚÜÑ', 'aeiouunAEIOUUN')))"

_CAPAS = """
SELECT l.id, w.db_schema, l.geoserver_layer
FROM mapalab.layers l
JOIN mapalab.workspaces w ON w.alias = l.workspace_alias
WHERE l.deleted_at IS NULL
  AND NOT l.has_municipio
  AND l.geoserver_layer IS NOT NULL
  AND l.geoserver_layer <> ''
"""


def _tiene_columna(bind, esquema: str, tabla: str, columna: str) -> bool:
    return bool(bind.execute(sa.text(
        "SELECT 1 FROM pg_attribute a "
        "JOIN pg_class c ON c.oid = a.attrelid "
        "JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname = :e AND c.relname = :t AND a.attname = :c "
        "  AND a.attnum > 0 AND NOT a.attisdropped"
    ), {"e": esquema, "t": tabla, "c": columna}).scalar())


def _empata(bind, esquema: str, tabla: str, columna: str, tipo: str) -> bool:
    if tipo == "clave":
        cond = "v.valor IN (SELECT clave_geo FROM mapalab.municipios)"
        valor = f'"{columna}"'
    else:
        cond = (
            "v.valor IN (SELECT " + _NORMALIZA.format(col="nombre")
            + " FROM mapalab.municipios)"
        )
        valor = _NORMALIZA.format(col=f'"{columna}"')

    fila = bind.execute(sa.text(
        f'WITH v AS (SELECT DISTINCT {valor} AS valor '
        f'FROM "{esquema}"."{tabla}" WHERE "{columna}" IS NOT NULL LIMIT 500) '
        f"SELECT count(*) AS total, count(*) FILTER (WHERE {cond}) AS empatan FROM v"
    )).first()
    if not fila or not fila.total:
        return False
    return (fila.empatan / fila.total) >= _UMBRAL


def upgrade() -> None:
    bind = op.get_bind()
    declaradas = 0

    for capa_id, esquema, tabla in bind.execute(sa.text(_CAPAS)).fetchall():
        if bind.execute(
            sa.text(f"SELECT to_regclass('{esquema}.{tabla}')")
        ).scalar() is None:
            continue

        for columna, tipo in _CANDIDATAS:
            if not _tiene_columna(bind, esquema, tabla, columna):
                continue
            if not _empata(bind, esquema, tabla, columna, tipo):
                continue
            bind.execute(sa.text(
                "UPDATE mapalab.layers SET has_municipio = true, "
                "municipio_field = :campo, municipio_field_type = :tipo, "
                "updated_at = now() WHERE id = :id"
            ), {"campo": columna, "tipo": tipo, "id": capa_id})
            declaradas += 1
            break

    print(f"capas declaradas: {declaradas}")


def downgrade() -> None:
    op.execute(
        "UPDATE mapalab.layers SET has_municipio = false, municipio_field = NULL, "
        "municipio_field_type = NULL WHERE deleted_at IS NULL AND has_municipio"
    )
