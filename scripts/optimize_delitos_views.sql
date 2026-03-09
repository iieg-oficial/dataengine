BEGIN;

-- =====================================================
-- TIPO "ARMA" (feminicidio, homicidio_doloso, lesiones_dolosas)
-- =====================================================

CREATE OR REPLACE VIEW seguridad_y_proteccion_ciudadana.datos_delitos_feminicidio_secretariado AS
SELECT row_number() OVER () AS fid,
    b.geom AS geom_iieg,
    c.geom AS geom_inegi,
    b.clave_geo,
    b.nombre,
    agg.fecha,
    agg.clave_entidad,
    agg.clave_municipio,
    agg.bien_juridico,
    agg.delito,
    agg.con_arma_de_fuego,
    agg.con_arma_blanca,
    agg.con_otro_elemento,
    agg.no_especificado,
    agg.carpetas_investigacion,
    agg.tasa_carpetas_investigacion
FROM (
    SELECT
        a.fecha,
        a.clave_entidad,
        a.clave_municipio,
        a.bien_juridico,
        a.delito,
        sum(CASE WHEN a.modalidad = 'Con arma de fuego' THEN a.carpetas_investigacion ELSE 0 END) AS con_arma_de_fuego,
        sum(CASE WHEN a.modalidad = 'Con arma blanca' THEN a.carpetas_investigacion ELSE 0 END) AS con_arma_blanca,
        sum(CASE WHEN a.modalidad = 'Con otro elemento' THEN a.carpetas_investigacion ELSE 0 END) AS con_otro_elemento,
        sum(CASE WHEN a.modalidad = 'No especificado' OR a.modalidad IS NULL THEN a.carpetas_investigacion ELSE 0 END) AS no_especificado,
        max(CASE WHEN a.nivel_jerarquico = 'delito' THEN a.carpetas_investigacion ELSE NULL END) AS carpetas_investigacion,
        max(CASE WHEN a.nivel_jerarquico = 'delito' THEN a.tasa_carpetas_investigacion ELSE NULL END) AS tasa_carpetas_investigacion
    FROM seguridad_y_proteccion_ciudadana.delitos_secretariado a
    WHERE a.delito = 'Feminicidio'
    GROUP BY a.clave_municipio, a.fecha, a.clave_entidad, a.bien_juridico, a.delito
) agg
JOIN mapa_base.limite_municipal b ON b.clave_geo::bpchar = agg.clave_municipio
LEFT JOIN mapa_base.limite_municipal_inegi c ON b.clave_geo = c.clave_geo::text;


CREATE OR REPLACE VIEW seguridad_y_proteccion_ciudadana.datos_delitos_homicidio_doloso_secretariado AS
SELECT row_number() OVER () AS fid,
    b.geom AS geom_iieg,
    c.geom AS geom_inegi,
    b.clave_geo,
    b.nombre,
    agg.fecha,
    agg.clave_entidad,
    agg.clave_municipio,
    agg.bien_juridico,
    agg.delito,
    agg.con_arma_de_fuego,
    agg.con_arma_blanca,
    agg.con_otro_elemento,
    agg.no_especificado,
    agg.carpetas_investigacion,
    agg.tasa_carpetas_investigacion
FROM (
    SELECT
        a.fecha,
        a.clave_entidad,
        a.clave_municipio,
        a.bien_juridico,
        a.delito,
        sum(CASE WHEN a.modalidad = 'Con arma de fuego' THEN a.carpetas_investigacion ELSE 0 END) AS con_arma_de_fuego,
        sum(CASE WHEN a.modalidad = 'Con arma blanca' THEN a.carpetas_investigacion ELSE 0 END) AS con_arma_blanca,
        sum(CASE WHEN a.modalidad = 'Con otro elemento' THEN a.carpetas_investigacion ELSE 0 END) AS con_otro_elemento,
        sum(CASE WHEN a.modalidad = 'No especificado' OR a.modalidad IS NULL THEN a.carpetas_investigacion ELSE 0 END) AS no_especificado,
        max(CASE WHEN a.nivel_jerarquico = 'delito' THEN a.carpetas_investigacion ELSE NULL END) AS carpetas_investigacion,
        max(CASE WHEN a.nivel_jerarquico = 'delito' THEN a.tasa_carpetas_investigacion ELSE NULL END) AS tasa_carpetas_investigacion
    FROM seguridad_y_proteccion_ciudadana.delitos_secretariado a
    WHERE a.delito = 'Homicidio doloso'
    GROUP BY a.clave_municipio, a.fecha, a.clave_entidad, a.bien_juridico, a.delito
) agg
JOIN mapa_base.limite_municipal b ON b.clave_geo::bpchar = agg.clave_municipio
LEFT JOIN mapa_base.limite_municipal_inegi c ON b.clave_geo = c.clave_geo::text;


