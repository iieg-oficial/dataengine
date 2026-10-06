"""volumen del edificio del instituto: alturas por piso y elementos constructivos

Lo que hace falta para levantar el plano en 3D y caminarlo. Cada piso guarda a que nivel esta su
suelo y cuanto mide de alto (3 m mientras no haya dato medido; se cambia desde mariachi), si se
puede pisar y si hay plano de el. Una planta sin plano no se inventa: es un `volumen` sin
divisiones sobre su huella. La azotea es un piso mas, de altura cero.

`instituto.elementos` guarda muros, escaleras y volumenes. `altura` nula toma la del piso; `base` es
el desplazamiento sobre el suelo del piso. Los muros salen del CAD de SIOP y se corrigen en QGIS, igual
que los espacios. Una escalera sube de su piso al siguiente a lo largo de su lado mas largo.

Como en la 0052, la geometria no viene en la migracion: se carga aparte en cada entorno.

Revision ID: 0055_instituto_elementos
Revises: 0054_legend_version
Create Date: 2026-10-05
"""
from alembic import op


revision = "0055_instituto_elementos"
down_revision = "0054_legend_version"
branch_labels = None
depends_on = None


_UPGRADE = """
ALTER TABLE instituto.pisos
    ADD COLUMN IF NOT EXISTS nivel double precision NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS altura double precision NOT NULL DEFAULT 3 CHECK (altura >= 0),
    ADD COLUMN IF NOT EXISTS transitable boolean NOT NULL DEFAULT true,
    ADD COLUMN IF NOT EXISTS con_plano boolean NOT NULL DEFAULT true;

CREATE TABLE IF NOT EXISTS instituto.elementos (
    fid serial PRIMARY KEY,
    tipo varchar(20) NOT NULL CHECK (tipo IN ('muro', 'escalera', 'volumen')),
    piso_id integer NOT NULL REFERENCES instituto.pisos (id),
    base double precision NOT NULL DEFAULT 0,
    altura double precision CHECK (altura IS NULL OR altura >= 0),
    aproximado boolean NOT NULL DEFAULT false,
    geom geometry(MultiPolygon, 6368) NOT NULL,
    actualizado_en timestamptz NOT NULL DEFAULT now(),
    actualizado_por varchar(150)
);
CREATE INDEX IF NOT EXISTS ix_elementos_geom ON instituto.elementos USING gist (geom);
CREATE INDEX IF NOT EXISTS ix_elementos_piso ON instituto.elementos (piso_id, tipo);

DROP TRIGGER IF EXISTS elementos_sellar ON instituto.elementos;
CREATE TRIGGER elementos_sellar BEFORE INSERT OR UPDATE ON instituto.elementos
    FOR EACH ROW EXECUTE FUNCTION instituto.sellar_espacio();

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mariachi_layers') THEN
        GRANT SELECT ON instituto.elementos TO mariachi_layers;
    END IF;
END $$;
"""

_DOWNGRADE = """
DROP TABLE IF EXISTS instituto.elementos;
ALTER TABLE instituto.pisos
    DROP COLUMN IF EXISTS nivel,
    DROP COLUMN IF EXISTS altura,
    DROP COLUMN IF EXISTS transitable,
    DROP COLUMN IF EXISTS con_plano;
"""


def upgrade() -> None:
    op.execute(_UPGRADE)


def downgrade() -> None:
    op.execute(_DOWNGRADE)
