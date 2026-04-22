# Changelog

Todos los cambios notables del proyecto se documentan en este archivo.

El formato esta basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/),
y este proyecto se adhiere a [Versionado Semantico](https://semver.org/lang/es/). El versionado
de `mapalab-dataengine` es independiente del de MapaLab.

## [No publicado]

## [1.5.0] - 2026-04-22

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

## [1.4.0] - 2026-04-14

### Agregado
- **PgBouncer** (`edoburu/pgbouncer:latest`) como connection pooler expuesto en `${PGBOUNCER_PORT:-6432}`
  - `pgbouncer/pgbouncer.ini`: `pool_mode = transaction`, `default_pool_size = 40`, `max_client_conn = 300`, `min_pool_size = 10`, `reserve_pool_size = 5`, `auth_type = scram-sha-256`
  - `pgbouncer/entrypoint.sh` genera `userlist.txt` dinamicamente desde `${POSTGRES_USER}/${POSTGRES_PASSWORD}` + usuario admin `pgbouncer_admin`
  - healthcheck con `pg_isready -h localhost -p 6432`
- Configuracion de PostgreSQL optimizada para produccion en `postgres/primary/config/postgresql.conf` montada al primary

### Cambiado
- `docker-compose.yml` agrega el servicio `pgbouncer` a `dataengine-network` con dependencia de `postgres-primary` healthy
- Primary arranca con `postgres -c config_file=/etc/postgresql/postgresql.conf`

## [1.3.1] - 2026-03-30

### Cambiado
- Backups y cron jobs ahora respetan `ENV`: solo se ejecutan en `ENV=production` (de lo contrario emiten warning y salen limpiamente). Comprobacion en `Makefile` (`backup`, `cron-install`)
- `backup/scripts/backup.sh` usa `pg_dump --format=custom --compress=5` con SSL verify-ca
- Retencion consistente en dumps SQL y CSV

### Eliminado
- Configuracion no usada de `insert date` en el ETL de `mapalab_card`

## [1.3.0] - 2026-03-27

### Agregado
- **Periodicidad de capas**: funcion SQL `public.refresh_layer_periodicity()` + tabla `public.layer_periodicity` que calcula y cachea la periodicidad por capa
- `scripts/refresh_periodicity.sql` — migracion/rebuild de la funcion
- `scripts/check_periodicity.sql` — diagnostico: muestra si la periodicidad esta al dia
- `make refresh-periodicity` invoca directamente la funcion SQL via `psql` (antes el refresh pasaba por un service Python)
- `make check-periodicity` corre el diagnostico sobre el primary
- `make card` incluye `refresh-periodicity` al final

### Cambiado
- El refresh de periodicidad deja de ser un script Python + SQLAlchemy: invocacion directa `SELECT public.refresh_layer_periodicity()` (menos dependencias, mas rapido)

## [1.2.0] - 2026-03-18

### Eliminado
- **Servicio `postgres-replica`** (streaming replication hot-standby), rol `replication_user` y configuracion `postgres/replica/*`. Puerto `5433` deja de existir. Clientes que apuntaban a la replica deben migrar al primary en `5432` o al pooler en `6432`
- Credenciales `REPLICATION_USER` / `REPLICATION_PASSWORD` del `.env.example`
- Comandos make `logs-replica` y `shell-replica`

### Corregido
- `postgres/primary/init/01-pg-hba.sh` corrige el caso del `replication_user` antes de eliminarlo, para no romper stacks con volumen existente durante el rollout

## [1.1.2] - 2026-03-12

### Agregado
- Entrypoint del servicio `mapalab-card` corre `alembic upgrade head` antes del proceso principal (migraciones automaticas)
- DEBUG flag en backup y restore para output verbose (`DEBUG=1 make backup`, `DEBUG=1 make restore FILE=...`)
- Entrada host adicional en `pg_hba.conf`

### Cambiado
- Ingesta del Google Sheet: `strip()` aplicado a todas las columnas string; representaciones vacias (`""`, `"nan"`, `"none"`, `"null"`) normalizadas a `None`
- `fecha_ultima_actualizacion` cambia de `Date` a `String` para soportar valores de solo ano (`"2023"`) y anos numericos puros

### Eliminado
- Comandos y codigo de firewall (`fw-status`, `fw-setup`, `fw-reset`): reemplazado definitivamente por `pg_hba.conf` + `ALLOWED_HOSTS`

### Corregido
- Whitespace al inicio/fin en columnas durante ingesta causaba duplicados logicos
- Parsing de `fecha_ultima_actualizacion` rompia con valores numericos (ej. `2023` como int)
- Trailing space en llave `Descripción` en diccionario de actions

## [1.1.1] - 2026-03-09

### Agregado
- **`backup/do-backup.sh`** — wrapper en host con spinner animado (frames braille), tiempo transcurrido y stream en tiempo real del log del container. `make backup` delega a este script
- Naming y politicas de retencion estandarizadas para dumps SQL y CSV; cron del backup ahora semanal (domingos 02:00)
- **Firewall management** (`fw-status`, `fw-setup`, `fw-reset`) en el Makefile — removido en 1.1.2
- `scripts/optimize_delitos_views.sql`: SQL views optimizadas para agregacion de datos de delitos
- Variable `BACKUP_DATA` parametriza el volumen de backups (incluyendo `${BACKUP_DATA}/mapalab_card`)

### Cambiado
- `make restart` incluye `fw-setup` + `cron-install`

### Corregido
- Restore mas robusto ante archivos malformados o inexistentes
- Comentarios y docstrings redundantes eliminados para claridad

## [1.1.0] - 2026-03-08

### Agregado
- **Servicio `mapalab-card`** (container `dataengine-mapalab-card`): ETL desde Google Sheet a `public.mapalab_card` usando `gspread` + `pandas` + `sqlalchemy` + `psycopg2`
  - Framework propio en `mapalab_card/core/` (`action.py`, `etl.py`, `source.py`) con acciones `actinsert`, `actbackup`, `actmapdata` y source `srcdatatabular`
  - Config por envs `MAPALAB_CARD_*` (DB + sheets + dirs)
  - `ID` se resetea a `1` antes de cada ingesta
  - Dropping de filas null
- **Alembic migrations** para `mapalab_card`: `377c681a4c1c_crear_tabla_mapalab_card.py` (tabla inicial)
- **`make card`** dispara la ingesta via `docker compose exec`
- **Cron job host** en el `Makefile`: `make cron-install` instala un entry de crontab que ejecuta `make card` a la hora configurada en `CRON_SCHEDULE` (`HH:MM`). `make cron-remove` lo desinstala
- Credenciales de Google Sheets via env (`MAPALAB_CARD_GOOGLE_CREDENTIALS_PATH`, `MAPALAB_CARD_GOOGLE_SHEET_URL`)
- `.gitignore` con entradas especificas para `mapalab_card/**/*.env`, `mapalab_card/**/*.csv` y la credencial JSON de GCP
- README del servicio en `mapalab_card/README.md`

## [1.0.0] - 2026-02-25

Primera version del stack en produccion. Consolida el cluster PostgreSQL con replica, respaldos al Acervo de Objetos, SSL, control de acceso dinamico y restore con deteccion de formato.

### Agregado
- **Cluster PostgreSQL primary + replica** (streaming replication hot-standby) sobre la imagen `postgis/postgis:18-3.6-alpine`. Primary expuesto en `${PG_PRIMARY_PORT:-5432}`, replica en `${PG_REPLICA_PORT:-5433}`
- **Servicio `pg-backup`** (imagen propia en `./backup`): cron con `crond -f -l 8`, dumps diarios a `/backups` con `pg_dump --format=custom`, subida al Acervo de Objetos via MinIO `mc`, cleanup de dumps `+30 dias`
- **SSL obligatorio** (`sslmode=verify-ca`) entre pg-backup y primary; certificados en `postgres/certs/` generados por `make certs` (CA autofirmada + cert de servidor) y montados como bind mount
- **Control de acceso dinamico** con `postgres/primary/init/01-pg-hba.sh`: siempre permite local + red Docker (`172.16.0.0/12`); para cada IP en `${ALLOWED_HOSTS}` agrega linea `hostssl ... scram-sha-256`; al final `reject` catch-all
- **Replica setup** (`postgres/replica/start-replica.sh` + `postgres/primary/init/02-init-replication.sh`): `pg_basebackup` contra primary, chequeo de system identifier para evitar rebase incorrecto, `pg_isready` explicit a base `postgres`
- **Entrypoint custom del primary** (`postgres/primary/entrypoint.sh`): verifica certs, corrige ownership y permisos (`600` a `server.key`), luego delega a `docker-entrypoint.sh`
- **Restore con deteccion de formato** (`restore/do-restore.sh` + `restore/restore.sh`):
  - auto-deteccion: si no se pasa `FILE`, toma el unico archivo en `./restore/` o presenta un menu numerado con tamanos humanizados
  - inspeccion del header: `PGDMP` → `pg_restore --clean --if-exists --no-owner --no-acl`; `.gz` → `gunzip | psql`; fallback `psql -f`
  - crea PostGIS extensions automaticamente antes del restore
  - spinner animado + stream en tiempo real del log del container
  - mode `continue-on-error` para pg_restore (acepta codigo 1 como warning)
- **Docker named volumes** con prefijo `dataengine` (`dataengine-primary-data`, `dataengine-replica-data`, `dataengine-backups-data`) y red `dataengine-network`
- **Variable `PGDATA`** configurable: permite apuntar a path custom dentro del container
- **MinIO `mc` client** copiado al build del backup (curl eliminado al finalizar), alias `acervo` configurado dinamicamente via env vars (`AO_ENDPOINT`, `AO_BUCKET`, `AO_ACCESS_KEY`, `AO_SECRET_KEY`); si no estan configurados, upload se skipea silenciosamente
- **Makefile** inicial con: `up`, `down`, `restart`, `build`, `ps`, `logs`, `logs-primary`, `logs-replica`, `logs-backup`, `shell`, `shell-replica`, `backup`, `restore`, `clean`, `certs`
- **`.env.example`** con lista de variables requeridas (postgres, AO, allowed hosts, ports)

### Cambiado
- Migracion de `postgres:18.2-alpine` → `postgis/postgis:18-3.6-alpine` (PostGIS + pg_restore preparado para GIS)
- Replace de `supercronic` → `crond` nativo en el container de backup
- SSL cert generation movido de init script → custom entrypoint (evita recrear si ya existen)

### Corregido
- `pg_isready` en replica apunta explicitamente a DB `postgres` (fix para race condition al arranque)
- `pg_restore` continua en errores no fatales (codigo 1) para que rebuilds no quiebren por issues cosmeticos
