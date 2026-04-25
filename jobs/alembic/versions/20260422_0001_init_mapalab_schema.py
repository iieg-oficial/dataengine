"""init mapalab schema (workspaces, layers, initial_layer_order)

Revision ID: 0001_mapalab_init
Revises:
Create Date: 2026-04-22

Schema 'mapalab' + 3 tablas + seed de workspaces.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0001_mapalab_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Nota: el schema 'mapalab' debe existir previo a esta migracion.
    # bootstrap-v14.sh lo crea con:
    #   CREATE SCHEMA IF NOT EXISTS mapalab AUTHORIZATION mariachi_layers;

    op.create_table(
        "workspaces",
        sa.Column("alias", sa.String(50), primary_key=True),
        sa.Column("geoserver_workspace", sa.String(200), nullable=False),
        sa.Column("db_schema", sa.String(200), nullable=False),
        sa.Column("label", sa.String(200)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        schema="mapalab",
    )

    op.create_table(
        "layers",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column(
            "parent_id",
            sa.String(100),
            sa.ForeignKey("mapalab.layers.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("sort_order", sa.Integer, server_default="0", nullable=False),
        sa.Column(
            "node_type",
            sa.String(20),
            sa.CheckConstraint(
                "node_type IN ('tema','category','label','group','leaf')",
                name="ck_layers_node_type",
            ),
            nullable=False,
        ),
        sa.Column("hidden_in_menu", sa.Boolean, server_default=sa.text("FALSE"), nullable=False),
        sa.Column("disabled", sa.Boolean, server_default=sa.text("FALSE"), nullable=False),
        sa.Column(
            "workspace_alias",
            sa.String(50),
            sa.ForeignKey("mapalab.workspaces.alias", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("geoserver_layer", sa.String(200), nullable=True),
        sa.Column("styles", sa.String(200), server_default="", nullable=False),
        sa.Column("cql_filter", sa.Text, server_default="", nullable=False),
        sa.Column("wms_group", sa.String(100), nullable=True),
        sa.Column("wfs_available", sa.Boolean, server_default=sa.text("TRUE"), nullable=False),
        sa.Column("wfs_layer_name", sa.String(200), nullable=True),
        sa.Column("downloadable", sa.Boolean, server_default=sa.text("TRUE"), nullable=False),
        sa.Column("metadata_layer", sa.String(200), nullable=True),
        sa.Column("default_date", postgresql.JSONB, nullable=True),
        sa.Column("time_enabled", sa.Boolean, server_default=sa.text("FALSE"), nullable=False),
        sa.Column("time_style_pattern", sa.String(200), nullable=True),
        sa.Column("raster_periodicity", postgresql.JSONB, nullable=True),
        sa.Column("hide_periodicity", sa.Boolean, server_default=sa.text("FALSE"), nullable=False),
        sa.Column("default_zoom", postgresql.JSONB, nullable=True),
        sa.Column("zoom_range", postgresql.JSONB, nullable=True),
        sa.Column("search_tags", postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column("searchable_fields", postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column("has_municipio", sa.Boolean, server_default=sa.text("FALSE"), nullable=False),
        sa.Column("has_direccion", sa.Boolean, server_default=sa.text("FALSE"), nullable=False),
        sa.Column("municipio_field", sa.String(100), nullable=True),
        sa.Column("direccion_field", sa.String(100), nullable=True),
        sa.Column("infobox_template", sa.String(50), nullable=True),
        sa.Column("infobox_params", postgresql.JSONB, nullable=True),
        sa.Column("infobox_config", postgresql.JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("updated_by", sa.String(100), nullable=True),
        schema="mapalab",
    )
    op.create_index("idx_layers_parent", "layers", ["parent_id"], schema="mapalab")
    op.create_index("idx_layers_node_type", "layers", ["node_type"], schema="mapalab")
    op.create_index(
        "idx_layers_search",
        "layers",
        ["search_tags"],
        schema="mapalab",
        postgresql_using="gin",
    )
    op.create_index(
        "idx_layers_workspace",
        "layers",
        ["workspace_alias"],
        schema="mapalab",
        postgresql_where=sa.text("workspace_alias IS NOT NULL"),
    )

    op.create_table(
        "initial_layer_order",
        sa.Column(
            "layer_id",
            sa.String(100),
            sa.ForeignKey("mapalab.layers.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("sort_order", sa.Integer, nullable=False),
        schema="mapalab",
    )

    op.execute("""
        INSERT INTO mapalab.workspaces (alias, geoserver_workspace, db_schema, label) VALUES
            ('general',    'general',                          'mapa_base',                         'General'),
            ('economia',   'economia',                         'economia',                          'Economía'),
            ('salud',      'salud',                            'salud',                             'Salud'),
            ('educacion',  'educacion',                        'educacion',                         'Educación'),
            ('seguridad',  'seguridad_y_proteccion_ciudadana', 'seguridad_y_proteccion_ciudadana',  'Seguridad y Protección Ciudadana'),
            ('recursos',   'recursos_y_calidad_de_vida',       'recursos_y_calidad_de_vida',        'Recursos y Calidad de Vida'),
            ('demografia', 'demografia',                       'demografia',                        'Demografía'),
            ('desarrollo', 'desarrollo_social',                'desarrollo_social',                 'Desarrollo Social'),
            ('gobierno',   'gobierno_y_ciudadania',            'gobierno_y_ciudadania',             'Gobierno y Ciudadanía'),
            ('raster',     'raster',                           'raster',                            'Raster (Clima)'),
            ('mundial',    'mundial',                          'mundial',                           'Mundial')
    """)


def downgrade() -> None:
    op.drop_table("initial_layer_order", schema="mapalab")
    op.drop_index("idx_layers_workspace", table_name="layers", schema="mapalab")
    op.drop_index("idx_layers_search", table_name="layers", schema="mapalab")
    op.drop_index("idx_layers_node_type", table_name="layers", schema="mapalab")
    op.drop_index("idx_layers_parent", table_name="layers", schema="mapalab")
    op.drop_table("layers", schema="mapalab")
    op.drop_table("workspaces", schema="mapalab")
