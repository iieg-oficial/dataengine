"""capas privadas de MapaLab y quien puede verlas

`mapalab.layers.privada` saca un nodo (capa o carpeta) del arbol publico. Una carpeta privada
arrastra a sus descendientes. Quien la ve se decide aqui y no en minerva: minerva solo dice quien
puede iniciar sesion en el visor (app `mapalab`), y sus grupos no se exponen a los consumidores.

- `usuarios`: se crea al primer login con el `sub` de minerva; tambien se puede dar de alta por
  correo antes, y el `sub` se completa cuando entra.
- `grupos` y `grupo_miembros`: grupos de trabajo del visor, administrados desde mariachi.
- `capa_acceso`: por capa privada, una persona o un grupo, nunca los dos en la misma fila.

mariachi_layers edita todo (mariachi administra y mapalab registra el login).

Revision ID: 0053_capas_privadas
Revises: 0052_instituto_espacios
Create Date: 2026-10-05
"""
from alembic import op


revision = "0053_capas_privadas"
down_revision = "0052_instituto_espacios"
branch_labels = None
depends_on = None


_UPGRADE = """
ALTER TABLE mapalab.layers ADD COLUMN privada boolean NOT NULL DEFAULT false;

CREATE TABLE mapalab.usuarios (
    id serial PRIMARY KEY,
    sub varchar(100) UNIQUE,
    correo varchar(254) NOT NULL,
    nombre varchar(200),
    activo boolean NOT NULL DEFAULT true,
    ultimo_acceso timestamptz,
    creado_en timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX ux_usuarios_correo ON mapalab.usuarios (lower(correo));

CREATE TABLE mapalab.grupos (
    id serial PRIMARY KEY,
    nombre varchar(120) NOT NULL,
    descripcion varchar(300),
    creado_en timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX ux_grupos_nombre ON mapalab.grupos (lower(nombre));

CREATE TABLE mapalab.grupo_miembros (
    grupo_id integer NOT NULL REFERENCES mapalab.grupos (id) ON DELETE CASCADE,
    usuario_id integer NOT NULL REFERENCES mapalab.usuarios (id) ON DELETE CASCADE,
    PRIMARY KEY (grupo_id, usuario_id)
);
CREATE INDEX ix_grupo_miembros_usuario ON mapalab.grupo_miembros (usuario_id);

CREATE TABLE mapalab.capa_acceso (
    id serial PRIMARY KEY,
    layer_id varchar(100) NOT NULL REFERENCES mapalab.layers (id) ON DELETE CASCADE ON UPDATE CASCADE,
    usuario_id integer REFERENCES mapalab.usuarios (id) ON DELETE CASCADE,
    grupo_id integer REFERENCES mapalab.grupos (id) ON DELETE CASCADE,
    CHECK ((usuario_id IS NULL) <> (grupo_id IS NULL))
);
CREATE UNIQUE INDEX ux_capa_acceso_usuario ON mapalab.capa_acceso (layer_id, usuario_id) WHERE usuario_id IS NOT NULL;
CREATE UNIQUE INDEX ux_capa_acceso_grupo ON mapalab.capa_acceso (layer_id, grupo_id) WHERE grupo_id IS NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mariachi_layers') THEN
        RAISE NOTICE 'rol mariachi_layers no existe, se omiten los grants';
        RETURN;
    END IF;
    GRANT SELECT, INSERT, UPDATE, DELETE
        ON mapalab.usuarios, mapalab.grupos, mapalab.grupo_miembros, mapalab.capa_acceso
        TO mariachi_layers;
    GRANT USAGE, SELECT
        ON mapalab.usuarios_id_seq, mapalab.grupos_id_seq, mapalab.capa_acceso_id_seq
        TO mariachi_layers;
END
$$;
"""

_DOWNGRADE = """
DROP TABLE IF EXISTS mapalab.capa_acceso;
DROP TABLE IF EXISTS mapalab.grupo_miembros;
DROP TABLE IF EXISTS mapalab.grupos;
DROP TABLE IF EXISTS mapalab.usuarios;
ALTER TABLE mapalab.layers DROP COLUMN IF EXISTS privada;
"""


def upgrade() -> None:
    op.execute(_UPGRADE)


def downgrade() -> None:
    op.execute(_DOWNGRADE)
