# Prod Migration v1.4.0 MapaLab

Flujo one-shot para dejar la base lista para MapaLab v1.4.0+: pull final del Google Sheet, creacion del schema `mapalab.*`, seed de capas, migracion de `public.mapalab_card` y stamp de alembic. Todo en una sola llamada.

**Entrypoint**: `make prod-migration`
**Script**: `scripts/prod-migration.sh` (orquesta `scripts/bootstrap-v14.sh` + restauracion temporal del ETL legacy)

## Cuando usarlo

- **Primer deploy a produccion** de v1.4.0+ (upgrade desde una version LTS anterior).
- **Dev/staging desde cero**: `make prod-migration PROD_MIGRATION_FLAGS="--skip-etl"` (sin credenciales Google).
- **Re-seed puntual del tree** con un JSON conocido: `--skip-etl --layers-json /ruta/custom.json`.

**No usar** una vez mariachi empiece a recibir ediciones en prod — los upserts de este flujo sobrescribirian esas ediciones. A partir de ese momento: cambios de DDL via alembic, cambios de data via mariachi UI.

## Prerequisitos

- Stack dataengine corriendo (`make up`): containers `dataengine-primary` y `dataengine-jobs` healthy.
- `.env` con `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`.
- Para el pull del Sheet (cuando **no** se pasa `--skip-etl`):
  - `MAPALAB_CARD_GOOGLE_CREDENTIALS_PATH` en `.env` apuntando al JSON del service account.
  - `MAPALAB_CARD_GOOGLE_SHEET_URL` en `.env`.
- JSON baseline de capas: viene versionado en `jobs/bootstrap/layers_export.json` (no hay que generar nada).

## Uso

```bash
# Prod deploy completo: Sheet + bootstrap
make prod-migration

# Dev/staging sin credenciales Google (salta el ETL)
make prod-migration PROD_MIGRATION_FLAGS="--skip-etl"

# Override del JSON de capas
make prod-migration PROD_MIGRATION_FLAGS="--layers-json /ruta/custom.json"
```

Flags del script:

| Flag | Efecto |
|---|---|
| `--skip-etl` | No restaura ni corre el ETL del Sheet. Sigue directo al bootstrap. |
| `--layers-json <path>` | Override del baseline (default: `jobs/bootstrap/layers_export.json`). |
| `--dry-run` | No aplica cambios; muestra lo que haria. |

## Pasos ejecutados

### A. Pull final del Google Sheet (solo sin `--skip-etl`)

1. Restaura el codigo del ETL legacy desde git commit `1f70a88~1` en `jobs/_legacy_etl/` (gitignored).
2. Copia el ETL dentro del container `jobs` (en `/tmp/legacy_etl/`).
3. Instala las deps legacy on-the-fly (`pandas`, `gspread`, `google-auth`).
4. Corre `run_bootstrap.py` con `FORCE_LEGACY_ETL=1` + env vars `MAPALAB_CARD_DB_*` derivadas de las `DATAENGINE_DB_*` actuales.
5. El ETL hace `DELETE FROM public.mapalab_card` + `INSERT` masivo (con backup automatico antes). **Unico paso destructivo** — sobrescribe `mapalab_card` completo con el ultimo snapshot del Sheet.
6. Limpia `jobs/_legacy_etl/` al terminar (trap en exit).

### B. Bootstrap v1.4.0 (siempre)

Delega a `scripts/bootstrap-v14.sh`:

1. **Rol `mariachi_layers`** — crea con password generado de 32 chars (o con `--password <val>`). Si existe, solo actualiza password cuando se pasa `--password`. Otorga `CONNECT` a la DB y `search_path = mapalab, public`.
2. **Schema `mapalab`** — `CREATE SCHEMA mapalab AUTHORIZATION mariachi_layers`, revoca `CREATE` sobre `public` al rol, otorga `SELECT` sobre `public.mapalab_card`.
3. **Tablas + seed de workspaces** — aplica `jobs/bootstrap/v14_schema.sql` via `psql` dentro del container `jobs`. Crea 6 tablas + indices + FKs + check constraints, inserta 11 workspaces base.
4. **Seed de layers** — `jobs/bootstrap/run_seed_layers.py --apply`: aplana el tree del JSON, infiere `node_type`, detecta prefijos `*` como `disabled=true`, ordena topologicamente, upsertea en `mapalab.layers`. Reemplaza `mapalab.initial_layer_order`.
5. **Migracion de `public.mapalab_card`** — `jobs/bootstrap/run_migrate_mapalab_card.py --apply`: lee filas con `nombre_capa_geoserver` no vacio, deduplica por `layer_key`, upsertea en `mapalab.layer_metadata` y `mapalab.layer_stats` (solo cuando hay numeralia).
6. **Refresh inicial del cache** — `run_refresh_layer_tree.py` pobla `mapalab.layer_tree_cache` sin esperar al cron de 04:00.
7. **Stamp alembic** — detecta container mariachi corriendo y stampea `dataengine@head` para que migraciones futuras (0004+) apliquen limpias (ver [politica de ownership](../../gateway-hub/docs/ecosystem.md) seccion 7.3).

