# Context

Snapshot del estado del proyecto al 2026-04-22 (version actual: `1.5.0`). Este archivo es un mapa archivo → feature para referencia rapida y una lista de TODOs/limpiezas pendientes.

## TODOs / pendientes

### Documentacion
- [x] **Version visible en `README.md`** (verificado 2026-04-23): ya presente como `**Version:** 1.5.0 ([changelog](docs/CHANGELOG.md))` en la primera linea despues del titulo.
- [ ] Sincronizar `jobs/README.md` con `docs/jobs.md` — hoy los dos documentan el container pero con solapamiento. Decidir si se conserva `jobs/README.md` (util si se publica la imagen sola) o se deja `docs/jobs.md` como fuente unica y `jobs/README.md` como stub que referencia
- [ ] Crear/migrar `.env.example`: actualmente lista variables pero falta `PGBOUNCER_PORT` documentado claramente, `ENV` con sus valores validos explicitos, y las variables opcionales `MAPALAB_STATS_DB_USER` / `MAPALAB_STATS_DB_PASSWORD` / `DATAENGINE_URL`

### Limpieza de codigo muerto
- [x] **`postgres/replica/start-replica.sh`** — eliminado 2026-04-23 (huerfano desde `1.2.0`). Cambio staged como `D` en git; pendiente commit.
- [x] **`postgres/primary/init/02-init-replication.sh`** — eliminado 2026-04-23 (mismo caso).
- [x] **`jobs/run_bootstrap.py` y toda la cadena del Google Sheet ETL** (legacy deprecado en `1.5.0`): eliminados en `1.6.0` (`core/mapalab_card/`, `core/schemas/mapalab_card.py`, `alembic/mapalab_card/`, deps `pandas/gspread/google-auth`, credenciales Google). Se conservo `jobs/bootstrap/run_migrate_mapalab_card.py` como herramienta de recuperacion idempotente
- [ ] **Drop de `public.mapalab_card`**: la tabla sigue viva en produccion como respaldo. Una vez validado que mariachi es la unica fuente de verdad, ejecutar `DROP TABLE IF EXISTS public.mapalab_card;` y eliminar `jobs/bootstrap/run_migrate_mapalab_card.py`

### Bugs / inconsistencias detectadas durante la revision
- [x] **Schedule del cron de backup** (verificado 2026-04-23): README dice "dump semanal (domingos 02:00 UTC)" — alineado con `backup/crontab` `0 2 * * 0` y con CHANGELOG 1.1.1. Sin drift.
- [ ] **`jobs/run_refresh_layer_stats.py`** declara el `operation` `latest` pero el `field` requerido no esta bajo validacion `_is_identifier` cuando `op == 'count'` (caso borde). No es bug critico pero vale revisarlo
- [x] **`docker-compose.yml`** (verificado 2026-04-23): el mount `${BACKUP_DATA}/mapalab_card:/app/data/backups` ya no existe en el servicio `jobs`. Se removio junto con el ETL legacy. Actualmente jobs no tiene mount de backups (no lo necesita).

### Infraestructura
- [ ] Evaluar si `scripts/optimize_delitos_views.sql` sigue vigente (no se ejecuta desde el Makefile, requiere ejecucion manual sobre la DB)
- [ ] Considerar dump de prueba `restore/iieg_gis_20260422_170247.sql.gz` (6.6 MB, esta local y gitignored) — purgar del working dir si ya no se necesita

## Mapa de features → archivos

### Stack base (1.0.0)

| Feature | Archivos |
|---|---|
| Cluster primary (con SSL, PostGIS) | `docker-compose.yml` → `postgres-primary`; `postgres/primary/entrypoint.sh`, `postgres/primary/config/postgresql.conf` |
| `pg_hba.conf` dinamico por `ALLOWED_HOSTS` | `postgres/primary/init/01-pg-hba.sh` |
| Certificados SSL | `make certs` (Makefile:45-69), `postgres/certs/*` (gitignored), bind mount en compose |
| Servicio de backup + subida a AO | `backup/Dockerfile`, `backup/crontab`, `backup/scripts/backup.sh`, `backup/scripts/upload-ao.sh`, `backup/scripts/cleanup.sh` |
| Restore con auto-deteccion y spinner | `restore/do-restore.sh` (host wrapper), `restore/restore.sh` (en container) |
| Control de volumenes via envs | `.env.example` → `POSTGRES_PRIMARY_DATA`, `BACKUP_DATA`, `PGDATA` |

