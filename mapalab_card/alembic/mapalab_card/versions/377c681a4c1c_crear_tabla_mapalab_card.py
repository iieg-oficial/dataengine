"""Crear tabla mapalab_card

Revision ID: 377c681a4c1c
Revises: 
Create Date: 2025-11-11 12:43:27.121444

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '377c681a4c1c'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('mapalab_card',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tema', sa.String(length=1000), nullable=True),
        sa.Column('subtema', sa.String(length=1000), nullable=True),
        sa.Column('link_final_capa', sa.String(length=1000), nullable=True),
        sa.Column('capa_descargable', sa.String(length=1000), nullable=True),
        sa.Column('capa_finalizada_geoserver', sa.String(length=1000), nullable=True),
        sa.Column('nombre_capa_db', sa.String(length=1000), nullable=True),
        sa.Column('nombre_capa_usuario', sa.String(length=1000), nullable=True),
        sa.Column('nombre_capa_geoserver', sa.String(length=1000), nullable=True),
        sa.Column('descripcion', sa.String(length=1000), nullable=True),
        sa.Column('frecuencia_actualizacion', sa.String(length=1000), nullable=True),
        sa.Column('fecha_ultima_actualizacion', sa.Date(), nullable=True),
        sa.Column('numeralia_01_valor', sa.String(length=1000), nullable=True),
        sa.Column('numeralia_01_nombre', sa.String(length=1000), nullable=True),
        sa.Column('numeralia_01_simbolo', sa.String(length=1000), nullable=True),
        sa.Column('numeralia_02_valor', sa.String(length=1000), nullable=True),
        sa.Column('numeralia_02_nombre', sa.String(length=1000), nullable=True),
        sa.Column('numeralia_02_simbolo', sa.String(length=1000), nullable=True),
        sa.Column('numeralia_03_valor', sa.String(length=1000), nullable=True),
        sa.Column('numeralia_03_nombre', sa.String(length=1000), nullable=True),
        sa.Column('numeralia_03_simbolo', sa.String(length=1000), nullable=True),
        sa.Column('numeralia_04_valor', sa.String(length=1000), nullable=True),
        sa.Column('numeralia_04_nombre', sa.String(length=1000), nullable=True),
        sa.Column('numeralia_04_simbolo', sa.String(length=1000), nullable=True),
        sa.Column('numeralia_05_valor', sa.String(length=1000), nullable=True),
        sa.Column('numeralia_05_nombre', sa.String(length=1000), nullable=True),
        sa.Column('numeralia_05_simbolo', sa.String(length=1000), nullable=True),
        sa.Column('numeralia_06_valor', sa.String(length=1000), nullable=True),
        sa.Column('numeralia_06_nombre', sa.String(length=1000), nullable=True),
        sa.Column('numeralia_06_simbolo', sa.String(length=1000), nullable=True),
        sa.Column('numeralia_07_valor', sa.String(length=1000), nullable=True),
        sa.Column('numeralia_07_nombre', sa.String(length=1000), nullable=True),
        sa.Column('numeralia_07_simbolo', sa.String(length=1000), nullable=True),
        sa.Column('numeralia_08_valor', sa.String(length=1000), nullable=True),
        sa.Column('numeralia_08_nombre', sa.String(length=1000), nullable=True),
        sa.Column('numeralia_08_simbolo', sa.String(length=1000), nullable=True),
        sa.Column('nombre_pie_numeralia', sa.String(length=1000), nullable=True),
        sa.Column('metodologia_texto', sa.String(length=1000), nullable=True),
        sa.Column('metodologia_archivo_enlace', sa.String(length=1000), nullable=True),
        sa.Column('fuentes_texto_largo', sa.String(length=1000), nullable=True),
        sa.Column('fuentes_texto_corto', sa.String(length=1000), nullable=True),
        sa.Column('fuentes_enlace', sa.String(length=1000), nullable=True),
        sa.Column('tipo_mapa', sa.String(length=1000), nullable=True),
        sa.Column('texto_leyenda_juridico', sa.String(length=2000), nullable=True),
        sa.Column('tipo_mapa_enlace', sa.String(length=1000), nullable=True),
        sa.Column('metadato_txt', sa.String(length=1000), nullable=True),
        sa.Column('metadato_xlsx', sa.String(length=1000), nullable=True),
        sa.Column('tarjeta_punto_poligono', sa.String(length=1000), nullable=True),
        sa.Column('created_at', sa.Date(), server_default=sa.func.current_date(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('mapalab_card')
