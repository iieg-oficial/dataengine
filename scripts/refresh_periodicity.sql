CREATE TABLE IF NOT EXISTS public.layer_periodicity (
    layer_key TEXT PRIMARY KEY,
    periodicity JSONB NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

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
        periodicity JSONB NOT NULL
    ) ON COMMIT DROP;

    FOR rec IN
        SELECT n.nspname AS schema_name, c.relname AS table_name,
               t.typname AS col_type
        FROM pg_attribute a
        JOIN pg_class c ON c.oid = a.attrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        JOIN pg_type t ON t.oid = a.atttypid
        WHERE a.attname = 'fecha'
          AND a.attnum > 0
          AND c.relkind IN ('r', 'm', 'v')
          AND n.nspname != ALL(exclude_schemas)
        ORDER BY n.nspname, c.relname
    LOOP
        BEGIN
            IF rec.col_type IN ('date', 'timestamp', 'timestamptz') THEN
                fecha_expr := 'fecha';
            ELSE
                fecha_expr := 'fecha::date';
            END IF;

            dyn_sql := format(
                'WITH dates AS (
                    SELECT DISTINCT
                        EXTRACT(YEAR FROM %s)::int AS y,
                        EXTRACT(MONTH FROM %s)::int AS m,
                        EXTRACT(DAY FROM %s)::int AS d
                    FROM %I.%I
                    WHERE fecha IS NOT NULL
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
                rec.schema_name, rec.table_name
            );

            EXECUTE dyn_sql INTO result;

            IF result IS NOT NULL THEN
                INSERT INTO _periodicity_batch (layer_key, periodicity)
                VALUES (rec.schema_name || ':' || rec.table_name, result);
            END IF;

        EXCEPTION WHEN OTHERS THEN
            RAISE WARNING 'Error processing %.%: %', rec.schema_name, rec.table_name, SQLERRM;
        END;
    END LOOP;

    DELETE FROM public.layer_periodicity;
    INSERT INTO public.layer_periodicity (layer_key, periodicity, updated_at)
    SELECT layer_key, periodicity, now()
    FROM _periodicity_batch;
END;
$$;

SELECT public.refresh_layer_periodicity();