### mapalab_card ETL legacy — eliminado (v1.7.0)

El ETL del Google Sheet (`run_bootstrap.py`, `core/mapalab_card/*`, `core/schemas/mapalab_card.py`, `alembic/mapalab_card/*`, deps `pandas`/`gspread`/`google-auth`, credenciales `iieg2025-cloud-*.json`) fue eliminado en v1.7.0. La fuente de verdad es `mapalab.layer_metadata` + `mapalab.layer_stats`, editables desde mariachi.

**Preservado** como herramienta de recuperación idempotente:

| Feature | Archivos |
|---|---|
| Migracion 1-shot `mapalab_card` → `layer_metadata`/`layer_stats` | `jobs/bootstrap/run_migrate_mapalab_card.py` (self-contained, solo SQLAlchemy + psycopg2) |

Invocable desde `scripts/bootstrap-v14.sh` (paso 5) o directamente con `docker compose exec jobs python bootstrap/run_migrate_mapalab_card.py --apply`. La tabla `public.mapalab_card` puede dropearse cuando se confirme que todo esta migrado.

### Refresh jobs diarios (1.5.0)

| Feature | Archivos |
|---|---|
| Periodicidad (refresh) | `jobs/run_refresh_periodicity.py`, `scripts/refresh_periodicity.sql` (rebuild de la funcion), `scripts/check_periodicity.sql` (diagnostico) |
| Layer tree cache | `jobs/run_refresh_layer_tree.py` → `mapalab.layer_tree_cache` singleton |
| Layer stats (template catalog) | `jobs/run_refresh_layer_stats.py` → `mapalab.layer_stats.values` |
| Cron del container | `jobs/crontab` (03:00/04:00/04:30), `jobs/Dockerfile`, `jobs/entrypoint.sh` |
| Targets make | `Makefile:126-137` (`refresh-layer-tree`, `refresh-layer-stats`, `refresh-all`), `Makefile:150-161` (`logs-jobs`, `refresh-periodicity`, `check-periodicity`) |

### Ownership del schema mapalab.* (2026-04-23)

**Alembic en mariachi es la fuente autoritativa** de DDL del schema `mapalab.*` hacia adelante. `jobs/bootstrap/v14_schema.sql` queda frozen como baseline de bootstrap de v1.4.0 — no se modifica. Cambios futuros (agregar columna, nueva tabla, index) entran como migracion alembic en `mariachi/api/alembic/versions/dataengine/`. Ver `gateway-hub/docs/ecosystem.md` seccion 7.3.

Guardrail: `gateway-hub/scripts/check-model-drift.py` compara modelos SQLAlchemy de mapalab y mariachi y reporta drift de columnas.

### Bootstrap v1.4.0 MapaLab (1.5.0)

| Feature | Archivos |
|---|---|
| Orquestador 5 pasos | `scripts/bootstrap-v14.sh` |
| DDL + seed workspaces | `jobs/bootstrap/v14_schema.sql` |
| Seed de layers desde JSON | `jobs/bootstrap/run_seed_layers.py` |
| Migracion `mapalab_card` → `layer_metadata`/`layer_stats` | `jobs/bootstrap/run_migrate_mapalab_card.py` |
| Target make | `make prod-migration` (orquesta ETL Sheet + bootstrap + seed + migrate + stamp) |

### PgBouncer (1.4.0)

| Feature | Archivos |
|---|---|
| Pooler transaction mode | `pgbouncer/pgbouncer.ini` |
| Generacion dinamica de `userlist.txt` | `pgbouncer/entrypoint.sh` |
| Servicio compose | `docker-compose.yml` → `pgbouncer` |

### Periodicidad de capas (1.3.0)

| Feature | Archivos |
|---|---|
| Funcion SQL + tabla | `scripts/refresh_periodicity.sql` |
| Diagnostico | `scripts/check_periodicity.sql` |
| Targets make | `Makefile:153-161` |

