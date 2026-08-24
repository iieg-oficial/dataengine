"""columna fid en las vistas materializadas, para que GeoServer pagine

73 de las 118 capas WFS que publica sextante estan montadas sobre vistas
materializadas sin clave primaria, y GeoServer rechaza con 400 cualquier
`GetFeature` con `STARTINDEX`. Un poligono sobre `delitos_fiscalia_robo_persona`
cruza 88 702 registros y solo devuelve la primera pagina.

La `0039` asumia que las matviews traian columna `fid` y solo habia que
indexarla. Verificado contra la base el 2026-08-21: **ninguna de las 83 la
tiene**, ni ellas ni sus tablas base, asi que aquella migracion es un no-op. El
identificador hay que fabricarlo.

Tampoco sirve una llave natural: las once columnas de una matview de delitos no
la forman —dos delitos del mismo tipo, el mismo dia y en el mismo punto son dos
filas identicas—, asi que se numera con `row_number() OVER ()`.

Comprobado el 2026-08-24 antes de escribir esto, publicando una matview de
prueba con un unico indice sobre `fid`: GeoTools resuelve la clave por heuristica
sobre indices unicos, sin necesidad de `gt_pk_metadata`. `GetFeature` con
`startIndex=5&count=2` devolvio 200 y los ids `pk_probe.6` y `pk_probe.7`.

Postgres no permite agregar una columna a una vista materializada, asi que cada
una se reconstruye: se crea al lado envolviendo su propia definicion, se cambia
por la original y se le devuelven indices y permisos. La definicion, los indices
y los grants se leen del catalogo, porque este repo no declara estas vistas.

**Pesada: 39 GB en 83 vistas.** Va en ventana de mantenimiento. Cada vista queda
bloqueada mientras se reconstruye y `alembic` corre todo en una transaccion.

Revision ID: 0042_matviews_fid
Revises: 0041_cabeceras_clave_geo
Create Date: 2026-08-24
"""
from alembic import op
import sqlalchemy as sa


revision = "0042_matviews_fid"
down_revision = "0041_cabeceras_clave_geo"
branch_labels = None
depends_on = None


_SIN_FID = """
SELECT n.nspname AS esquema, c.relname AS vista
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind = 'm'
  AND NOT EXISTS (
    SELECT 1 FROM pg_attribute a
    WHERE a.attrelid = c.oid AND a.attname = 'fid'
      AND a.attnum > 0 AND NOT a.attisdropped
  )
ORDER BY n.nspname, c.relname
"""


def _indices(bind, esquema: str, vista: str) -> list[str]:
    filas = bind.execute(sa.text(
        "SELECT indexdef FROM pg_indexes WHERE schemaname = :e AND tablename = :v"
    ), {"e": esquema, "v": vista}).fetchall()
    return [f[0] for f in filas]


def _grants(bind, esquema: str, vista: str) -> list[str]:
    filas = bind.execute(sa.text(
        "SELECT pg_get_userbyid(g.grantee) AS rol, g.privilege_type "
        "FROM pg_class c "
        "JOIN pg_namespace n ON n.oid = c.relnamespace, "
        "LATERAL aclexplode(c.relacl) AS g "
        "WHERE n.nspname = :e AND c.relname = :v "
        "  AND g.grantee <> 0 AND pg_get_userbyid(g.grantee) <> current_user"
    ), {"e": esquema, "v": vista}).fetchall()
    return [f'GRANT {p} ON "{esquema}"."{vista}" TO "{rol}"' for rol, p in filas]


def upgrade() -> None:
    bind = op.get_bind()
    vistas = bind.execute(sa.text(_SIN_FID)).fetchall()

    for esquema, vista in vistas:
        definicion = bind.execute(sa.text(
            "SELECT definition FROM pg_matviews WHERE schemaname = :e AND matviewname = :v"
        ), {"e": esquema, "v": vista}).scalar()
        if not definicion:
            continue

        indices = _indices(bind, esquema, vista)
        grants = _grants(bind, esquema, vista)
        cuerpo = definicion.strip().rstrip(";")
        temporal = f"{vista}__fid"

        op.execute(
            f'CREATE MATERIALIZED VIEW "{esquema}"."{temporal}" AS '
            f"SELECT row_number() OVER () AS fid, origen.* FROM ({cuerpo}) AS origen"
        )
        op.execute(f'DROP MATERIALIZED VIEW "{esquema}"."{vista}"')
        op.execute(
            f'ALTER MATERIALIZED VIEW "{esquema}"."{temporal}" '
            f'RENAME TO "{vista}"'
        )
        op.execute(
            f'CREATE UNIQUE INDEX "uidx_{vista}_fid" ON "{esquema}"."{vista}" (fid)'
        )
        for indexdef in indices:
            op.execute(indexdef)
        for grant in grants:
            op.execute(grant)
        op.execute(f'ANALYZE "{esquema}"."{vista}"')


def downgrade() -> None:
    bind = op.get_bind()
    vistas = bind.execute(sa.text(
        "SELECT n.nspname, c.relname FROM pg_class c "
        "JOIN pg_namespace n ON n.oid = c.relnamespace "
        "JOIN pg_attribute a ON a.attrelid = c.oid AND a.attname = 'fid' "
        "  AND a.attnum > 0 AND NOT a.attisdropped "
        "WHERE c.relkind = 'm'"
    )).fetchall()

    for esquema, vista in vistas:
        definicion = bind.execute(sa.text(
            "SELECT definition FROM pg_matviews WHERE schemaname = :e AND matviewname = :v"
        ), {"e": esquema, "v": vista}).scalar()
        if not definicion or "row_number() OVER ()" not in definicion:
            continue
        indices = [i for i in _indices(bind, esquema, vista) if f"uidx_{vista}_fid" not in i]
        grants = _grants(bind, esquema, vista)
        cuerpo = definicion.strip().rstrip(";")
        temporal = f"{vista}__sinfid"

        columnas = bind.execute(sa.text(
            "SELECT a.attname FROM pg_attribute a "
            "JOIN pg_class c ON c.oid = a.attrelid "
            "JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = :e AND c.relname = :v AND a.attnum > 0 "
            "  AND NOT a.attisdropped AND a.attname <> 'fid' "
            "ORDER BY a.attnum"
        ), {"e": esquema, "v": vista}).fetchall()
        lista = ", ".join(f'origen."{c[0]}"' for c in columnas)

        op.execute(
            f'CREATE MATERIALIZED VIEW "{esquema}"."{temporal}" AS '
            f"SELECT {lista} FROM ({cuerpo}) AS origen"
        )
        op.execute(f'DROP MATERIALIZED VIEW "{esquema}"."{vista}"')
        op.execute(f'ALTER MATERIALIZED VIEW "{esquema}"."{temporal}" RENAME TO "{vista}"')
        for indexdef in indices:
            op.execute(indexdef)
        for grant in grants:
            op.execute(grant)
