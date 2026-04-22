"""fecha_ultima_actualizacion de Date a String

Revision ID: a1b2c3d4e5f6
Revises: 377c681a4c1c
Create Date: 2026-03-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '377c681a4c1c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'mapalab_card',
        'fecha_ultima_actualizacion',
        existing_type=sa.Date(),
        type_=sa.String(length=1000),
        existing_nullable=True,
        postgresql_using='fecha_ultima_actualizacion::text'
    )


def downgrade() -> None:
    op.alter_column(
        'mapalab_card',
        'fecha_ultima_actualizacion',
        existing_type=sa.String(length=1000),
        type_=sa.Date(),
        existing_nullable=True,
        postgresql_using='fecha_ultima_actualizacion::date'
    )
