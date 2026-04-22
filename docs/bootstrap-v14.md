# Bootstrap v1.4.0 MapaLab

Orquestador idempotente para dejar la base de datos lista para MapaLab v1.4.0+. Crea el rol owner del schema, la estructura de tablas, las seeds y migra los datos legacy del Google Sheet.

Script: `scripts/bootstrap-v14.sh`. Entrypoint: `make bootstrap-v14`.

## Prerequisitos

- Stack dataengine corriendo (`make up`): containers `dataengine-primary` y `dataengine-jobs` healthy.
- `.env` configurado (`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`).
- JSON de layers exportado desde el frontend de MapaLab:

  ```bash
  cd /IIEG/mapalab/frontend
  node scripts/export_layers_to_json.mjs
  ```

  genera `layers_export.json`.

## Uso

```bash
make bootstrap-v14 LAYERS_JSON=/ruta/a/layers_export.json

# dry-run (no persiste)
make bootstrap-v14-dry

# con flags extra para ./scripts/bootstrap-v14.sh
make bootstrap-v14 LAYERS_JSON=... BOOTSTRAP_FLAGS="--skip-migrate"
```

Flags del script:

| Flag | Efecto |
|---|---|
| `--layers-json <path>` | Requerido (salvo `--skip-seed`) |
| `--dry-run` | No aplica cambios; muestra lo que haria |
| `--skip-role` | No crea el rol `mariachi_layers` |
| `--skip-schema` | No crea schema ni aplica `v14_schema.sql` |
| `--skip-seed` | No corre el seed de `mapalab.layers` |
| `--skip-migrate` | No migra `public.mapalab_card` |
| `--password <val>` | Usa password explicito para `mariachi_layers` (ALTER si ya existe) |

## Pasos ejecutados

1. **Rol `mariachi_layers`** — crea el rol con password generado (`secrets.choice`, 32 chars) o con `--password <val>`. Si ya existe, solo actualiza password cuando se pasa `--password`. Otorga `CONNECT` a la DB y deja `search_path = mapalab, public`.
2. **Schema `mapalab`** — `CREATE SCHEMA mapalab AUTHORIZATION mariachi_layers`, revoca `CREATE` sobre `public` al rol, otorga `SELECT` sobre `public.mapalab_card` (necesario para el paso 5).
3. **Tablas + seed de workspaces** — aplica `jobs/bootstrap/v14_schema.sql` via `psql` dentro del container `jobs`. Crea 6 tablas + indices + FK + check constraints, inserta 11 workspaces base, inserta la marca de version `0003_metadata_stats` en `mapalab.alembic_version_dataengine`.
4. **Seed de layers** — `jobs/bootstrap/run_seed_layers.py --input ... --apply`:
   - Aplana el tree exportado con `flatten_tree` (infiere `node_type` por `depth` + flags: `tema`, `category`, `label`, `group`, `leaf`).
   - Detecta prefijos `*` en labels como `disabled=true` y strippea el caracter.
   - Ordena topologicamente respetando `parent_id`.
   - Upsertea en `mapalab.layers` (ON CONFLICT DO UPDATE — el script es re-ejecutable).
   - Reemplaza `mapalab.initial_layer_order` con lo provisto en el JSON.
5. **Migracion de `public.mapalab_card`** — `jobs/bootstrap/run_migrate_mapalab_card.py --apply`:
   - Lee filas con `nombre_capa_geoserver` no vacio.
   - Deduplica por `layer_key`, arma `fuentes`, `metodologia`, `metadato`, `numeralia` como estructuras JSON.
   - Upsertea en `mapalab.layer_metadata` (siempre) y `mapalab.layer_stats` (solo cuando hay numeralia o `pie_numeralia`).
   - Se puede correr independiente para re-sync puntual.
6. **Refresh inicial del cache** — dispara `run_refresh_layer_tree.py` para poblar `mapalab.layer_tree_cache` inmediatamente (sin esperar al cron de las 04:00).

## Idempotencia

Seguro correr varias veces. El rol, schema, tablas y seeds usan `IF NOT EXISTS` / `ON CONFLICT`. Usar flags `--skip-*` para fases especificas si alguna ya esta aplicada.

Si se pierde el password del rol generado en el paso 1:

```bash
./scripts/bootstrap-v14.sh --skip-schema --skip-seed --skip-migrate --password <nuevo>
```

## Salida importante

Al crear el rol por primera vez, el script imprime al final:

```
DATAENGINE_DATABASE_URL=postgresql://mariachi_layers:<password>@<host>:5432/<db>?sslmode=require
```

**Guardarlo en `.env` de mariachi** — solo se muestra una vez. No se persiste en logs.

## Despliegue en produccion (primera vez)

**Contexto:** en produccion `public.mapalab_card` existe y esta poblada por el ETL del Sheet (historico), pero `mapalab.layer_metadata` y `mapalab.layer_stats` estan vacias. El backend nuevo (mapalab >= v1.7.0) lee exclusivamente de `mapalab.*`. Si haces `pull + up` sin migrar primero, las capas cargan sin metadata ni numeralia.

Secuencia correcta:

1. **Antes del pull del backend** — con el codigo anterior aun corriendo:
   ```bash
   cd /IIEG/mapalab-dataengine
   git pull
   make up
   make bootstrap-v14 LAYERS_JSON=/ruta/a/layers_export.json
   ```
   Esto crea schema + tablas + seed de layers + migra `mapalab_card` → `layer_metadata`/`layer_stats` en una sola corrida idempotente.

2. **Validacion:**
   ```bash
   docker compose exec postgres-primary psql -U $POSTGRES_USER -d $POSTGRES_DB -c "
     SELECT
       (SELECT COUNT(*) FROM mapalab.layers)           AS layers,
       (SELECT COUNT(*) FROM mapalab.layer_metadata)   AS metadata,
       (SELECT COUNT(*) FROM mapalab.layer_stats)      AS stats;"
   ```
   Esperar ~250 layers, ~107 metadata, ~102 stats.

3. **Pull del backend mapalab** (una vez validado el paso 2):
   ```bash
   cd /IIEG/mapalab
   git pull
   make up
   ```

### Re-migracion puntual

Si el Sheet se actualizo y quieres re-sincronizar filas legacy despues del deploy inicial:

```bash
make migrate-mapalab-card
```

**OJO:** esto **sobreescribe** los campos en `mapalab.layer_metadata` con los valores del Sheet (via `ON CONFLICT DO UPDATE`). Si algun admin edito metadata desde mariachi, pierdes esos cambios. La fuente de verdad desde v1.4.2 es mariachi; el re-sync del Sheet solo tiene sentido como herramienta de recuperacion.

### Deprecacion

`public.mapalab_card` y su ETL desde Google Sheet quedan como historico. Una vez validado el deploy inicial y confirmado que los admins editan desde mariachi, la tabla puede dropearse con:

```sql
DROP TABLE IF EXISTS public.mapalab_card;
```

Tras eso, el script `run_migrate_mapalab_card.py` deja de tener fuente y puede eliminarse del repo.
