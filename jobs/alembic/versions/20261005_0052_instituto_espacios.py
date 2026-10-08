"""espacios del instituto georreferenciados, con historial

Schema `instituto`: los pisos y los espacios del edificio del IIEG como poligonos en 6368, para
que la intranet marque donde se tomo una foto y para publicarlos como capa. mariachi edita
nombre, tipo, piso, orden e inclusion; el poligono se corrige en QGIS.

`espacios_historial` lo llena un trigger `SECURITY DEFINER`, no la aplicacion: queda igual un cambio hecho desde
mariachi que uno hecho en QGIS o a mano. Quien y desde donde salen de `instituto.actor` e
`instituto.origen` (mariachi los fija con `SET LOCAL`); sin ellos, el usuario de la sesion y
`qgis` si `application_name` lo dice, si no `sql`. `antes` y `despues` son la fila completa en
jsonb, geometria incluida, para poder volver a una version. mariachi_layers solo lo lee.

`pisos.giro_grados` y su centro giran el plano para dibujarlo horizontal (el eje largo del
edificio va a 63.33 grados de azimut).

La geometria no viene en la migracion: es el plano de un edificio de gobierno y no se versiona.
Se carga aparte en cada entorno.

Revision ID: 0052_instituto_espacios
Revises: 0051_drop_mapalab_card
Create Date: 2026-10-05
"""
from alembic import op


revision = "0052_instituto_espacios"
down_revision = "0051_drop_mapalab_card"
branch_labels = None
depends_on = None


_UPGRADE = """
CREATE SCHEMA IF NOT EXISTS instituto;

CREATE TABLE instituto.pisos (
    id serial PRIMARY KEY,
    nombre varchar(60) NOT NULL UNIQUE,
    orden integer NOT NULL DEFAULT 0,
    giro_grados double precision NOT NULL DEFAULT 0,
    centro_x double precision NOT NULL DEFAULT 0,
    centro_y double precision NOT NULL DEFAULT 0
);

CREATE TABLE instituto.espacios (
    fid serial PRIMARY KEY,
    nombre varchar(150) NOT NULL,
    tipo varchar(20) NOT NULL CHECK (tipo IN (
        'oficina', 'trabajo', 'sala', 'recepcion', 'comedor', 'circulacion', 'exterior', 'servicio'
    )),
    piso_id integer NOT NULL REFERENCES instituto.pisos (id),
    incluir boolean NOT NULL DEFAULT true,
    aproximado boolean NOT NULL DEFAULT false,
    orden integer NOT NULL DEFAULT 0,
    geom geometry(MultiPolygon, 6368) NOT NULL,
    actualizado_en timestamptz NOT NULL DEFAULT now(),
    actualizado_por varchar(150),
    UNIQUE (piso_id, nombre)
);
CREATE INDEX ix_espacios_geom ON instituto.espacios USING gist (geom);

CREATE TABLE instituto.espacios_historial (
    id bigserial PRIMARY KEY,
    espacio_fid integer NOT NULL,
    accion varchar(10) NOT NULL,
    antes jsonb,
    despues jsonb,
    quien varchar(150) NOT NULL,
    origen varchar(20) NOT NULL,
    cuando timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_espacios_historial_fid ON instituto.espacios_historial (espacio_fid, cuando DESC);

CREATE FUNCTION instituto.quien() RETURNS text LANGUAGE sql STABLE AS $$
    SELECT COALESCE(NULLIF(current_setting('instituto.actor', true), ''), session_user::text)
$$;

CREATE FUNCTION instituto.origen() RETURNS text LANGUAGE sql STABLE AS $$
    SELECT COALESCE(
        NULLIF(current_setting('instituto.origen', true), ''),
        CASE WHEN current_setting('application_name') ILIKE '%qgis%' THEN 'qgis' ELSE 'sql' END
    )
$$;

CREATE FUNCTION instituto.sellar_espacio() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    NEW.actualizado_en := now();
    NEW.actualizado_por := instituto.quien();
    RETURN NEW;
END $$;

CREATE FUNCTION instituto.historiar_espacio() RETURNS trigger LANGUAGE plpgsql
    SECURITY DEFINER SET search_path = instituto, pg_temp AS $$
BEGIN
    IF TG_OP = 'UPDATE' AND (to_jsonb(OLD) - 'actualizado_en' - 'actualizado_por')
        = (to_jsonb(NEW) - 'actualizado_en' - 'actualizado_por') THEN
        RETURN NEW;
    END IF;
    INSERT INTO instituto.espacios_historial (espacio_fid, accion, antes, despues, quien, origen)
    VALUES (
        COALESCE(NEW.fid, OLD.fid),
        lower(TG_OP),
        CASE WHEN TG_OP = 'INSERT' THEN NULL ELSE to_jsonb(OLD) END,
        CASE WHEN TG_OP = 'DELETE' THEN NULL ELSE to_jsonb(NEW) END,
        instituto.quien(),
        instituto.origen()
    );
    RETURN COALESCE(NEW, OLD);
END $$;

CREATE TRIGGER espacios_sellar BEFORE INSERT OR UPDATE ON instituto.espacios
    FOR EACH ROW EXECUTE FUNCTION instituto.sellar_espacio();
CREATE TRIGGER espacios_historial AFTER INSERT OR UPDATE OR DELETE ON instituto.espacios
    FOR EACH ROW EXECUTE FUNCTION instituto.historiar_espacio();

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mariachi_layers') THEN
        GRANT USAGE ON SCHEMA instituto TO mariachi_layers;
        GRANT SELECT, INSERT, UPDATE, DELETE ON instituto.pisos, instituto.espacios TO mariachi_layers;
        GRANT SELECT ON instituto.espacios_historial TO mariachi_layers;
        GRANT USAGE, SELECT ON instituto.pisos_id_seq, instituto.espacios_fid_seq TO mariachi_layers;
        GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA instituto TO mariachi_layers;
    END IF;
END $$;
"""

_DOWNGRADE = "DROP SCHEMA IF EXISTS instituto CASCADE;"


def upgrade() -> None:
    op.execute(_UPGRADE)


def downgrade() -> None:
    op.execute(_DOWNGRADE)
