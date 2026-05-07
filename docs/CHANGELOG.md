# Changelog

Todos los cambios notables del proyecto se documentan en este archivo.

El formato esta basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/),
y este proyecto se adhiere a [Versionado Semantico](https://semver.org/lang/es/). El versionado
de `mapalab-dataengine` es independiente del de MapaLab.

## [1.13.0] - 2026-05-07

Mientras el primer deploy a produccion no se haya completado, el Sheet de Google sigue siendo la fuente de verdad para `mapalab.layer_metadata`. Por eso `make prod-migration` vuelve a hacer pull del Sheet por default; el `--skip-etl` queda como opt-in para cuando se cierre el ciclo de testing y el Sheet se congele.

### Cambiado

- `scripts/prod-migration.sh`: `SKIP_ETL` default pasa de `1` a `0` (pull del Sheet activo por default). `--with-etl` deja de ser necesario; `--skip-etl` queda como opt-in.
- `Makefile`: ayuda de `prod-migration` actualizada — default `with-etl`, override con `PROD_MIGRATION_FLAGS="--skip-etl"`.
- Comentario de cabecera del script aclarado: revertir el default a `SKIP_ETL=1` tras el primer go-live a produccion.

---

## [1.12.2] - 2026-05-06

Refuerzo del rename agregado en 1.12.1: el migrador ahora también limpia las filas viejas con `layer_key` en formato pre-rename antes de hacer el upsert. Sin esto, al correr `prod-migration` en un ambiente que ya tenía filas con `mundial:*`, las nuevas filas con `eventos:*` se insertaban por separado (PK distinta) y quedaban duplicadas.

### Cambiado

- `run_migrate_mapalab_card.py::main` hace `DELETE` previo en `mapalab.layer_stats` y `mapalab.layer_metadata` para cada `WORKSPACE_RENAMES` y `LAYER_RENAMES` configurado, en orden seguro respecto a la FK `layer_stats_layer_key_fkey`.
- Idempotente: en ambientes limpios (sin filas viejas) los DELETE devuelven 0 rows y no afecta nada.

---

## [1.12.1] - 2026-05-06

`run_migrate_mapalab_card.py` (paso 5 del bootstrap v1.4.0) ahora normaliza el `layer_key` cuando el Sheet de Google usó un nombre de workspace distinto al que GeoServer/`mapalab.workspaces` tienen registrado.

### Cambiado

- **Mapeo de renames in-flight** en `jobs/bootstrap/run_migrate_mapalab_card.py`:
  - Workspace: `mundial` → `eventos` (todas las capas del mundial vivían bajo este alias en el Sheet, pero el workspace real en GeoServer es `eventos`).
  - Layer especifico: `mundial:sitios_interes` → `eventos:sitios_interes_direcciones` (nombre de la capa en GeoServer agrega sufijo `_direcciones`).
- Constantes `WORKSPACE_RENAMES` y `LAYER_RENAMES` + helper `normalize_layer_key`. Idempotente: si el `layer_key` ya viene en formato correcto pasa sin cambios.

### Por qué

Sin esto, `mapalab.layer_metadata` y `mapalab.layer_stats` quedaban con `layer_key = mundial:*`, pero los editores (mariachi, visor) buscan por `${workspaceAlias}:${geoserverLayer}` = `eventos:*`. Resultado: 11 metadatas "huérfanas" y los editores mostraban formularios vacíos para capas que sí tenían datos.

### Notas operativas

- Sin cambios en migración Alembic ni schema.
- `--with-etl` o `--skip-etl` ambos aplican el rename al final (el migrador siempre corre).
- Si el equipo del Sheet alguna vez corrige `mundial:` → `eventos:` en la fuente, los renames quedan no-ops (el `layer_key` ya viene correcto).
- Para renames adicionales en el futuro (otros workspaces mal nombrados desde el Sheet), agregar al diccionario y volver a correr `make prod-migration`.

---

## [1.12.0] - 2026-04-28

`/ontoy` ahora vive dentro del container `jobs` (un mini HTTP server con `http.server` stdlib, sin deps externas) en lugar de un servicio `version-api` con `nginx:alpine` dedicado. Mismo endpoint, mismo formato JSON, lectura del `version.json` en cada request → hot-update sin restart cuando bumpas `VERSION` y corres `make version-json`.

### Cambiado
- **`/ontoy` integrado en `jobs`** (`jobs/ontoy_server.py`): mini server con `http.server.ThreadingHTTPServer` que lee `/app/version.json` (bind-mount read-only) o fallback `/app/VERSION`. Cero deps Python adicionales (stdlib).
- `jobs/entrypoint.sh`: arranca `ontoy_server.py` en background antes del `exec` de cron.
- `docker-compose.yml`: el servicio `jobs` ahora expone `${VERSION_API_PORT:-8088}:8088`, monta `./VERSION` y `./version-api/html/version.json` read-only, y tiene healthcheck con `urllib.request` (sin nuevas deps).

### Eliminado
- Servicio `version-api` (`nginx:alpine`) — reemplazado por el endpoint embebido en `jobs`.
- `version-api/nginx.conf` — ya no se usa (se conserva `version-api/html/` para el `version.json` generado por `make version-json`).

### Notas
- Ahorro real: −1 container, ~−15 MB RAM. Mismo comportamiento desde el cliente (`curl http://localhost:8088/ontoy`).
- Convivencia con cron: el server HTTP corre en background como child del entrypoint; si `cron -f` (PID 1) muere, docker reinicia el container. Si el server HTTP muere, el healthcheck falla y docker reinicia.

---

## [1.11.0] - 2026-04-27

`icon_url` para temas: identidad visual configurable en cada nodo de tipo `tema` del árbol de capas.

### Agregado
- **Migración alembic 0006** (`jobs/alembic/versions/20260426_0006_layer_icon_url.py`): agrega columna `icon_url TEXT` (nullable) a `mapalab.layers`. Por convención solo aplica a `node_type='tema'`.
- `run_refresh_layer_tree.py` incluye `icon_url` en el `SELECT` y emite `iconUrl` en el JSON cacheado únicamente cuando el nodo es tema (no se propaga a leafs ni groups).

### Cambiado
- `prod-migration.sh` aplica esta migración automáticamente via `alembic upgrade head` (sin pasos manuales en producción).

---

## [1.10.0] - 2026-04-26

Herencia automática del `littleCard` (infobox) desde el group ancestro más cercano, para evitar replicación manual del config en cada hijo. Incluye corrección al bug del head fantasma de alembic que bloqueaba el upgrade tras el bootstrap.

### Agregado
- **Herencia automática de `littleCard` desde el ancestro `group`** (`run_refresh_layer_tree.py`): nueva función `_inherit_little_card` que, al construir el árbol del cache, propaga el `infobox_config` del group ancestro más cercano hacia los descendientes (`leaf` o `group`) que no tienen uno propio. Marca con `inheritedFrom: ancestor_id` para debugging. Permite editar el infobox UNA vez en el group y que todos los hijos lo hereden automáticamente sin replicación. Coordina con mariachi v0.26.0 que ofrece UI de herencia (banner verde "Heredando de X" + botón "Personalizar para esta capa"). Cero cambios necesarios en el visor mapalab.

### Corregido
- **Bug del head fantasma de alembic** (`jobs/bootstrap/v14_schema.sql`): el `INSERT ... ON CONFLICT DO NOTHING` insertaba `0003_metadata_stats` en cada corrida del bootstrap, incluso cuando alembic ya estaba en `0005_map_shares`. Esto creaba dos rows simultáneas en `mapalab.alembic_version_dataengine` y alembic interpretaba dos heads activos, fallando con `"Requested revision 0005_map_shares overlaps with other requested revisions 0003_metadata_stats"` en el siguiente `alembic upgrade head`. Fix: usar `INSERT ... SELECT ... WHERE NOT EXISTS` para que el stamp del baseline solo ocurra cuando la tabla está vacía (BD recién creada). En BDs ya migradas, no toca nada. Para BDs ya afectadas: `DELETE FROM mapalab.alembic_version_dataengine WHERE version_num = '0003_metadata_stats';`
- **Orden en `bootstrap-v14.sh`**: el `alembic upgrade head` se ejecuta ANTES del refresh del `layer_tree_cache` (los modelos SQLAlchemy de `jobs/` esperan columnas que agregan las migraciones nuevas, ej. `mapalab.layers.slug` en 0004; sin esto el `SELECT` fallaba con `"column does not exist"`).

---

## [1.9.0] - 2026-04-24

Persistencia de estado de mapa compartido (`map_shares`) con cleanup automático.

### Agregado
- **Migración alembic 0005** (`jobs/alembic/versions/20260424_0005_map_shares.py`): nueva tabla `mapalab.map_shares` para snapshots persistidos del estado del mapa (layers, order, visibility, opacity, filters, periodicity, loop, basemap, view). Indexada para cleanup sliding-window (`last_accessed_at`) y cleanup pinned (`pinned_until`).
- **Job `run_cleanup_shares.py`** agregado al cron diario de `dataengine-jobs` a las 04:45: borra shares no-pinned con `last_accessed_at` mayor a 30 días y los pinned-expired (`pinned_until < now()`).
- Nueva entrada en `jobs/crontab` para el cleanup diario.

---

## [1.8.0] - 2026-04-24

`slug` público y aliases cortos para capas, base para URLs amigables y referencias estables.

### Agregado
- **Migración alembic 0004** (`jobs/alembic/versions/20260424_0004_layer_slugs_and_aliases.py`):
  - Columna `slug` en `mapalab.layers` (unique, kebab-case, max 60 chars) validada por check constraint.
  - Nueva tabla `mapalab.layer_aliases` para identificadores alternos cortos (ej. `esalud` → `establecimientos-salud`), también validados por check constraint.
- `run_refresh_layer_tree.py` incluye `slug` y `aliases` en el JSON materializado del cache, para que el backend de mapalab los sirva en `/layers/tree`.

### Notas de deploy
Backwards compatible: `slug` es nullable. Mariachi admin lo poblará via su bulk slug generator; los IDs existentes siguen resolviendo hasta el cutover.

---

## [1.7.0] - 2026-04-24

Migraciones de `mapalab` ahora viven en este repo. Antes residían en `mariachi/api/alembic/versions/dataengine/` y aplicarlas en producción requería SSH cross-host (mariachi en S1, dataengine en S4). Con este cambio `make prod-migration` es self-contained.

### Agregado
- **Alembic ownership** (`jobs/alembic/`): `env.py`, `alembic.ini`, `script.py.mako` y los 4 baselines (`0001_init_mapalab_schema`, `0002_layer_tree_cache`, `0003_layer_metadata_stats`) movidos desde `mariachi/api/alembic/versions/dataengine/` hacia este repo.
- `alembic` agregado a `jobs/requirements.txt` y al container `dataengine-jobs`.
- Nuevos targets: `make migrate` (corre `alembic upgrade head` dentro de `dataengine-jobs`) y `make migrate-status` (muestra heads/current).
- `bootstrap-v14.sh` ahora corre `alembic upgrade head` automáticamente al final (idempotente).
- `prod-migration.sh` se vuelve re-ejecutable: default `--skip-etl`; `--with-etl` opt-in para el pull legacy del Google Sheet.

### Referencia
Ver `gateway-hub/docs/ecosystem.md §7.3` (revisado 2026-04-24) para el contexto del split mariachi/dataengine en producción.

---

## [1.6.0] - 2026-04-23

`make prod-migration` consolidado como unico orquestador, con un paso nuevo de GRANTs sobre `mapalab.*` que hace el flujo idempotente de punta a punta y desbloquea a mariachi sin runbooks manuales.

### Agregado
- **Paso 3b en `scripts/bootstrap-v14.sh`: GRANTs sobre `mapalab.*` para `mariachi_layers`**. Despues de aplicar `v14_schema.sql` (que crea las tablas como `POSTGRES_USER`), corre `GRANT SELECT/INSERT/UPDATE/DELETE` sobre todas las tablas y sequences del schema + `ALTER DEFAULT PRIVILEGES` para objetos futuros creados por el mismo rol. Sin esto, `mariachi_layers` queda owner del schema pero sin acceso a las tablas, y el editor de capas en mariachi truena con `permission denied for table layers`. Idempotente.
- **Checklist extendido** al final de `bootstrap-v14.sh`:
  - Nuevo "Paso 3: Conectividad mariachi-api ↔ DataEngine" distinguiendo dev/staging (red docker external) vs produccion (`ALLOWED_HOSTS` + reload de `pg_hba.conf` + `sslmode=require`).
  - Nueva seccion "TROUBLESHOOTING: `permission denied for table layers`" con comando de re-aplicacion rapida (`./scripts/bootstrap-v14.sh --skip-role --skip-seed --skip-migrate`) + las 5 queries SQL exactas como fallback standalone.
- `scripts/prod-migration.sh` + `make prod-migration` — orquesta pull final del Google Sheet (restaurando temporalmente el ETL legacy desde git) + bootstrap v1.4.0 + seed + migrate + stamp alembic en una sola llamada.
- `jobs/bootstrap/layers_export.json` versionado — baseline del tree de capas (250 nodos, 9 temas) recuperado del commit pre-refactor.
- `scripts/drop_mapalab_card_validation.sql` — checklist SQL para validar paridad antes de dropear `public.mapalab_card`.

### Cambiado
- `scripts/bootstrap-v14.sh` — al finalizar hace `alembic stamp dataengine@head` automaticamente si detecta container mariachi, e imprime los pasos siguientes de produccion (ahora 8 pasos, antes 7) + bloque de troubleshooting.
- `jobs/bootstrap/v14_schema.sql` marcado como FROZEN (baseline v1.4.0, no se modifica mas). Cambios futuros via alembic.
- `README.md`: version bump a 1.6.0.

### Eliminado
- Targets make `bootstrap-v14`, `bootstrap-v14-dry`, `migrate-mapalab-card` — consolidados en `make prod-migration`. El script `scripts/bootstrap-v14.sh` sigue existiendo como orquestador interno.
- Archivos huerfanos: `postgres/replica/start-replica.sh`, `postgres/primary/init/02-init-replication.sh`.

### Notas de deploy
Esta version desbloquea el editor de capas en mariachi sin pasos manuales post-bootstrap. Si actualizas un DataEngine **ya provisionado** con una version anterior (donde `mariachi_layers` existe pero no tiene GRANTs sobre las tablas), correr una sola vez para que el editor empiece a funcionar:

```bash
./scripts/bootstrap-v14.sh --skip-role --skip-seed --skip-migrate
```

Eso re-aplica solo el Paso 2 (idempotente), Paso 3 (idempotente) y el nuevo Paso 3b.

### Requiere
Compatible con `mariachi >= 0.13.0` (que configura `DATAENGINE_DATABASE_URL` y `MAPALAB_BACKEND_URL` en sus `.env.*`).

---

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
- **`make migrate-mapalab-card`** — target 1-shot (idempotente) que re-corre `run_migrate_mapalab_card.py --apply` como herramienta de recuperacion si el Sheet se actualizo. **OJO**: usa `ON CONFLICT DO UPDATE` y sobreescribe ediciones hechas desde mariachi
- **Template catalog** en `run_refresh_layer_stats.py`: 8 operaciones validadas (`count`, `count_distinct`, `count_where`, `sum`, `avg`, `min`, `max`, `latest`) reemplazan SQL libre. Identificadores validados con regex (`[A-Za-z0-9_]{1,100}`), valores bindeados como `:param`
- **Targets make**: `refresh-layer-tree`, `refresh-layer-stats`, `refresh-all`, `logs-jobs`, `bootstrap-v14`, `bootstrap-v14-dry`, `migrate-mapalab-card`, `restore-local`
- **Crontab** del container jobs (`/etc/cron.d/jobs`) y entrypoint que exporta `DATAENGINE_*` a `/etc/environment` para que cron vea las vars
- Documentacion reorganizada: `docs/architecture.md` (componentes + diagrama Mermaid + schema), `docs/jobs.md` (cron container + template catalog + envs), `docs/bootstrap-v14.md` (pasos + flags + idempotencia + secuencia de deploy en produccion), `docs/CHANGELOG.md` (este archivo), `docs/context.md` (feature map + TODOs)
- `.gitignore`: patron `jobs/iieg2025-cloud-*.json` (credencial de service account GCP no versionada) y `jobs/bootstrap/_layers_export.json` (scratch del bootstrap)
- `README.md` muestra la version actual (`1.5.0`) en la cabecera

### Cambiado
- `mapalab_card/` → `jobs/` (git mv preservando historia); servicio docker `mapalab-card` → `jobs` (container `dataengine-mapalab-card` → `dataengine-jobs`). Scripts externos que invoquen el servicio o lean sus logs deben actualizarse
- **Envs del container `jobs` renombradas** `MAPALAB_CARD_DB_{USER,PASSWORD,HOST,PORT,NAME,SSLMODE}` → `DATAENGINE_DB_*`. Aplicado en `docker-compose.yml`, `jobs/run_refresh_*.py`, `jobs/bootstrap/*.py` y `jobs/entrypoint.sh` (que ahora filtra solo `DATAENGINE_*` hacia `/etc/environment`). `make restore-local` tambien usa el prefijo nuevo
- `jobs/Dockerfile` instala `cron`, copia `crontab` a `/etc/cron.d/jobs` (mode 0644), crea `/var/log/cron.log`
- `jobs/core/utils/logger.py` escribe a `jobs.log` (antes `mapalab_card.log`)
- README raiz reescrito: eliminadas referencias al servicio `mapalab-card` ya renombrado. Documentacion profunda movida a `docs/`

### Eliminado
- **ETL legacy del Google Sheet**: `jobs/run_bootstrap.py`, `jobs/core/mapalab_card/` (framework de actions + sources), `jobs/alembic/mapalab_card/` (migraciones), `jobs/core/schemas/mapalab_card.py`, `jobs/data/mapalab_card/`. La fuente de verdad es `mapalab.layer_metadata` + `mapalab.layer_stats`, editable desde mariachi (`/administrador/mapalab/layers`)
- **Target `make card`** y su flag `FORCE_LEGACY_ETL`: ya no hay ETL que correr
- **Envs legacy del compose**: `MAPALAB_CARD_GOOGLE_CREDENTIALS_PATH`, `MAPALAB_CARD_GOOGLE_SHEET_URL`, `MAPALAB_CARD_DATA_WORKING_DIR`, `MAPALAB_CARD_DATA_ERROR_DIR`
- **Mount** `${BACKUP_DATA}/mapalab_card` del servicio `jobs` (ya no hay ETL que lo llene)
- `jobs/requirements.txt`: quita `alembic`, `pandas`, `gspread`, `google-auth`
- `jobs/entrypoint.sh`: quita `alembic upgrade head` del legacy

### Seguridad
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
