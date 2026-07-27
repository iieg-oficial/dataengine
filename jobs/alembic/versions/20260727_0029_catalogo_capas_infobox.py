"""infobox propia de las capas del catalogo (override del arbol)

`mapalab.catalogo_capas` no tenia configuracion de tarjeta: la heredaba de
`mapalab.layers` con un LEFT JOIN LATERAL por (workspace_alias, geoserver_layer).
Eso dejaba dos huecos: las capas del catalogo que no existen en el arbol se
quedaban sin tarjeta, y cualquier ajuste hecho desde el catalogo habria tenido
que escribir en `layers`, cambiando tambien lo que ve el visor principal.

Con esta columna el catalogo puede tener su propia configuracion. La lectura
hace COALESCE: si la capa no define la suya, sigue heredando la del arbol, asi
que nada cambia para las capas ya configuradas. La escritura (propuestas
ciudadanas aprobadas desde mariachi) toca unicamente esta columna.

Revision ID: 0029_catalogo_capas_infobox
Revises: 0028_catalogo_instituciones
Create Date: 2026-07-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0029_catalogo_capas_infobox"
down_revision = "0028_catalogo_instituciones"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "catalogo_capas",
        sa.Column("infobox_config", postgresql.JSONB, nullable=True),
        schema="mapalab",
    )


def downgrade() -> None:
    op.drop_column("catalogo_capas", "infobox_config", schema="mapalab")