CREATE OR REPLACE VIEW seguridad_y_proteccion_ciudadana.datos_delitos_lesiones_dolosas_secretariado AS
SELECT row_number() OVER () AS fid,
    b.geom AS geom_iieg,
    c.geom AS geom_inegi,
    b.clave_geo,
    b.nombre,
    agg.fecha,
    agg.clave_entidad,
    agg.clave_municipio,
    agg.bien_juridico,
    agg.delito,
    agg.con_arma_de_fuego,
    agg.con_arma_blanca,
    agg.con_otro_elemento,
    agg.no_especificado,
    agg.carpetas_investigacion,
    agg.tasa_carpetas_investigacion
FROM (
    SELECT
        a.fecha,
        a.clave_entidad,
        a.clave_municipio,
        a.bien_juridico,
        a.delito,
        sum(CASE WHEN a.modalidad = 'Con arma de fuego' THEN a.carpetas_investigacion ELSE 0 END) AS con_arma_de_fuego,
        sum(CASE WHEN a.modalidad = 'Con arma blanca' THEN a.carpetas_investigacion ELSE 0 END) AS con_arma_blanca,
        sum(CASE WHEN a.modalidad = 'Con otro elemento' THEN a.carpetas_investigacion ELSE 0 END) AS con_otro_elemento,
        sum(CASE WHEN a.modalidad = 'No especificado' OR a.modalidad IS NULL THEN a.carpetas_investigacion ELSE 0 END) AS no_especificado,
        max(CASE WHEN a.nivel_jerarquico = 'delito' THEN a.carpetas_investigacion ELSE NULL END) AS carpetas_investigacion,
        max(CASE WHEN a.nivel_jerarquico = 'delito' THEN a.tasa_carpetas_investigacion ELSE NULL END) AS tasa_carpetas_investigacion
    FROM seguridad_y_proteccion_ciudadana.delitos_secretariado a
    WHERE a.delito = 'Lesiones dolosas'
    GROUP BY a.clave_municipio, a.fecha, a.clave_entidad, a.bien_juridico, a.delito
) agg
JOIN mapa_base.limite_municipal b ON b.clave_geo::bpchar = agg.clave_municipio
LEFT JOIN mapa_base.limite_municipal_inegi c ON b.clave_geo = c.clave_geo::text;


-- =====================================================
-- TIPO "VIOLENCIA" (todos los robos)
-- =====================================================

CREATE OR REPLACE VIEW seguridad_y_proteccion_ciudadana.datos_delitos_robo_autopartes_secretariado AS
SELECT row_number() OVER () AS fid,
    b.geom AS geom_iieg,
    c.geom AS geom_inegi,
    b.clave_geo,
    b.nombre,
    agg.fecha,
    agg.clave_entidad,
    agg.clave_municipio,
    agg.bien_juridico,
    agg.delito,
    agg.con_violencia,
    agg.sin_violencia,
    agg.carpetas_investigacion,
    agg.tasa_carpetas_investigacion
FROM (
    SELECT
        a.fecha,
        a.clave_entidad,
        a.clave_municipio,
        a.bien_juridico,
        a.delito,
        sum(CASE WHEN a.modalidad = 'Con violencia' THEN a.carpetas_investigacion ELSE 0 END) AS con_violencia,
        sum(CASE WHEN a.modalidad = 'Sin violencia' THEN a.carpetas_investigacion ELSE 0 END) AS sin_violencia,
        max(CASE WHEN a.nivel_jerarquico = 'delito' THEN a.carpetas_investigacion ELSE NULL END) AS carpetas_investigacion,
        max(CASE WHEN a.nivel_jerarquico = 'delito' THEN a.tasa_carpetas_investigacion ELSE NULL END) AS tasa_carpetas_investigacion
    FROM seguridad_y_proteccion_ciudadana.delitos_secretariado a
    WHERE a.delito = 'Robo de autopartes'
    GROUP BY a.clave_municipio, a.fecha, a.clave_entidad, a.bien_juridico, a.delito
) agg
JOIN mapa_base.limite_municipal b ON b.clave_geo::bpchar = agg.clave_municipio
LEFT JOIN mapa_base.limite_municipal_inegi c ON b.clave_geo = c.clave_geo::text;


