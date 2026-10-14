CREATE TABLE IF NOT EXISTS public.layer_periodicity (
    layer_key TEXT PRIMARY KEY,
    periodicity JSONB NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
ALTER TABLE public.layer_periodicity ADD COLUMN IF NOT EXISTS date_column TEXT NOT NULL DEFAULT 'fecha';

CREATE OR REPLACE FUNCTION public.refresh_layer_periodicity()
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
    rec RECORD;
    dyn_sql TEXT;
    fecha_expr TEXT;
    result JSONB;
    exclude_schemas TEXT[] := ARRAY[
        'information_schema', 'pg_catalog', 'pg_toast',
        'tiger', 'tiger_data', 'topology', 'ogr_system_tables',
        'prueba', 'public', 'raster'
    ];
BEGIN
    CREATE TEMP TABLE _periodicity_batch (
        layer_key TEXT PRIMARY KEY,
        periodicity JSONB NOT NULL,
        date_column TEXT NOT NULL
    ) ON COMMIT DROP;

    CREATE TEMP TABLE _configured_date_column (
        schema_name TEXT NOT NULL,
        table_name TEXT NOT NULL,
        column_name TEXT NOT NULL
    ) ON COMMIT DROP;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'mapalab' AND table_name = 'layers' AND column_name = 'date_column'
    ) THEN
        EXECUTE 'INSERT INTO _configured_date_column (schema_name, table_name, column_name)
            SELECT DISTINCT w.db_schema, l.geoserver_layer, l.date_column
            FROM mapalab.layers l
            JOIN mapalab.workspaces w ON w.alias = l.workspace_alias
            WHERE l.deleted_at IS NULL
              AND l.geoserver_layer IS NOT NULL
              AND nullif(btrim(l.date_column), '''') IS NOT NULL';
    END IF;

    FOR rec IN
        WITH candidates AS (
            SELECT n.nspname AS schema_name, c.relname AS table_name,
                   a.attname AS column_name, t.typname AS col_type,
                   EXISTS (
                       SELECT 1 FROM _configured_date_column cfg
                       WHERE cfg.schema_name = n.nspname
                         AND cfg.table_name = c.relname
                         AND cfg.column_name = a.attname
                   ) AS by_config,
                   coalesce(col_description(c.oid, a.attnum), '') ILIKE '%mapalab:fecha%' AS by_comment,
                   a.attname = 'fecha' AS by_name
            FROM pg_attribute a
            JOIN pg_class c ON c.oid = a.attrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            JOIN pg_type t ON t.oid = a.atttypid
            WHERE a.attnum > 0
              AND NOT a.attisdropped
              AND c.relkind IN ('r', 'm', 'v')
              AND n.nspname != ALL(exclude_schemas)
        )
        SELECT DISTINCT ON (schema_name, table_name) schema_name, table_name, column_name, col_type
        FROM candidates
        WHERE by_config OR by_comment OR by_name
        ORDER BY schema_name, table_name, by_config DESC, by_comment DESC, column_name
    LOOP
        BEGIN
            IF rec.col_type IN ('date', 'timestamp', 'timestamptz') THEN
                fecha_expr := format('%I', rec.column_name);
            ELSE
                fecha_expr := format('%I::date', rec.column_name);
            END IF;

            dyn_sql := format(
                'WITH dates AS (
                    SELECT DISTINCT
                        EXTRACT(YEAR FROM %s)::int AS y,
                        EXTRACT(MONTH FROM %s)::int AS m,
                        EXTRACT(DAY FROM %s)::int AS d
                    FROM %I.%I
                    WHERE %I IS NOT NULL
                ),
                by_month AS (
                    SELECT y, m, jsonb_agg(d ORDER BY d) AS days
                    FROM dates GROUP BY y, m
                ),
                by_year AS (
                    SELECT y, jsonb_object_agg(m::text, days ORDER BY m) AS months
                    FROM by_month GROUP BY y
                )
                SELECT jsonb_object_agg(y::text, months ORDER BY y) FROM by_year',
                fecha_expr, fecha_expr, fecha_expr,
                rec.schema_name, rec.table_name, rec.column_name
            );

            EXECUTE dyn_sql INTO result;

            IF result IS NOT NULL THEN
                INSERT INTO _periodicity_batch (layer_key, periodicity, date_column)
                VALUES (rec.schema_name || ':' || rec.table_name, result, rec.column_name);
            END IF;

        EXCEPTION WHEN OTHERS THEN
            RAISE WARNING 'Error processing %.%: %', rec.schema_name, rec.table_name, SQLERRM;
        END;
    END LOOP;

    DELETE FROM public.layer_periodicity;
    INSERT INTO public.layer_periodicity (layer_key, periodicity, date_column, updated_at)
    SELECT layer_key, periodicity, date_column, now()
    FROM _periodicity_batch;
END;
$$;

SELECT public.refresh_layer_periodicity();
