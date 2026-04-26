-- FROZEN (2026-04-23): baseline de bootstrap del schema mapalab.* para v1.4.0.
-- NO se modifica. Cambios futuros de schema van como migracion alembic en
-- mapalab-dataengine/jobs/alembic/versions/. Ver
-- gateway-hub/docs/ecosystem.md seccion 7.3 (revisado 2026-04-24) para la
-- politica de ownership. Tras aplicar este SQL, bootstrap-v14.sh corre
-- `alembic upgrade head` en el container `jobs` para aplicar 0004+.

BEGIN;

CREATE TABLE IF NOT EXISTS mapalab.workspaces (
    alias               VARCHAR(50) PRIMARY KEY,
    geoserver_workspace VARCHAR(200) NOT NULL,
    db_schema           VARCHAR(200) NOT NULL,
    label               VARCHAR(200),
    created_at          TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

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
ON CONFLICT (alias) DO NOTHING;

CREATE TABLE IF NOT EXISTS mapalab.layers (
    id                  VARCHAR(100) PRIMARY KEY,
    parent_id           VARCHAR(100),
    label               VARCHAR(255) NOT NULL,
    sort_order          INTEGER DEFAULT 0 NOT NULL,
    node_type           VARCHAR(20) NOT NULL,
    hidden_in_menu      BOOLEAN DEFAULT FALSE NOT NULL,
    disabled            BOOLEAN DEFAULT FALSE NOT NULL,
    workspace_alias     VARCHAR(50),
    geoserver_layer     VARCHAR(200),
    styles              VARCHAR(200) DEFAULT '' NOT NULL,
    cql_filter          TEXT DEFAULT '' NOT NULL,
    wms_group           VARCHAR(100),
    wfs_available       BOOLEAN DEFAULT TRUE NOT NULL,
    wfs_layer_name      VARCHAR(200),
    downloadable        BOOLEAN DEFAULT TRUE NOT NULL,
    metadata_layer      VARCHAR(200),
    default_date        JSONB,
    time_enabled        BOOLEAN DEFAULT FALSE NOT NULL,
    time_style_pattern  VARCHAR(200),
    raster_periodicity  JSONB,
    hide_periodicity    BOOLEAN DEFAULT FALSE NOT NULL,
    default_zoom        JSONB,
    zoom_range          JSONB,
    search_tags         TEXT[],
    searchable_fields   TEXT[],
    has_municipio       BOOLEAN DEFAULT FALSE NOT NULL,
    has_direccion       BOOLEAN DEFAULT FALSE NOT NULL,
    municipio_field     VARCHAR(100),
    direccion_field     VARCHAR(100),
    infobox_template    VARCHAR(50),
    infobox_params      JSONB,
    infobox_config      JSONB,
    created_at          TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at          TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_by          VARCHAR(100),
    CONSTRAINT ck_layers_node_type CHECK (node_type IN ('tema','category','label','group','leaf')),
    CONSTRAINT fk_layers_parent FOREIGN KEY (parent_id) REFERENCES mapalab.layers(id) ON DELETE CASCADE,
    CONSTRAINT fk_layers_workspace FOREIGN KEY (workspace_alias) REFERENCES mapalab.workspaces(alias) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_layers_parent ON mapalab.layers(parent_id);
CREATE INDEX IF NOT EXISTS idx_layers_node_type ON mapalab.layers(node_type);
CREATE INDEX IF NOT EXISTS idx_layers_search ON mapalab.layers USING GIN(search_tags);
CREATE INDEX IF NOT EXISTS idx_layers_workspace ON mapalab.layers(workspace_alias) WHERE workspace_alias IS NOT NULL;

CREATE TABLE IF NOT EXISTS mapalab.initial_layer_order (
    layer_id    VARCHAR(100) PRIMARY KEY REFERENCES mapalab.layers(id) ON DELETE CASCADE,
    sort_order  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS mapalab.layer_tree_cache (
    id                      INTEGER PRIMARY KEY,
    etag                    VARCHAR(64) NOT NULL,
    tree                    JSONB NOT NULL,
    initial_order           JSONB NOT NULL,
    workspaces              JSONB NOT NULL,
    source_max_updated_at   TIMESTAMPTZ,
    layer_count             INTEGER DEFAULT 0 NOT NULL,
    updated_at              TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    CONSTRAINT ck_layer_tree_cache_singleton CHECK (id = 1)
);

CREATE TABLE IF NOT EXISTS mapalab.layer_metadata (
    layer_key               VARCHAR(300) PRIMARY KEY,
    workspace               VARCHAR(200),
    layer_name_db           VARCHAR(200),
    layer_name_usuario      VARCHAR(300),
    descripcion             TEXT,
    fuentes                 JSONB,
    metodologia             JSONB,
    metadato                JSONB,
    frecuencia              VARCHAR(200),
    fecha_ultima            VARCHAR(200),
    tipo_mapa               VARCHAR(100),
    tipo_mapa_enlace        VARCHAR(500),
    texto_leyenda           TEXT,
    tarjeta_punto_poligono  VARCHAR(50),
    link_final_capa         VARCHAR(500),
    downloadable            BOOLEAN DEFAULT TRUE NOT NULL,
    created_at              TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at              TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_by              VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_layer_metadata_workspace ON mapalab.layer_metadata(workspace);

CREATE TABLE IF NOT EXISTS mapalab.layer_stats (
    layer_key            VARCHAR(300) PRIMARY KEY REFERENCES mapalab.layer_metadata(layer_key) ON DELETE CASCADE,
    stats_config         JSONB DEFAULT '[]'::jsonb NOT NULL,
    values               JSONB DEFAULT '[]'::jsonb NOT NULL,
    pie_numeralia        VARCHAR(500),
    values_refreshed_at  TIMESTAMPTZ,
    ttl_minutes          INTEGER DEFAULT 1440 NOT NULL
);

CREATE TABLE IF NOT EXISTS mapalab.alembic_version_dataengine (
    version_num VARCHAR(32) PRIMARY KEY
);

-- Solo stampear el baseline 0003 si la tabla esta vacia. Si alembic ya avanzo
-- a 0004+, NO insertamos 0003 porque crearia un head fantasma (multi-row →
-- alembic upgrade head falla con "overlaps with other revisions").
INSERT INTO mapalab.alembic_version_dataengine (version_num)
SELECT '0003_metadata_stats'
WHERE NOT EXISTS (SELECT 1 FROM mapalab.alembic_version_dataengine);

COMMIT;
