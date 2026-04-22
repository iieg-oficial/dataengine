# Changelog

Todos los cambios notables del proyecto se documentan en este archivo.

El formato esta basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/),
y este proyecto se adhiere a [Versionado Semantico](https://semver.org/lang/es/). El versionado
de `mapalab-dataengine` es independiente del de MapaLab.

## [No publicado]

## [1.4.0] - 2026-04-22

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
- **Template catalog** en `run_refresh_layer_stats.py`: 8 operaciones validadas (`count`, `count_distinct`, `count_where`, `sum`, `avg`, `min`, `max`, `latest`) reemplazan SQL libre. Identificadores validados con regex (`[A-Za-z0-9_]{1,100}`), valores bindeados como `:param`
- **Targets make**: `refresh-layer-tree`, `refresh-layer-stats`, `refresh-all`, `logs-jobs`, `bootstrap-v14`, `bootstrap-v14-dry`, `restore-local`
- **Crontab** del container jobs (`/etc/cron.d/jobs`) y entrypoint que exporta `MAPALAB_CARD_*` + `DATAENGINE_*` a `/etc/environment` para que cron vea las vars
- Documentacion reorganizada: `docs/architecture.md` (componentes + diagrama Mermaid + schema), `docs/jobs.md` (cron container + template catalog + credencial GCP), `docs/bootstrap-v14.md` (pasos + flags + idempotencia), `docs/CHANGELOG.md` (este archivo)
- `.gitignore`: patron `jobs/iieg2025-cloud-*.json` (credencial de service account GCP no versionada) y `jobs/bootstrap/_layers_export.json` (scratch del bootstrap)

### Cambiado
- `mapalab_card/` → `jobs/` (git mv preservando historia); servicio docker `mapalab-card` → `jobs` (container `dataengine-mapalab-card` → `dataengine-jobs`). Scripts externos que invoquen el servicio o lean sus logs deben actualizarse
- `jobs/Dockerfile` instala `cron`, copia `crontab` a `/etc/cron.d/jobs` (mode 0644), crea `/var/log/cron.log`
- `jobs/entrypoint.sh` ejecuta alembic legacy best-effort, exporta envs a `/etc/environment`, hace `tail -F` del log y pasa control al `CMD` (`cron -f`)
- README raiz reescrito: eliminadas referencias al servicio `mapalab-card` ya renombrado. Documentacion profunda movida a `docs/`
- `make card` queda como shim del legacy + `refresh-periodicity`

### Deprecado
- `run_bootstrap.py` (ETL del Google Sheet → `public.mapalab_card`): noop por defecto. Requiere `FORCE_LEGACY_ETL=1` para correr. La fuente de verdad es `mapalab.layer_metadata` + `mapalab.layer_stats`, editable desde mariachi (`/administrador/mapalab/layers`)

### Seguridad
- Credencial de service account GCP fuera del repo (ver `.gitignore` y `docs/jobs.md`)
- Template catalog reemplaza SQL libre en `stats_config` (ver Agregado)

## [1.3.0] - 2026-04-14

### Agregado
- **PgBouncer** (`edoburu/pgbouncer:latest`) como connection pooler expuesto en `${PGBOUNCER_PORT:-6432}`, healthcheck con `pg_isready`. Config en `pgbouncer/pgbouncer.ini` + `pgbouncer/entrypoint.sh`
- Configuracion de PostgreSQL optimizada para produccion en `postgres/primary/config/postgresql.conf` montada al primary

### Cambiado
- `docker-compose.yml` agrega el servicio `pgbouncer` a `dataengine-network` con dependencia de `postgres-primary` healthy
- Primary arranca con `postgres -c config_file=/etc/postgresql/postgresql.conf`

## [1.2.1] - 2026-03-30

### Cambiado
- Backups y cron jobs ahora respetan `ENV`: solo se ejecutan en `ENV=production` (de lo contrario emiten warning y salen limpiamente)
- `backup/do-backup.sh` comprime con mejor ratio; retencion consistente en dumps SQL y CSV

### Eliminado
- Configuracion no usada de `insert date`

## [1.2.0] - 2026-03-27

### Agregado
- **Periodicidad de capas**: funcion SQL `public.refresh_layer_periodicity()` + tabla `public.layer_periodicity` que calcula y cachea la periodicidad por capa
- `scripts/refresh_periodicity.sql` — migracion/rebuild de la funcion
- `scripts/check_periodicity.sql` — diagnostico: muestra si la periodicidad esta al dia
- `make refresh-periodicity` invoca directamente la funcion SQL via `psql` (antes el refresh pasaba por un service Python)
- `make check-periodicity` corre el diagnostico sobre el primary
- `make card` incluye `refresh-periodicity` al final

### Cambiado
- El refresh de periodicidad deja de ser un script Python + SQLAlchemy: invocacion directa `SELECT public.refresh_layer_periodicity()` (menos dependencias, mas rapido)

## [1.1.0] - 2026-03-18

### Eliminado
- **Servicio `postgres-replica`** (streaming replication hot-standby), rol `replication_user` y configuracion `postgres/replica/`. Puerto `5433` deja de existir. Clientes que apuntaban a la replica deben migrar al primary en `5432` o al pooler en `6432`
- Credenciales `REPLICATION_USER` / `REPLICATION_PASSWORD` del `.env.example`
- Comandos make `logs-replica` y `shell-replica`

### Corregido
- `postgres/primary/init/01-pg-hba.sh` corrige el caso del `replication_user` antes de eliminarlo, para no romper stacks con volumen existente durante el rollout

## [1.0.2] - 2026-03-12

### Agregado
- Entrypoint de `mapalab-card` corre `alembic upgrade head` antes del proceso principal (migraciones automaticas)
- DEBUG flag en backup y restore para output verbose (`DEBUG=1 make backup`)
- Entrada host adicional en `pg_hba.conf`

### Cambiado
- Ingesta del Google Sheet: `strip()` aplicado a todas las columnas string; representaciones vacias (`""`, `"nan"`, `"none"`, `"null"`) normalizadas a `None`
- `fecha_ultima_actualizacion` cambia de `Date` a `String` para soportar valores de solo ano (`"2023"`) y anos numericos puros

### Eliminado
- Comandos y codigo de firewall (`fw-status`, `fw-setup`, `fw-reset`): reemplazado por `pg_hba.conf` + `ALLOWED_HOSTS`

### Corregido
- Whitespace al inicio/fin en columnas durante ingesta causaba duplicados logicos
- Parsing de `fecha_ultima_actualizacion` rompia con valores numericos (ej. `2023` como int)

## [1.0.1] - 2026-03-09

### Agregado
- Script de backup delegado con spinner de progreso y output en tiempo real (`backup/do-backup.sh`)
- Naming y politicas de retencion estandarizadas para dumps SQL y CSV
- SQL views optimizadas para agregacion de datos de delitos en `scripts/optimize_delitos_views.sql`

### Cambiado
- Schedule de cron del backup de semanal → diario
- `make restart` incluye `fw-setup` + `cron-install`

### Corregido
- Restore mas robusto ante archivos malformados o inexistentes

## [1.0.0] - 2026-03-04

Primera version del stack en produccion.

### Agregado
- Stack PostgreSQL primary + replica hot-standby + `pg-backup`
- Servicio `mapalab-card`: ETL desde Google Sheet a `public.mapalab_card` (gspread + pandas + SQLAlchemy)
- Credenciales de Google Sheets via env (`MAPALAB_CARD_GOOGLE_*`)
- Alembic migrations para `mapalab_card`
- `make card` dispara la ingesta
- `make cron-install` / `cron-remove` para el cron host
- Respaldos automaticos a archivos + subida al Acervo de Objetos
- Comandos make base: `up`, `down`, `restart`, `logs`, `shell`, `backup`, `restore`, `clean`, `certs`
- Control de acceso inicial via firewall (reemplazado por `pg_hba.conf` en 1.0.2)
