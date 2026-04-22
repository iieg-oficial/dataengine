# jobs container

Container `dataengine-jobs` (antes `dataengine-mapalab-card`). Corre **todos los jobs periodicos** sobre la base de datos de DataEngine. Ver tambien `jobs/README.md` en el repo.

## Cron diario

Todos en UTC del contenedor (`cron -f`). Logs: `/var/log/cron.log` (tail con `make logs-jobs`).

| Hora | Script | Funcion |
|---|---|---|
| 03:00 | `run_refresh_periodicity.py` | Invoca `SELECT public.refresh_layer_periodicity()` y cuenta filas de `public.layer_periodicity` |
| 04:00 | `run_refresh_layer_tree.py` | Reconstruye JSON del arbol, calcula ETag y upsertea `mapalab.layer_tree_cache` (singleton id=1) |
| 04:30 | `run_refresh_layer_stats.py` | Evalua `stats_config` de cada `mapalab.layer_stats` via template catalog, guarda `values` + `values_refreshed_at` |

## Trigger manual

Desde la raiz del repo (`/IIEG/mapalab-dataengine`):

```
make refresh-periodicity
make refresh-layer-tree
make refresh-layer-stats
make refresh-all           # los tres en orden
make logs-jobs             # tail del log del cron
make migrate-mapalab-card  # re-sync 1-shot public.mapalab_card -> mapalab.layer_metadata+stats
```

Desde `/IIEG/mapalab/`: `make refresh-layer-tree` delega a este container si esta corriendo (fallback HTTP a `POST /layers/refresh-cache` del backend mapalab).

## Variables de entorno

Heredadas del `docker-compose.yml` raiz:

- `DATAENGINE_DB_USER`, `DATAENGINE_DB_PASSWORD`, `DATAENGINE_DB_HOST`, `DATAENGINE_DB_PORT`, `DATAENGINE_DB_NAME`, `DATAENGINE_DB_SSLMODE`
- `DATAENGINE_URL` (alternativa: URL completa; tiene prioridad si esta seteada)
- `MAPALAB_STATS_DB_USER` / `MAPALAB_STATS_DB_PASSWORD` (opcional; override de credenciales solo para el refresh de stats)

## Template catalog de `stats_config`

`run_refresh_layer_stats.py` **no ejecuta SQL libre**. Cada config de `mapalab.layer_stats.stats_config` se resuelve contra un catalogo de 8 operaciones: `count`, `count_distinct`, `count_where`, `sum`, `avg`, `min`, `max`, `latest`.

- `schema`, `table`, `field`, `where_field`, `order_field` se validan como identificadores (`[A-Za-z0-9_]{1,100}`) antes de interpolarse citados en la query. Valores rechazados se marcan como `skip` y se contabilizan en `failed`.
- `where_value` se pasa como parametro bindeado (`:where_value`).
- Config invalido no aborta el job: se contabiliza en `failed`/`skipped` y los demas layers siguen.

Resultado por config: `{ posicion, nombre, simbolo, valor }`, persistido como array JSONB en `values`.

## Estructura del container

```
jobs/
├── Dockerfile                  # python:3.13-slim + cron
├── entrypoint.sh               # exporta DATAENGINE_* a /etc/environment + tail log + cron -f
├── crontab                     # 3 schedules instalados en /etc/cron.d/jobs
├── requirements.txt            # sqlalchemy, psycopg2, rich, python-dotenv
├── run_refresh_periodicity.py
├── run_refresh_layer_tree.py
├── run_refresh_layer_stats.py
├── bootstrap/                  # scripts one-shot del bootstrap v1.4.0 (ver docs/bootstrap-v14.md)
│   ├── v14_schema.sql
│   ├── run_seed_layers.py
│   └── run_migrate_mapalab_card.py
└── core/                       # utilidades compartidas (logger, etc.)
```

Cron corre en foreground (`cron -f`). El entrypoint exporta las envs `DATAENGINE_*` del container a `/etc/environment` para que los jobs las vean via cron, y hace `tail -F` del log para que `docker logs` vea las lineas de los jobs.