CREATE OR REPLACE VIEW seguridad_y_proteccion_ciudadana.datos_delitos_robo_casa_habitacion_secretariado AS
SELECT row_number() OVER () AS fid,
    b.geom AS geom_iieg,
    c.geom AS geom_inegi,
    b.clave_geo,
    b.nombre,
    agg.fecha,
    agg.clave_entidad,
    agg.clave_municipio,
    agg.bien_juridico,
    agg.delito,
    agg.con_violencia,
    agg.sin_violencia,
    agg.carpetas_investigacion,
    agg.tasa_carpetas_investigacion
FROM (
    SELECT
        a.fecha,
        a.clave_entidad,
        a.clave_municipio,
        a.bien_juridico,
        a.delito,
        sum(CASE WHEN a.modalidad = 'Con violencia' THEN a.carpetas_investigacion ELSE 0 END) AS con_violencia,
        sum(CASE WHEN a.modalidad = 'Sin violencia' THEN a.carpetas_investigacion ELSE 0 END) AS sin_violencia,
        max(CASE WHEN a.nivel_jerarquico = 'delito' THEN a.carpetas_investigacion ELSE NULL END) AS carpetas_investigacion,
        max(CASE WHEN a.nivel_jerarquico = 'delito' THEN a.tasa_carpetas_investigacion ELSE NULL END) AS tasa_carpetas_investigacion
    FROM seguridad_y_proteccion_ciudadana.delitos_secretariado a
    WHERE a.delito = 'Robo a casa habitación'
    GROUP BY a.clave_municipio, a.fecha, a.clave_entidad, a.bien_juridico, a.delito
) agg
JOIN mapa_base.limite_municipal b ON b.clave_geo::bpchar = agg.clave_municipio
LEFT JOIN mapa_base.limite_municipal_inegi c ON b.clave_geo = c.clave_geo::text;


CREATE OR REPLACE VIEW seguridad_y_proteccion_ciudadana.datos_delitos_robo_coche_cuatro_ruedas_secretariado AS
SELECT row_number() OVER () AS fid,
    b.geom AS geom_iieg,
    c.geom AS geom_inegi,
    b.clave_geo,
    b.nombre,
    agg.fecha,
    agg.clave_entidad,
    agg.clave_municipio,
    agg.bien_juridico,
    agg.delito,
    agg.con_violencia,
    agg.sin_violencia,
    agg.carpetas_investigacion,
    agg.tasa_carpetas_investigacion
FROM (
    SELECT
        a.fecha,
        a.clave_entidad,
        a.clave_municipio,
        a.bien_juridico,
        a.delito,
        sum(CASE WHEN a.modalidad = 'Con violencia' THEN a.carpetas_investigacion ELSE 0 END) AS con_violencia,
        sum(CASE WHEN a.modalidad = 'Sin violencia' THEN a.carpetas_investigacion ELSE 0 END) AS sin_violencia,
        max(CASE WHEN a.nivel_jerarquico = 'delito' THEN a.carpetas_investigacion ELSE NULL END) AS carpetas_investigacion,
        max(CASE WHEN a.nivel_jerarquico = 'delito' THEN a.tasa_carpetas_investigacion ELSE NULL END) AS tasa_carpetas_investigacion
    FROM seguridad_y_proteccion_ciudadana.delitos_secretariado a
    WHERE a.delito = 'Robo de coche de cuatro ruedas'
    GROUP BY a.clave_municipio, a.fecha, a.clave_entidad, a.bien_juridico, a.delito
) agg
JOIN mapa_base.limite_municipal b ON b.clave_geo::bpchar = agg.clave_municipio
LEFT JOIN mapa_base.limite_municipal_inegi c ON b.clave_geo = c.clave_geo::text;


CREATE OR REPLACE VIEW seguridad_y_proteccion_ciudadana.datos_delitos_robo_institucion_bancaria_secretariado AS
SELECT row_number() OVER () AS fid,
    b.geom AS geom_iieg,
    c.geom AS geom_inegi,
    b.clave_geo,
    b.nombre,
    agg.fecha,
    agg.clave_entidad,
    agg.clave_municipio,
    agg.bien_juridico,
    agg.delito,
    agg.con_violencia,
    agg.sin_violencia,
    agg.carpetas_investigacion,
    agg.tasa_carpetas_investigacion
