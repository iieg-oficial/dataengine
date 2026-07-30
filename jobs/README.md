# dataengine-jobs

Container que corre **todos los jobs periodicos** sobre la base de datos de DataEngine.

## Cron diario (TZ del sistema)

| Hora | Script | Funcion |
|---|---|---|
| 03:00 | `run_refresh_periodicity.py` | Invoca `SELECT public.refresh_layer_periodicity()` |
| 04:00 | `run_refresh_layer_tree.py` | Reconstruye JSON del arbol en `mapalab.layer_tree_cache` |
| 04:30 | `run_refresh_layer_stats.py` | Ejecuta queries de `mapalab.layer_stats.stats_config` y guarda resultados |

Cron corre en foreground (`cron -f`). Logs: `/var/log/cron.log`. Ver `make logs-jobs` desde el repo.

## Trigger manual

Desde `/IIEG/dataengine/`:
- `make refresh-periodicity`
- `make refresh-layer-tree`
- `make refresh-layer-stats`
- `make refresh-all` (los tres)
- `make logs-jobs` (tail del log del cron)

Desde `/IIEG/mapalab/`:
- `make refresh-layer-tree` delega a este container si esta corriendo; fallback HTTP a `POST /layers/refresh-cache`.

## Variables de entorno

Heredadas del `compose.yaml` del stack:

- `DATAENGINE_DB_USER`, `DATAENGINE_DB_PASSWORD`, `DATAENGINE_DB_HOST`, `DATAENGINE_DB_PORT`, `DATAENGINE_DB_NAME`, `DATAENGINE_DB_SSLMODE`
- Alternativa: `DATAENGINE_URL` (URL completa)

## Estructura

```
jobs/
├── Dockerfile                # python:3.13-slim + cron
├── entrypoint.sh             # exporta envs + tail log + cron -f
├── crontab                   # 3 schedules
├── requirements.txt          # sqlalchemy, psycopg2, rich
├── run_refresh_periodicity.py
├── run_refresh_layer_tree.py
├── run_refresh_layer_stats.py
├── bootstrap/                # scripts one-shot (seed, schema)
└── core/                     # utilidades compartidas
```
