# mapalab-dataengine

Stack PostgreSQL para produccion con replica de lectura, respaldos automaticos y subida al Acervo de Objetos (AO).

## Arquitectura

| Servicio | Descripcion | Puerto |
|----------|-------------|--------|
| `postgres-primary` | Base de datos principal (lectura/escritura) | `5432` |
| `postgres-replica` | Replica de solo lectura (streaming replication) | `5433` |
| `pg-backup` | Respaldos automaticos con cron + subida al AO | - |

## Requisitos

- Docker y Docker Compose
- `make`

## Inicio rapido

```bash
cp .env.example .env
# Editar .env con tus credenciales

make up
```

## Comandos disponibles

```bash
make help             # Ver todos los comandos

# Servicios
make up               # Levantar todo
make down             # Detener todo
make restart          # Reiniciar
make build            # Reconstruir imagen de backup
make ps               # Ver estado

# Logs
make logs             # Todos los servicios
make logs-primary     # Solo primary
make logs-replica     # Solo replica
make logs-backup      # Solo backup

# Base de datos
make shell            # psql conectado al primary
make shell-replica    # psql conectado a la replica

# Respaldos
make backup                          # Respaldo manual
make restore FILE=mi_dump.dump      # Restaurar dump
```

## Restaurar un dump existente

1. Crear la carpeta `restore/` en la raiz del proyecto:
```bash
mkdir -p restore
```

2. Copiar tu archivo dump ahi:
```bash
cp /ruta/a/mi_dump.dump restore/
```

3. Restaurar:
```bash
make restore FILE=mi_dump.dump
```

Formatos soportados:
- `.dump` — custom format de `pg_dump` (recomendado)
- `.sql` — SQL plano
- `.sql.gz` — SQL comprimido con gzip

## Politica de respaldos

Los respaldos se ejecutan automaticamente a las **2:00 AM** todos los dias.

| Tipo | Cuando | Retencion |
|------|--------|-----------|
| Diario | Lunes a sabado | 7 dias |
| Semanal | Domingos | 4 semanas |
| Mensual | Dia 1 de cada mes | 3 meses |

Cada respaldo se sube automaticamente al AO despues de crearse. Los archivos locales se guardan en `./volumes/backups/`.

## Replica de lectura

La replica se sincroniza automaticamente con el primary via streaming replication. Al conectar a `localhost:5433` se accede en modo solo lectura.

Para verificar que la replica funciona:
```bash
# Crear tabla en primary
make shell
CREATE TABLE test (id serial PRIMARY KEY, data text);
INSERT INTO test (data) VALUES ('hello');
\q

# Verificar en replica
make shell-replica
SELECT * FROM test;
\q
```

## Variables de entorno

Copiar `.env.example` a `.env` y configurar:

| Variable | Descripcion |
|----------|-------------|
| `POSTGRES_USER` | Usuario de la BD |
| `POSTGRES_PASSWORD` | Password de la BD |
| `POSTGRES_DB` | Nombre de la BD |
| `REPLICATION_USER` | Usuario para replicacion |
| `REPLICATION_PASSWORD` | Password de replicacion |
| `AO_ENDPOINT` | Endpoint del Acervo de Objetos |
| `AO_BUCKET` | Nombre del bucket |
| `AO_ACCESS_KEY` | Access key del AO |
| `AO_SECRET_KEY` | Secret key del AO |

## Conexion externa

```
# Primary (lectura/escritura)
host: <ip-servidor>
port: 5432
user: (POSTGRES_USER)
password: (POSTGRES_PASSWORD)
database: (POSTGRES_DB)

# Replica (solo lectura)
host: <ip-servidor>
port: 5433
```