FROM (
    SELECT
        a.fecha,
        a.clave_entidad,
        a.clave_municipio,
        a.bien_juridico,
        a.delito,
        sum(CASE WHEN a.modalidad = 'Con violencia' THEN a.carpetas_investigacion ELSE 0 END) AS con_violencia,
        sum(CASE WHEN a.modalidad = 'Sin violencia' THEN a.carpetas_investigacion ELSE 0 END) AS sin_violencia,
        max(CASE WHEN a.nivel_jerarquico = 'delito' THEN a.carpetas_investigacion ELSE NULL END) AS carpetas_investigacion,
        max(CASE WHEN a.nivel_jerarquico = 'delito' THEN a.tasa_carpetas_investigacion ELSE NULL END) AS tasa_carpetas_investigacion
    FROM seguridad_y_proteccion_ciudadana.delitos_secretariado a
    WHERE a.delito = 'Robo a institución bancaria'
    GROUP BY a.clave_municipio, a.fecha, a.clave_entidad, a.bien_juridico, a.delito
) agg
JOIN mapa_base.limite_municipal b ON b.clave_geo::bpchar = agg.clave_municipio
LEFT JOIN mapa_base.limite_municipal_inegi c ON b.clave_geo = c.clave_geo::text;


CREATE OR REPLACE VIEW seguridad_y_proteccion_ciudadana.datos_delitos_robo_motocicleta_secretariado AS
SELECT row_number() OVER () AS fid,
    b.geom AS geom_iieg,
    c.geom AS geom_inegi,
    b.clave_geo,
    b.nombre,
    agg.fecha,
    agg.clave_entidad,
    agg.clave_municipio,
    agg.bien_juridico,
    agg.delito,
    agg.con_violencia,
    agg.sin_violencia,
    agg.carpetas_investigacion,
    agg.tasa_carpetas_investigacion
FROM (
    SELECT
        a.fecha,
        a.clave_entidad,
        a.clave_municipio,
        a.bien_juridico,
        a.delito,
        sum(CASE WHEN a.modalidad = 'Con violencia' THEN a.carpetas_investigacion ELSE 0 END) AS con_violencia,
        sum(CASE WHEN a.modalidad = 'Sin violencia' THEN a.carpetas_investigacion ELSE 0 END) AS sin_violencia,
        max(CASE WHEN a.nivel_jerarquico = 'delito' THEN a.carpetas_investigacion ELSE NULL END) AS carpetas_investigacion,
        max(CASE WHEN a.nivel_jerarquico = 'delito' THEN a.tasa_carpetas_investigacion ELSE NULL END) AS tasa_carpetas_investigacion
    FROM seguridad_y_proteccion_ciudadana.delitos_secretariado a
    WHERE a.delito = 'Robo de motocicleta'
    GROUP BY a.clave_municipio, a.fecha, a.clave_entidad, a.bien_juridico, a.delito
) agg
JOIN mapa_base.limite_municipal b ON b.clave_geo::bpchar = agg.clave_municipio
LEFT JOIN mapa_base.limite_municipal_inegi c ON b.clave_geo = c.clave_geo::text;


CREATE OR REPLACE VIEW seguridad_y_proteccion_ciudadana.datos_delitos_robo_negocio_secretariado AS
SELECT row_number() OVER () AS fid,
    b.geom AS geom_iieg,
    c.geom AS geom_inegi,
    b.clave_geo,
    b.nombre,
    agg.fecha,
    agg.clave_entidad,
    agg.clave_municipio,
    agg.bien_juridico,
    agg.delito,
    agg.con_violencia,
    agg.sin_violencia,
    agg.carpetas_investigacion,
    agg.tasa_carpetas_investigacion
