"""indice UNIQUE en fid para que GeoServer pagine las vistas materializadas

73 de las 118 capas WFS que publica sextante estan montadas sobre vistas
materializadas sin clave primaria. GeoServer rechaza con 400 cualquier
`GetFeature` que lleve `STARTINDEX`:

    Cannot do natural order without a primary key, please add it or specify
    a manual sort over existing attributes

Sin paginacion la consulta se queda en la primera pagina: un poligono sobre
`delitos_fiscalia_robo_persona` cruza 88 702 registros y solo devuelve 200.

El identificador ya existe y no hay que fabricarlo: las 82 matviews traen
columna `fid bigint`. Postgres no admite `ADD PRIMARY KEY` sobre una vista
materializada, solo indices, asi que la via es `CREATE UNIQUE INDEX (fid)`.
GeoTools resuelve la clave por heuristica sobre indices unicos.

Como en `0034_matviews_spatial_index`, la migracion descubre las vistas con un
`DO` block en vez de una lista fija: no las declara este repo, asi que una
tematica nueva queda cubierta con solo volver a aplicarla.

Antes de cada indice comprueba que `fid` sea realmente unico y no nulo en esa
vista. Un `CREATE UNIQUE INDEX` sobre datos duplicados aborta la transaccion
entera, y produccion no tiene por que traer los mismos datos que el espejo: la
vista que falle se omite con `WARNING` y las demas se aplican.

`REFRESH MATERIALIZED VIEW` reconstruye los indices, asi que no hay que
recrearlos despues de cada refresco.

Revision ID: 0039_matviews_unique_fid
Revises: 0038_hexbin_vista
Create Date: 2026-08-21
"""
from alembic import op


revision = "0039_matviews_unique_fid"
down_revision = "0038_hexbin_vista"
branch_labels = None
depends_on = None


_SELECT_CANDIDATAS = """
SELECT n.nspname, c.relname
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
JOIN pg_attribute a ON a.attrelid = c.oid AND a.attname = 'fid'
                   AND a.attnum > 0 AND NOT a.attisdropped
WHERE c.relkind = 'm'
  AND NOT EXISTS (
    SELECT 1 FROM pg_index i
    WHERE i.indrelid = c.oid AND i.indisunique
  )
ORDER BY n.nspname, c.relname
"""


def upgrade() -> None:
    op.execute(
        f"""
        DO $$
        DECLARE
          r record;
          duplicados bigint;
          nulos bigint;
          nombre text;
          creados int := 0;
          omitidos int := 0;
        BEGIN
          FOR r IN {_SELECT_CANDIDATAS} LOOP
            EXECUTE format(
              'SELECT count(*) FROM (SELECT fid FROM %I.%I GROUP BY fid HAVING count(*) > 1) d',
              r.nspname, r.relname
            ) INTO duplicados;
            EXECUTE format(
              'SELECT count(*) FROM %I.%I WHERE fid IS NULL', r.nspname, r.relname
            ) INTO nulos;

            IF duplicados > 0 OR nulos > 0 THEN
              RAISE WARNING 'omitida %.%: % fid duplicados, % nulos',
                r.nspname, r.relname, duplicados, nulos;
              omitidos := omitidos + 1;
              CONTINUE;
            END IF;

            nombre := left('uidx_' || r.relname || '_fid', 63);
            EXECUTE format(
              'CREATE UNIQUE INDEX IF NOT EXISTS %I ON %I.%I (fid)',
              nombre, r.nspname, r.relname
            );
            EXECUTE format('ANALYZE %I.%I', r.nspname, r.relname);
            creados := creados + 1;
          END LOOP;

          RAISE NOTICE 'indices unicos sobre fid creados: %, omitidos: %', creados, omitidos;
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
            WHERE c.relkind = 'm' AND i.indisunique AND ic.relname LIKE 'uidx\\_%\\_fid'
          LOOP
            EXECUTE format('DROP INDEX IF EXISTS %I.%I', r.nspname, r.idxname);
          END LOOP;
        END $$;
        """
    )
