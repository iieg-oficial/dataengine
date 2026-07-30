# dataengine

**Version:** ver [`VERSION`](VERSION) y el [changelog](docs/CHANGELOG.md)

Stack PostgreSQL para produccion: primary con SSL, pooler, respaldos automaticos con subida al Acervo de Objetos y un container de jobs periodicos sobre el schema `mapalab` (fuente de verdad de MapaLab v1.4.0+).

## Servicios

| Servicio | Puerto | Rol |
|---|---|---|
| `postgres-primary` | `5432` | BD principal (lectura/escritura), PostGIS 3.6 |
| `pgbouncer` | `6432` | Connection pooler |
| `pg-backup` | — | Respaldos automaticos con subida al AO |
| `jobs` | — | Cron diario: periodicidad (03:00), layer tree (04:00), layer stats (04:30) |

Arquitectura completa + diagrama Mermaid + schema `mapalab` en [`docs/arquitectura.md`](docs/arquitectura.md).

## Requisitos

- Docker y Docker Compose
- `make`

## Inicio rapido

```bash
cp .env.example .env
# editar con credenciales

make up
```

`make up` genera certificados SSL la primera vez (idempotente) antes de levantar el stack.

## Bootstrap v1.4.0 MapaLab

La primera vez que se monta el stack para MapaLab v1.4.0+ hay que correr el bootstrap que crea el rol owner, el schema `mapalab`, las tablas, los seeds y migra los datos legacy:

```bash
make bootstrap
```

El bootstrap del schema v14 fue una migracion one-shot ya ejecutada; su registro esta en
`historial/2026-04-dataengine-bootstrap-v14.md` del repositorio central de contexto.

## Jobs periodicos

El container `jobs` corre 3 refresh diarios sobre el schema `mapalab`. Cron, template catalog de stats y variables de entorno en [`docs/jobs.md`](docs/jobs.md).

## Comandos

```bash
make help             # lista completa

# servicios
make up               # certs + up
make down
make restart
make deploy           # produccion: git pull + down + build + up
make status           # contenedores + estado de las migraciones alembic
make clean            # destructivo: elimina volumenes

# logs
make logs             # selector de servicio (o todos)

# base de datos
make psql             # psql en primary

# respaldos
make backup           # solo en ENV=production
make restore          # selector de dump en restore/, restaura dentro del container primary

# jobs periodicos sobre mapalab schema
make refresh              # selector: todos o un job concreto
make check-periodicity    # verifica si la periodicidad esta al dia

# ingesta ad-hoc de metadatos desde CSV (dependencias externas)
make ingest-metadata      # pregunta dependencia y fuente, muestra el plan y pide confirmar con "aplicar"

# bootstrap y migracion de produccion
make bootstrap        # rol, schema, grants, seed y alembic upgrade head (idempotente)
```

## Restaurar un dump

1. Copiar el archivo en `./restore/`:

   ```bash
   cp /ruta/a/mi_dump.dump restore/
   ```

2. Restaurar y elegir el archivo en el selector:

   ```bash
   make restore
   ```

Formatos: `.dump` (custom de `pg_dump`, recomendado), `.sql`, `.sql.gz`.

## Respaldos

En `ENV=production`, el container `pg-backup` corre un dump semanal (domingos 02:00 UTC) y sube el archivo al Acervo de Objetos. Retencion local: 30 dias en `./volumes/backups/`.

`make backup` fuerza un respaldo manual (tambien solo en `ENV=production`). `DEBUG=1 make backup` activa verbose.

## Variables de entorno

Copiar `.env.example` a `.env` y configurar al menos:

| Variable | Descripcion |
|---|---|
| `ENV` | `production` habilita los backups; cualquier otro valor los desactiva |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Credenciales de la BD |
| `ALLOWED_HOSTS` | Lista de IPs (separadas por espacio) autorizadas en `pg_hba.conf` |
| `PG_BIND_ADDRESS` | IP de binding del puerto expuesto (default `0.0.0.0`) |
| `PG_PRIMARY_PORT` | Puerto host del primary (default `5432`) |
| `PGBOUNCER_PORT` | Puerto host del pooler (default `6432`) |
| `PGDATA` | Path dentro del container para datos |
| `POSTGRES_PRIMARY_DATA` | Volumen host para `/var/lib/postgresql/data` |
| `BACKUP_DATA` | Volumen host para dumps (`/backups` en `pg-backup`) |
| `AO_ENDPOINT` / `AO_BUCKET` / `AO_ACCESS_KEY` / `AO_SECRET_KEY` | Acervo de Objetos |

El container `jobs` recibe sus credenciales DB via `DATAENGINE_DB_*`, inyectadas desde las `POSTGRES_*` en el `compose.yaml`. Ver [`docs/jobs.md`](docs/jobs.md#variables-de-entorno) para vars opcionales (`DATAENGINE_URL`, `MAPALAB_STATS_DB_*`).

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

- [`docs/arquitectura.md`](docs/arquitectura.md) — componentes, schema `mapalab`, volumenes
- [`docs/jobs.md`](docs/jobs.md) — cron container y template catalog
- [`docs/CHANGELOG.md`](docs/CHANGELOG.md) — cambios por version
- `repos/dataengine/contexto.md` (repositorio central de contexto) — mapa feature → archivos y pendientes
