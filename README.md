# mapalab-dataengine

Stack PostgreSQL para produccion: primary con SSL, pooler, respaldos automaticos con subida al Acervo de Objetos y un container de jobs periodicos sobre el schema `mapalab` (fuente de verdad de MapaLab v1.4.0+).

## Servicios

| Servicio | Puerto | Rol |
|---|---|---|
| `postgres-primary` | `5432` | BD principal (lectura/escritura), PostGIS 3.6 |
| `pgbouncer` | `6432` | Connection pooler |
| `pg-backup` | — | Respaldos automaticos con subida al AO |
| `jobs` | — | Cron diario: periodicidad (03:00), layer tree (04:00), layer stats (04:30) |

Arquitectura completa + diagrama Mermaid + schema `mapalab` en [`docs/architecture.md`](docs/architecture.md).

## Requisitos

- Docker y Docker Compose
- `make`

## Inicio rapido

```bash
cp .env.example .env
# editar con credenciales

make up
```

`make up` genera certificados SSL la primera vez (idempotente) y, en `ENV=production`, instala el cron job de ingesta.

## Bootstrap v1.4.0 MapaLab

La primera vez que se monta el stack para MapaLab v1.4.0+ hay que correr el bootstrap que crea el rol owner, el schema `mapalab`, las tablas, los seeds y migra los datos legacy:

```bash
make bootstrap-v14 LAYERS_JSON=/ruta/a/layers_export.json
```

Pasos, flags e idempotencia en [`docs/bootstrap-v14.md`](docs/bootstrap-v14.md).

## Jobs periodicos

El container `jobs` corre 3 refresh diarios y reemplaza al antiguo `mapalab-card` (que era solo ETL del Google Sheet). Cron, template catalog de stats y credencial GCP del legado en [`docs/jobs.md`](docs/jobs.md).

## Comandos

```bash
make help             # lista completa

# servicios
make up               # certs + up + cron-install (si ENV=production)
make down
make restart
make build            # rebuild sin cache (imagen de backup)
make ps
make clean            # destructivo: elimina volumenes

# logs
make logs             # todos
make logs-primary
make logs-backup
make logs-jobs        # tail del cron del container jobs

# base de datos
make shell            # psql en primary

# respaldos
make backup                      # solo en ENV=production
make restore FILE=mi_dump.dump   # restaura dentro del container primary
make restore-local FILE=...      # restaura contra la DB remota usando vars del .env

# jobs
make card                 # ingesta legacy del Google Sheet (no-op salvo FORCE_LEGACY_ETL=1)
make refresh-periodicity  # refresca public.layer_periodicity
make refresh-layer-tree   # rebuild de mapalab.layer_tree_cache
make refresh-layer-stats  # evalua stats_config de mapalab.layer_stats
make refresh-all          # los 3 refresh en orden
make check-periodicity    # verifica si la periodicidad esta al dia

# bootstrap v1.4.0
make bootstrap-v14 LAYERS_JSON=...
make bootstrap-v14-dry

# cron host (solo para make card)
make cron-install
make cron-remove

# certs
make certs
```

## Restaurar un dump

1. Copiar el archivo en `./restore/`:

   ```bash
   cp /ruta/a/mi_dump.dump restore/
   ```

2. Restaurar:

   ```bash
   make restore FILE=mi_dump.dump
   ```

Formatos: `.dump` (custom de `pg_dump`, recomendado), `.sql`, `.sql.gz`.

Tambien `make restore-local FILE=...` para restaurar contra la BD remota usando `MAPALAB_CARD_DB_*` del `.env`.

## Respaldos

En `ENV=production`, el container `pg-backup` corre `backup/do-backup.sh` diariamente a las 08:00 AM y sube el dump al Acervo de Objetos. Retencion local: 7 dias en `./volumes/backups/`.

`make backup` fuerza un respaldo manual (tambien solo en `ENV=production`). `DEBUG=1 make backup` activa verbose.

## Variables de entorno

Copiar `.env.example` a `.env` y configurar al menos:

| Variable | Descripcion |
|---|---|
| `ENV` | `production` habilita cron host + backups; cualquier otro valor los desactiva |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Credenciales de la BD |
| `ALLOWED_HOSTS` | Lista de IPs (separadas por espacio) autorizadas en `pg_hba.conf` |
| `PG_BIND_ADDRESS` | IP de binding del puerto expuesto (default `0.0.0.0`) |
| `PG_PRIMARY_PORT` | Puerto host del primary (default `5432`) |
| `PGBOUNCER_PORT` | Puerto host del pooler (default `6432`) |
| `PGDATA` | Path dentro del container para datos |
| `POSTGRES_PRIMARY_DATA` | Volumen host para `/var/lib/postgresql/data` |
| `BACKUP_DATA` | Volumen host para dumps y datos del job legado |
| `AO_ENDPOINT` / `AO_BUCKET` / `AO_ACCESS_KEY` / `AO_SECRET_KEY` | Acervo de Objetos |
| `MAPALAB_CARD_GOOGLE_SHEET_URL` | URL del Sheet legado (solo si se usa `FORCE_LEGACY_ETL=1`) |
| `MAPALAB_CARD_GOOGLE_CREDENTIALS_PATH` | Path del service account GCP dentro del container |
| `CRON_SCHEDULE` | Hora del cron host de `make card` en formato `HH:MM` |

La credencial GCP del ETL legado (`iieg2025-cloud-*.json`) no vive en el repo — montarla manualmente en el host y referenciar via env. Detalles en [`docs/jobs.md`](docs/jobs.md#credencial-gcp).

## Control de acceso

PostgreSQL restringe conexiones a nivel `pg_hba.conf`. Solo conecta:

- local del container
- red interna de Docker (`172.16.0.0/12`)
- IPs en `ALLOWED_HOSTS`

Para inspeccionar la configuracion viva:

```bash
docker exec dataengine-primary cat /var/lib/postgresql/data/pg_hba.conf
```

## Conexion externa

```
host:     <ip-servidor>
port:     5432 (primary)  |  6432 (pgbouncer)
user:     ${POSTGRES_USER}
password: ${POSTGRES_PASSWORD}
database: ${POSTGRES_DB}
sslmode:  require
```

## Docs

- [`docs/architecture.md`](docs/architecture.md) — componentes, schema `mapalab`, volumenes
- [`docs/jobs.md`](docs/jobs.md) — cron container, template catalog, legado ETL
- [`docs/bootstrap-v14.md`](docs/bootstrap-v14.md) — bootstrap del schema `mapalab`
- [`docs/CHANGELOG.md`](docs/CHANGELOG.md) — cambios por version
