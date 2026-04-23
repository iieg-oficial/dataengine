-- Validacion previa al DROP de public.mapalab_card
--
-- La tabla public.mapalab_card es el ETL legacy del Google Sheet. Su contenido
-- debe haber sido migrado a mapalab.layer_metadata + mapalab.layer_stats via
-- jobs/bootstrap/run_migrate_mapalab_card.py. Antes de ejecutar el DROP, correr
-- este archivo y verificar que TODAS las filas de mapalab_card estan cubiertas
-- por layer_metadata.
--
-- Uso:
--   psql -h <host> -U <user> -d <db> -f scripts/drop_mapalab_card_validation.sql
--
-- Si cualquier seccion devuelve filas que indican faltantes, NO ejecutar el DROP.
-- El drop real esta al final, comentado. Descomentar solo despues de validar.

\echo '======================================================================'
\echo '1. Conteo comparativo'
\echo '======================================================================'

SELECT
    (SELECT COUNT(*) FROM public.mapalab_card WHERE nombre_capa_geoserver IS NOT NULL
       AND COALESCE(NULLIF(trim(nombre_capa_geoserver), ''), NULL) IS NOT NULL) AS mapalab_card_rows_con_nombre,
    (SELECT COUNT(*) FROM mapalab.layer_metadata) AS layer_metadata_rows;

\echo '======================================================================'
\echo '2. layer_keys en mapalab_card que NO estan en layer_metadata'
\echo '   (deberia ser 0 filas)'
\echo '======================================================================'

SELECT DISTINCT
    CASE
        WHEN trim(workspace) = '' OR workspace IS NULL
            THEN trim(nombre_capa_geoserver)
        ELSE trim(workspace) || ':' || trim(nombre_capa_geoserver)
    END AS expected_layer_key
FROM public.mapalab_card mc
WHERE nombre_capa_geoserver IS NOT NULL
  AND trim(nombre_capa_geoserver) <> ''
  AND NOT EXISTS (
      SELECT 1 FROM mapalab.layer_metadata lm
      WHERE lm.layer_key = CASE
          WHEN trim(mc.workspace) = '' OR mc.workspace IS NULL
              THEN trim(mc.nombre_capa_geoserver)
          ELSE trim(mc.workspace) || ':' || trim(mc.nombre_capa_geoserver)
      END
  )
LIMIT 50;

\echo '======================================================================'
\echo '3. Sample de 3 layer_keys con descripcion populada en ambos lados'
\echo '   (deben coincidir o estar intencionalmente editadas via mariachi)'
\echo '======================================================================'

WITH paired AS (
    SELECT
        lm.layer_key,
        lm.descripcion AS lm_desc,
        mc.descripcion AS mc_desc
    FROM mapalab.layer_metadata lm
    JOIN public.mapalab_card mc
      ON CASE
          WHEN trim(mc.workspace) = '' OR mc.workspace IS NULL
              THEN trim(mc.nombre_capa_geoserver)
          ELSE trim(mc.workspace) || ':' || trim(mc.nombre_capa_geoserver)
      END = lm.layer_key
    WHERE lm.descripcion IS NOT NULL AND mc.descripcion IS NOT NULL
    LIMIT 3
)
SELECT * FROM paired;

\echo '======================================================================'
\echo '4. ¿Alguien lee mapalab_card desde el app layer?'
\echo '   Revisar grepping en ambos backends antes de drop:'
\echo '     grep -rn mapalab_card /home/egar/IIEG/mapalab/backend /home/egar/IIEG/mariachi/api'
\echo '   Deberia aparecer solo en run_migrate_mapalab_card.py (idempotente).'
\echo '======================================================================'

\echo '======================================================================'
\echo 'DROP (descomenta cuando validaciones 1-4 pasen)'
\echo '======================================================================'

-- BEGIN;
-- REVOKE ALL ON public.mapalab_card FROM mariachi_layers;
-- DROP TABLE public.mapalab_card;
-- COMMIT;

-- Tras el drop, considerar borrar tambien:
--   jobs/bootstrap/run_migrate_mapalab_card.py
--   referencias a public.mapalab_card en scripts/bootstrap-v14.sh