## Idempotencia

El paso B entero es idempotente. El paso A no: correrlo dos veces hace dos pulls del Sheet (el segundo tumba el primero, no hay data lost porque ambos vienen del Sheet).

Si se pierde el password del rol generado:

```bash
# Re-setear sin recrear el resto
./scripts/bootstrap-v14.sh --skip-schema --skip-seed --skip-migrate --password <nuevo>
```

## Salida importante

Al crear el rol `mariachi_layers` por primera vez, el script imprime al final:

```
DATAENGINE_DATABASE_URL=postgresql://mariachi_layers:<password>@<host>:5432/<db>?sslmode=require
```

**Guardarlo en `.env` de mariachi antes de arrancar mariachi**. Solo se muestra una vez.

## Validacion post-ejecucion

```bash
docker compose exec postgres-primary psql -U $POSTGRES_USER -d $POSTGRES_DB -c "
  SELECT
    (SELECT COUNT(*) FROM public.mapalab_card)     AS legacy,
    (SELECT COUNT(*) FROM mapalab.layers)          AS tree,
    (SELECT COUNT(*) FROM mapalab.layer_metadata)  AS metadata,
    (SELECT COUNT(*) FROM mapalab.layer_stats)     AS stats;"
```

Valores esperados despues del primer deploy completo: ~250 layers, ~107 metadata, ~102 stats.

Para una validacion de paridad mas detallada contra `mapalab_card` antes del DROP: `psql -f scripts/drop_mapalab_card_validation.sql`.

## Despliegue en produccion (primera vez)

Orden correcto en la ventana de deploy:

1. **Anuncio al equipo**: el Sheet se congela a partir de T0. Toda edicion posterior es ignorada.
2. **Backup pre-migration**: `make backup` (solo en ENV=production).
3. **Pull del repo dataengine** + `make up` (levanta stack con imagen nueva).
4. **`make prod-migration`** (ETL + bootstrap + seed + migrate + stamp + refresh).
5. **Validacion** (query de arriba + smoke test del tree: `curl -I https://<dominio>/mapalab/api/layers/tree`).
6. **Deploy mapalab backend** v1.7+ (ya lee de `mapalab.*`).
7. **Deploy mariachi** por primera vez — apunta al `DATAENGINE_DATABASE_URL` impreso en el paso 4.

A partir de T0 los editores usan mariachi en vez del Sheet.

## Deprecacion de `public.mapalab_card`

Una vez confirmado el deploy y que los admins editan desde mariachi, `public.mapalab_card` puede dropearse. Validar paridad primero:

```bash
psql -f scripts/drop_mapalab_card_validation.sql
```

Si no reporta faltantes, descomentar el bloque `DROP` del archivo y re-ejecutar. Tras el drop: eliminar `jobs/bootstrap/run_migrate_mapalab_card.py` y la referencia en `scripts/bootstrap-v14.sh`.

## Notas

- El target `make prod-migration` es el **unico** relacionado al bootstrap. Antes habia `bootstrap-v14`, `bootstrap-v14-dry` y `migrate-mapalab-card` — se consolidaron aqui porque la orquestacion completa es una sola operacion.
- El script `scripts/bootstrap-v14.sh` sigue existiendo como orquestador interno (llamado por `prod-migration.sh`). Es re-llamable directamente con sus flags propios si se necesita granularidad (por ejemplo para recuperar password: `--skip-schema --skip-seed --skip-migrate --password <nuevo>`).
