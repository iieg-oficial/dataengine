"""schema atributos: configuracion de columnas de la tabla del visor

La tabla de atributos del visor lee las columnas por WFS y le llegan con el
nombre crudo de la base: `cve_mun`, `p_total`, `nom_loc`. Una tabla con esos
encabezados es hostil, y el alias no se deduce: lo escribe una persona. Eso es
lo unico de esa herramienta que necesita persistir. Las filas, los conteos y el
esquema de columnas salen del WFS en cada consulta y no se cachean aqui: seria
duplicar dataengine dentro de dataengine.

Va en un schema propio y no en `mapalab` para separar la configuracion de una
herramienta del visor del catalogo institucional del que dependen mariachi y el
resto del ecosistema. La ventaja concreta es la bajada: un DROP SCHEMA CASCADE
que no roza ninguna tabla del catalogo.

Los GRANT van en esta misma revision porque un schema nuevo no hereda nada. El
sintoma de olvidarlos es que el GET funciona y el POST responde 500 con
`permission denied for table`. El ALTER DEFAULT PRIVILEGES evita que la
siguiente tabla del schema repita el bug.

Una capa sin filas aqui tiene que seguir funcionando, con los nombres crudos en
el orden del WFS: ninguna capa nueva nace rota por no estar configurada.

Plan: `repos/mapalab/planes/tabla-de-atributos.md` del repo de contexto.

Revision ID: 0046_atributos_columnas
Revises: 0045_matviews_fid
Create Date: 2026-08-28
"""
from alembic import op


revision = "0046_atributos_columnas"
down_revision = "0045_matviews_fid"
branch_labels = None
depends_on = None

SCHEMA = "atributos"
ROL = "mariachi_layers"


def upgrade() -> None:
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA};")

    op.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.columnas (
            layer_key   text        NOT NULL,
            columna     text        NOT NULL,
            alias       text,
            orden       smallint    NOT NULL DEFAULT 0,
            visible     boolean     NOT NULL DEFAULT true,
            formato     text,
            updated_at  timestamptz NOT NULL DEFAULT NOW(),
            updated_by  text,
            PRIMARY KEY (layer_key, columna),
            CONSTRAINT columnas_formato_valido CHECK (
                formato IS NULL
                OR formato IN ('entero', 'decimal', 'fecha', 'moneda', 'texto')
            )
        );
        """
    )

    op.execute(
        f"CREATE INDEX IF NOT EXISTS columnas_layer_key_orden_idx "
        f"ON {SCHEMA}.columnas (layer_key, orden);"
    )

    op.execute(f"GRANT USAGE ON SCHEMA {SCHEMA} TO {ROL};")
    op.execute(
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA {SCHEMA} TO {ROL};"
    )
    op.execute(f"GRANT USAGE ON ALL SEQUENCES IN SCHEMA {SCHEMA} TO {ROL};")
    op.execute(
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA {SCHEMA} "
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {ROL};"
    )
    op.execute(
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA {SCHEMA} "
        f"GRANT USAGE ON SEQUENCES TO {ROL};"
    )


def downgrade() -> None:
    op.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE;")
