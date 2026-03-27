CREATE OR REPLACE FUNCTION public.check_layer_periodicity()
RETURNS TABLE (
    layer_key TEXT,
    status TEXT,
    source_dates BIGINT,
    stored_dates BIGINT
)
LANGUAGE plpgsql
AS $$
DECLARE
    rec RECORD;
    dyn_sql TEXT;
    fecha_expr TEXT;
    src_count BIGINT;
    stored JSONB;
    stored_count BIGINT;
    exclude_schemas TEXT[] := ARRAY[
        'information_schema', 'pg_catalog', 'pg_toast',
        'tiger', 'tiger_data', 'topology', 'ogr_system_tables',
        'prueba', 'public', 'raster'
    ];
BEGIN
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
                'SELECT COUNT(*) FROM (
                    SELECT DISTINCT
                        EXTRACT(YEAR FROM %s)::int,
                        EXTRACT(MONTH FROM %s)::int,
                        EXTRACT(DAY FROM %s)::int
                    FROM %I.%I
                    WHERE fecha IS NOT NULL
                ) sub',
                fecha_expr, fecha_expr, fecha_expr,
                rec.schema_name, rec.table_name
            );
            EXECUTE dyn_sql INTO src_count;

            layer_key := rec.schema_name || ':' || rec.table_name;

            SELECT lp.periodicity INTO stored
            FROM public.layer_periodicity lp
            WHERE lp.layer_key = check_layer_periodicity.layer_key;

            IF stored IS NULL THEN
                stored_dates := 0;
            ELSE
                SELECT COALESCE(SUM(jsonb_array_length(days)), 0) INTO stored_count
                FROM jsonb_each(stored) AS years(y, months),
                     jsonb_each(months) AS m(month_key, days);
                stored_dates := stored_count;
            END IF;

            source_dates := src_count;

            IF stored IS NULL AND src_count > 0 THEN
                status := 'MISSING';
            ELSIF src_count != stored_dates THEN
                status := 'STALE';
            ELSE
                status := 'OK';
            END IF;

            RETURN NEXT;

        EXCEPTION WHEN OTHERS THEN
            layer_key := rec.schema_name || ':' || rec.table_name;
            status := 'ERROR';
            source_dates := -1;
            stored_dates := -1;
            RETURN NEXT;
        END;
    END LOOP;
END;
$$;

SELECT layer_key, status, source_dates, stored_dates
FROM public.check_layer_periodicity()
ORDER BY
    CASE status WHEN 'MISSING' THEN 0 WHEN 'STALE' THEN 1 WHEN 'ERROR' THEN 2 ELSE 3 END,
    layer_key;
