"""indice GiST en las columnas de geometria de las vistas materializadas

Las 83 matviews tematicas (`demografia.poblacion`, `desarrollo_social.pobreza`,
`seguridad_y_proteccion_ciudadana.*`, ...) se crean fuera de Alembic y ninguna
salvo `mapalab.municipios` llevaba indice espacial. Cada una repite la geometria
completa del municipio por cada periodo, asi que pesan ~1.25 GB con solo ~17 000
filas, y **cada tile hacia un Seq Scan de la vista entera**.

Medido sobre `seguridad_y_proteccion_ciudadana.personas_localizadas`, con el
envelope de un tile de 256 px a z=11:

    sin indice   Seq Scan, 63 961 buffers, 705.9 ms
    con indice   Bitmap Index Scan, 21 buffers, 0.769 ms

El indice se crea sobre cada columna `geometry` que no tenga ya uno GiST, en
todas las matviews de la base. Se hace en un DO block y no con una lista fija
porque las vistas no las declara este repo: si mañana se agrega una tematica
nueva, basta con volver a aplicar esta logica.

`REFRESH MATERIALIZED VIEW` reconstruye los indices, asi que no hay que
recrearlos despues de cada refresco.

Revision ID: 0034_matviews_spatial_index
Revises: 0033_layer_render_defaults
Create Date: 2026-08-06
"""
from alembic import op


revision = "0034_matviews_spatial_index"
down_revision = "0033_layer_render_defaults"
branch_labels = None
depends_on = None


_SELECT_MISSING = """
SELECT n.nspname, c.relname, a.attname
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum > 0 AND NOT a.attisdropped
JOIN pg_type t ON t.oid = a.atttypid
WHERE c.relkind = 'm' AND t.typname = 'geometry'
  AND NOT EXISTS (
    SELECT 1 FROM pg_index i
    JOIN pg_class ic ON ic.oid = i.indexrelid
    JOIN pg_am am ON am.oid = ic.relam
    WHERE i.indrelid = c.oid AND am.amname = 'gist' AND a.attnum = ANY(i.indkey)
  )
"""


def upgrade() -> None:
    op.execute(
        f"""
        DO $$
        DECLARE r record;
        BEGIN
          FOR r IN {_SELECT_MISSING} LOOP
            EXECUTE format(
              'CREATE INDEX IF NOT EXISTS %I ON %I.%I USING gist (%I)',
              'sidx_' || r.relname || '_' || r.attname, r.nspname, r.relname, r.attname
            );
            EXECUTE format('ANALYZE %I.%I', r.nspname, r.relname);
          END LOOP;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        DECLARE r record;
        BEGIN
          FOR r IN
            SELECT n.nspname, ic.relname AS idxname
            FROM pg_index i
            JOIN pg_class ic ON ic.oid = i.indexrelid
            JOIN pg_class c ON c.oid = i.indrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            JOIN pg_am am ON am.oid = ic.relam
            WHERE c.relkind = 'm' AND am.amname = 'gist' AND ic.relname LIKE 'sidx_%'
          LOOP
            EXECUTE format('DROP INDEX IF EXISTS %I.%I', r.nspname, r.idxname);
          END LOOP;
        END $$;
        """
    )
