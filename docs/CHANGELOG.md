# Changelog

Todos los cambios notables del proyecto se documentan en este archivo.

El formato esta basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/),
y este proyecto se adhiere a [Versionado Semantico](https://semver.org/lang/es/). El versionado
de `mapalab-dataengine` es independiente del de MapaLab.

## [No publicado]

## [1.0.0] - 2026-04-22

Primera version estable. Consolida la infraestructura en produccion: primary con SSL + PostGIS,
pooler con PgBouncer, respaldos automaticos con subida al Acervo de Objetos, y el container
`jobs` con cron diario sobre el schema `mapalab`.

### Agregado
- **Container `jobs`** (rebautizado desde `mapalab-card`, container `dataengine-jobs`) corriendo `cron -f` con 3 tareas diarias sobre el schema `mapalab`
  - 03:00 `run_refresh_periodicity.py` — invoca `SELECT public.refresh_layer_periodicity()` y cuenta filas de `public.layer_periodicity`
  - 04:00 `run_refresh_layer_tree.py` — reconstruye `mapalab.layer_tree_cache` (singleton JSONB con `etag`, `tree`, `initial_order`, `workspaces`)
  - 04:30 `run_refresh_layer_stats.py` — evalua `stats_config` de cada `mapalab.layer_stats` via template catalog
- **Bootstrap idempotente del schema `mapalab`** para MapaLab v1.4.0+: `make bootstrap-v14 LAYERS_JSON=<path>`
  - `scripts/bootstrap-v14.sh` orquesta 5 pasos: rol `mariachi_layers`, schema `mapalab` + ownership, tablas + seed de workspaces, seed de `mapalab.layers` desde JSON, migracion de `public.mapalab_card` → `mapalab.layer_metadata` + `mapalab.layer_stats`
  - `jobs/bootstrap/v14_schema.sql` crea 6 tablas (`workspaces`, `layers`, `initial_layer_order`, `layer_tree_cache`, `layer_metadata`, `layer_stats`) + indices + FKs + checks + marca de version `0003_metadata_stats` en `mapalab.alembic_version_dataengine`
  - `jobs/bootstrap/run_seed_layers.py` aplana el tree exportado, infiere `node_type`, detecta prefijo `*` como `disabled=true`, ordena topologicamente y upsertea (`ON CONFLICT DO UPDATE`)
  - `jobs/bootstrap/run_migrate_mapalab_card.py` migra filas legacy deduplicando por `layer_key` y arma `fuentes`, `metodologia`, `metadato`, numeralia como JSONB
  - Flags: `--dry-run`, `--skip-role`, `--skip-schema`, `--skip-seed`, `--skip-migrate`, `--password <val>`
  - `make bootstrap-v14-dry` para validar sin persistir
- **Template catalog** en `run_refresh_layer_stats.py`: 8 operaciones validadas (`count`, `count_distinct`, `count_where`, `sum`, `avg`, `min`, `max`, `latest`). Identificadores validados con regex (`[A-Za-z0-9_]{1,100}`), valores bindeados como `:param`. Reemplaza cualquier forma de SQL libre
- **PgBouncer** (`edoburu/pgbouncer:latest`) como connection pooler expuesto en `${PGBOUNCER_PORT:-6432}`, healthcheck con `pg_isready`. Config en `pgbouncer/pgbouncer.ini` + `pgbouncer/entrypoint.sh`
- **Respaldos automaticos** en `pg-backup`: dump diario a las 08:00, retencion 7 dias, subida al Acervo de Objetos. Solo en `ENV=production`. `DEBUG=1` para verbose. `make backup` fuerza respaldo manual
- **Periodicidad de capas**: funcion SQL `public.refresh_layer_periodicity()` + tabla `public.layer_periodicity`. `scripts/refresh_periodicity.sql` (rebuild), `scripts/check_periodicity.sql` (diagnostico)
- **Control de acceso via `pg_hba.conf`** generado por `postgres/primary/init/00-pg-hba.sh`: conexiones locales, red interna de Docker, IPs explicitas en `ALLOWED_HOSTS`
- **SSL** con certificados autogenerados en `postgres/certs/` via `make certs` (CA 10 anos, server 2 anos, idempotente)
- **Restore**: `make restore FILE=<dump>` dentro del container primary y `make restore-local FILE=<dump>` contra una BD remota usando vars del `.env`. Formatos `.dump`, `.sql`, `.sql.gz`
- **Targets make**: `up`, `down`, `restart`, `build`, `ps`, `logs`, `logs-primary`, `logs-backup`, `logs-jobs`, `shell`, `backup`, `restore`, `restore-local`, `clean`, `certs`, `card`, `refresh-periodicity`, `refresh-layer-tree`, `refresh-layer-stats`, `refresh-all`, `check-periodicity`, `bootstrap-v14`, `bootstrap-v14-dry`, `cron-install`, `cron-remove`
- **Cron host** para `make card` instalado por `make up` solo en `ENV=production`, removible con `make cron-remove`
- **Documentacion**: `docs/architecture.md`, `docs/jobs.md`, `docs/bootstrap-v14.md`, `docs/CHANGELOG.md`

### Deprecado
- **`run_bootstrap.py`** (ETL legacy del Google Sheet → `public.mapalab_card`): noop por defecto. Requiere `FORCE_LEGACY_ETL=1` para correr. La fuente de verdad es `mapalab.layer_metadata` + `mapalab.layer_stats`, editable desde mariachi (`/administrador/mapalab/layers`)

### Seguridad
- Credencial de service account GCP fuera del repo: patron `jobs/iieg2025-cloud-*.json` en `.gitignore`. Se monta en el host y se referencia via `MAPALAB_CARD_GOOGLE_CREDENTIALS_PATH`
- Template catalog elimina SQL libre en `stats_config` (ver Agregado)
- Conexiones PostgreSQL restringidas por `pg_hba.conf` con whitelist via `ALLOWED_HOSTS`
