# dataengine-jobs

Container que corre **todos los jobs periodicos** sobre la base de datos de DataEngine.

Antes era `dataengine-mapalab-card` (solo ETL del Google Sheet). Desde v1.4.0 de MapaLab corre cron con tres jobs mas el ETL legacy.

## Cron diario (TZ del sistema)

| Hora | Script | Funcion |
|---|---|---|
| 03:00 | `run_refresh_periodicity.py` | Invoca `SELECT public.refresh_layer_periodicity()` |
| 04:00 | `run_refresh_layer_tree.py` | Reconstruye JSON del arbol en `mapalab.layer_tree_cache` |
| 04:30 | `run_refresh_layer_stats.py` | Ejecuta queries de `mapalab.layer_stats.stats_config` y guarda resultados |

Cron corre en foreground (`cron -f`). Logs: `/var/log/cron.log`. Ver `make logs-jobs` desde el repo.

## Trigger manual

Desde `/IIEG/mapalab-dataengine/`:
- `make refresh-periodicity`
- `make refresh-layer-tree`
- `make refresh-layer-stats`
- `make refresh-all` (los tres)
- `make logs-jobs` (tail del log del cron)

Desde `/IIEG/mapalab/`:
- `make refresh-layer-tree` delega a este container si esta corriendo; fallback HTTP a `POST /layers/refresh-cache`.

## Legacy: ETL del Google Sheet (deprecated)

El script `run_bootstrap.py` ingestaba `public.mapalab_card` desde un Google Sheet. Desde v1.4.0 de MapaLab la fuente de verdad es `mapalab.layer_metadata` + `mapalab.layer_stats`, editable desde mariachi. El script emite un warning y no hace nada a menos que `FORCE_LEGACY_ETL=1`.

Se conserva para reingesta puntual del Sheet si fuera necesario. Eliminar en futuros release si no se usa.

## Variables de entorno

Heredadas del `docker-compose.yml` del stack:

- `MAPALAB_CARD_DB_USER`, `MAPALAB_CARD_DB_PASSWORD`, `MAPALAB_CARD_DB_HOST`, `MAPALAB_CARD_DB_PORT`, `MAPALAB_CARD_DB_NAME`, `MAPALAB_CARD_DB_SSLMODE` (mantienen el prefijo por compat con el ETL legacy)
- Alternativa: `DATAENGINE_URL` (URL completa)

## Estructura

```
jobs/
├── Dockerfile                # python:3.13-slim + cron
├── entrypoint.sh             # alembic legacy + exporta envs + tail log + cron -f
├── crontab                   # 3 schedules
├── requirements.txt          # sqlalchemy, psycopg2, pandas, gspread (legacy)
├── run_refresh_periodicity.py
├── run_refresh_layer_tree.py
├── run_refresh_layer_stats.py
├── run_bootstrap.py          # LEGACY — ETL Google Sheet
├── core/                     # framework ETL del legacy
└── alembic/mapalab_card/     # migraciones legacy de mapalab_card
```
