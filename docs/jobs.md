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
make refresh-all          # los tres en orden
make logs-jobs            # tail del log del cron
```

Desde `/IIEG/mapalab/`: `make refresh-layer-tree` delega a este container si esta corriendo (fallback HTTP a `POST /layers/refresh-cache` del backend mapalab).

## Variables de entorno

Heredadas del `docker-compose.yml` raiz. Mantienen el prefijo `MAPALAB_CARD_` por compatibilidad con el ETL legacy, pero ya son de uso general del container:

- `MAPALAB_CARD_DB_USER`, `MAPALAB_CARD_DB_PASSWORD`, `MAPALAB_CARD_DB_HOST`, `MAPALAB_CARD_DB_PORT`, `MAPALAB_CARD_DB_NAME`, `MAPALAB_CARD_DB_SSLMODE`
- `DATAENGINE_URL` (alternativa: URL completa; tiene prioridad si esta seteada)
- `MAPALAB_STATS_DB_USER` / `MAPALAB_STATS_DB_PASSWORD` (opcional; override de credenciales solo para el refresh de stats)

Para el ETL legacy:

- `MAPALAB_CARD_DATA_WORKING_DIR`, `MAPALAB_CARD_DATA_ERROR_DIR`
- `MAPALAB_CARD_GOOGLE_CREDENTIALS_PATH` → ruta dentro del container a un JSON de service account GCP. **El archivo no vive en el repo** (ver [Credencial GCP](#credencial-gcp))
- `MAPALAB_CARD_GOOGLE_SHEET_URL`
- `FORCE_LEGACY_ETL=1` → obliga a correr `run_bootstrap.py` pese al deprecation

## Template catalog de `stats_config`

`run_refresh_layer_stats.py` **no ejecuta SQL libre**. Cada config de `mapalab.layer_stats.stats_config` se resuelve contra un catalogo de 8 operaciones: `count`, `count_distinct`, `count_where`, `sum`, `avg`, `min`, `max`, `latest`.

- `schema`, `table`, `field`, `where_field`, `order_field` se validan como identificadores (`[A-Za-z0-9_]{1,100}`) antes de interpolarse citados en la query. Valores rechazados se marcan como `skip` y se contabilizan en `failed`.
- `where_value` se pasa como parametro bindeado (`:where_value`).
- Config invalido no aborta el job: se contabiliza en `failed`/`skipped` y los demas layers siguen.

Resultado por config: `{ posicion, nombre, simbolo, valor }`, persistido como array JSONB en `values`.

## Legado: ETL Google Sheet

`run_bootstrap.py` ingestaba `public.mapalab_card` desde un Google Sheet con credenciales de service account.

Desde v1.4.0 de MapaLab, la fuente de verdad es `mapalab.layer_metadata` + `mapalab.layer_stats` (editable desde mariachi `/administrador/mapalab/layers`). El script emite deprecation warning y termina sin hacer nada salvo `FORCE_LEGACY_ETL=1`.

Se conserva como fallback para reingesta puntual del Sheet. Eliminar en futuros releases si deja de usarse.

## Credencial GCP

Archivo `iieg2025-cloud-<id>.json` (service account) vive en el host, no en el repo. Esta en `.gitignore`.

- Colocarlo en el volumen/working dir del container en la ruta indicada por `MAPALAB_CARD_GOOGLE_CREDENTIALS_PATH` (default `/app/iieg2025-cloud-bc7772dcc9c2.json`).
- Solo lo necesita el ETL legado (`run_bootstrap.py`); los 3 jobs de refresh no lo tocan.

## Estructura del container

```
jobs/
├── Dockerfile                  # python:3.13-slim + cron
├── entrypoint.sh               # alembic legacy (best-effort) + exporta envs + tail log + cron -f
├── crontab                     # 3 schedules instalados en /etc/cron.d/jobs
├── requirements.txt            # sqlalchemy, psycopg2, pandas, gspread (legacy)
├── run_refresh_periodicity.py
├── run_refresh_layer_tree.py
├── run_refresh_layer_stats.py
├── run_bootstrap.py            # LEGACY — deprecated
├── core/                       # framework ETL del legacy (acciones, sources, config)
├── alembic/mapalab_card/       # migraciones legacy
└── bootstrap/                  # scripts de bootstrap v1.4.0 (ver docs/bootstrap-v14.md)
```

Cron corre en foreground (`cron -f`). El entrypoint exporta envs del container a `/etc/environment` para que los jobs las vean via cron, y hace `tail -F` del log para que `docker logs` vea las lineas de los jobs.