FROM (
    SELECT
        a.fecha,
        a.clave_entidad,
        a.clave_municipio,
        a.bien_juridico,
        a.delito,
        sum(CASE WHEN a.modalidad = 'Con violencia' THEN a.carpetas_investigacion ELSE 0 END) AS con_violencia,
        sum(CASE WHEN a.modalidad = 'Sin violencia' THEN a.carpetas_investigacion ELSE 0 END) AS sin_violencia,
        max(CASE WHEN a.nivel_jerarquico = 'delito' THEN a.carpetas_investigacion ELSE NULL END) AS carpetas_investigacion,
        max(CASE WHEN a.nivel_jerarquico = 'delito' THEN a.tasa_carpetas_investigacion ELSE NULL END) AS tasa_carpetas_investigacion
    FROM seguridad_y_proteccion_ciudadana.delitos_secretariado a
    WHERE a.delito = 'Robo a negocio'
    GROUP BY a.clave_municipio, a.fecha, a.clave_entidad, a.bien_juridico, a.delito
) agg
JOIN mapa_base.limite_municipal b ON b.clave_geo::bpchar = agg.clave_municipio
LEFT JOIN mapa_base.limite_municipal_inegi c ON b.clave_geo = c.clave_geo::text;


CREATE OR REPLACE VIEW seguridad_y_proteccion_ciudadana.datos_delitos_robo_transeunte_via_publica_secretariado AS
SELECT row_number() OVER () AS fid,
    b.geom AS geom_iieg,
    c.geom AS geom_inegi,
    b.clave_geo,
    b.nombre,
    agg.fecha,
    agg.clave_entidad,
    agg.clave_municipio,
    agg.bien_juridico,
    agg.delito,
    agg.con_violencia,
    agg.sin_violencia,
    agg.carpetas_investigacion,
    agg.tasa_carpetas_investigacion
FROM (
    SELECT
        a.fecha,
        a.clave_entidad,
        a.clave_municipio,
        a.bien_juridico,
        a.delito,
        sum(CASE WHEN a.modalidad = 'Con violencia' THEN a.carpetas_investigacion ELSE 0 END) AS con_violencia,
        sum(CASE WHEN a.modalidad = 'Sin violencia' THEN a.carpetas_investigacion ELSE 0 END) AS sin_violencia,
        max(CASE WHEN a.nivel_jerarquico = 'delito' THEN a.carpetas_investigacion ELSE NULL END) AS carpetas_investigacion,
        max(CASE WHEN a.nivel_jerarquico = 'delito' THEN a.tasa_carpetas_investigacion ELSE NULL END) AS tasa_carpetas_investigacion
    FROM seguridad_y_proteccion_ciudadana.delitos_secretariado a
    WHERE a.delito = 'Robo a transeúnte en vía pública'
    GROUP BY a.clave_municipio, a.fecha, a.clave_entidad, a.bien_juridico, a.delito
) agg
JOIN mapa_base.limite_municipal b ON b.clave_geo::bpchar = agg.clave_municipio
LEFT JOIN mapa_base.limite_municipal_inegi c ON b.clave_geo = c.clave_geo::text;


CREATE OR REPLACE VIEW seguridad_y_proteccion_ciudadana.datos_delitos_robo_transportista_secretariado AS
SELECT row_number() OVER () AS fid,
    b.geom AS geom_iieg,
    c.geom AS geom_inegi,
    b.clave_geo,
    b.nombre,
    agg.fecha,
    agg.clave_entidad,
    agg.clave_municipio,
    agg.bien_juridico,
    agg.delito,
    agg.con_violencia,
    agg.sin_violencia,
    agg.carpetas_investigacion,
    agg.tasa_carpetas_investigacion
FROM (
    SELECT
        a.fecha,
        a.clave_entidad,
        a.clave_municipio,
        a.bien_juridico,
        a.delito,
        sum(CASE WHEN a.modalidad = 'Con violencia' THEN a.carpetas_investigacion ELSE 0 END) AS con_violencia,
        sum(CASE WHEN a.modalidad = 'Sin violencia' THEN a.carpetas_investigacion ELSE 0 END) AS sin_violencia,
        max(CASE WHEN a.nivel_jerarquico = 'delito' THEN a.carpetas_investigacion ELSE NULL END) AS carpetas_investigacion,
        max(CASE WHEN a.nivel_jerarquico = 'delito' THEN a.tasa_carpetas_investigacion ELSE NULL END) AS tasa_carpetas_investigacion
    FROM seguridad_y_proteccion_ciudadana.delitos_secretariado a
    WHERE a.delito = 'Robo a transportista'
    GROUP BY a.clave_municipio, a.fecha, a.clave_entidad, a.bien_juridico, a.delito
) agg
JOIN mapa_base.limite_municipal b ON b.clave_geo::bpchar = agg.clave_municipio
LEFT JOIN mapa_base.limite_municipal_inegi c ON b.clave_geo = c.clave_geo::text;

COMMIT;