### Seguridad y acceso

| Feature | Archivos |
|---|---|
| SSL end-to-end | certs en `postgres/certs/`, montados read-only; `postgres/primary/entrypoint.sh` verifica existencia |
| ACL por `ALLOWED_HOSTS` | `postgres/primary/init/01-pg-hba.sh` |
| Credenciales GCP fuera del repo | `.gitignore` → `jobs/iieg2025-cloud-*.json`; doc en `docs/jobs.md#credencial-gcp` |
| Template catalog (no SQL libre) | `jobs/run_refresh_layer_stats.py` — `STATS_OPERATIONS`, `_is_identifier`, `_build_query` |

## Variables de entorno (donde se usan)

| Variable | Usada en | Proposito |
|---|---|---|
| `ENV` | `Makefile` (gate de `backup` y `cron-install`), `scripts/bootstrap-v14.sh` | `production` vs resto |
| `POSTGRES_USER/PASSWORD/DB` | `docker-compose.yml`, `backup/*`, `pgbouncer/entrypoint.sh`, `postgres/*` | BD principal |
| `ALLOWED_HOSTS` | `postgres/primary/init/01-pg-hba.sh` | ACL en pg_hba |
| `PG_BIND_ADDRESS`, `PG_PRIMARY_PORT`, `PGBOUNCER_PORT` | `docker-compose.yml` | binding externo |
| `POSTGRES_PRIMARY_DATA`, `BACKUP_DATA`, `PGDATA` | `docker-compose.yml` | volumenes |
| `AO_ENDPOINT/BUCKET/ACCESS_KEY/SECRET_KEY` | `backup/scripts/upload-ao.sh` | Acervo de Objetos |
| `DATAENGINE_DB_*` | `docker-compose.yml` → `jobs`, `jobs/run_refresh_*.py`, `jobs/bootstrap/*` | credenciales del container jobs (renombradas desde `MAPALAB_CARD_DB_*` en v1.7.0) |
| `MAPALAB_STATS_DB_USER/PASSWORD` | `jobs/run_refresh_layer_stats.py` | override opcional para stats refresh |
| `DATAENGINE_URL` | `jobs/run_refresh_*.py`, `jobs/bootstrap/run_seed_layers.py`, `jobs/bootstrap/run_migrate_mapalab_card.py` | URL completa alternativa a `DATAENGINE_DB_*` |
| `CRON_SCHEDULE` | `Makefile` | hora del cron host (legacy; el cron efectivo corre dentro del container `jobs`) |
| `DEBUG` | `backup/do-backup.sh`, `restore/do-restore.sh`, `backup/scripts/backup.sh`, `restore/restore.sh` | verbose pg_dump/pg_restore |

## Comandos make (agrupados)

Para la tabla completa ver `README.md`. Este es el agrupamiento por responsabilidad:

- **Lifecycle:** `up` (incluye `certs` + `cron-install` si `ENV=production`), `down`, `restart`, `build`, `ps`, `clean`
- **Observabilidad:** `logs`, `logs-primary`, `logs-backup`, `logs-jobs`
- **DB:** `shell`, `backup` (gate `ENV=production`), `restore FILE=`, `restore-local FILE=`
- **Jobs sobre `mapalab`:** `card` (legacy), `refresh-periodicity`, `refresh-layer-tree`, `refresh-layer-stats`, `refresh-all`, `check-periodicity`
- **Prod migration MapaLab v1.4:** `prod-migration` (consolidado — antes eran `bootstrap-v14{,-dry}` y `migrate-mapalab-card`)
- **Infra:** `certs`, `cron-install`, `cron-remove`

## Convenciones del proyecto

- Conventional commits en ingles (`feat:`, `fix:`, `refactor:`, `docs:`, `chore:`, `style:`, `build:`); scoping opcional (`feat(jobs): ...`)
- README + docs en Espanol sin acentos (sigue el patron del repo original)
- Shell scripts en `sh` POSIX donde sea posible, `bash` cuando requieren features (arrays, process substitution)
- SQL en `scripts/` para operaciones idempotentes o de diagnostico
- `.gitignore` cubre: `.env`, volumenes, certs, dumps, credenciales GCP, scratch del bootstrap
