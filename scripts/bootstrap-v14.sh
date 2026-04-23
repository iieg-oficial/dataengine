#!/usr/bin/env bash
# Bootstrap v1.4.0 MapaLab sobre DataEngine.
#
# Ejecuta de forma idempotente los pasos 1-5 del deploy:
#   1. Crear rol `mariachi_layers` (si no existe) + generar password
#   2. Crear schema `mapalab` con owner + grants + search_path
#   3. Aplicar schema (tablas + seed de workspaces)
#   4. Seed de layers desde JSON exportado por frontend
#   5. Migrar public.mapalab_card → mapalab.layer_metadata + layer_stats
#
# Asume que el stack dataengine esta corriendo (postgres-primary + jobs containers).
# Requiere .env con POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB.
#
# Uso:
#   ./scripts/bootstrap-v14.sh --layers-json /path/to/layers_export.json
#   ./scripts/bootstrap-v14.sh --layers-json ... --skip-role --skip-migrate
#   ./scripts/bootstrap-v14.sh --dry-run

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

LAYERS_JSON=""
DRY_RUN=0
SKIP_ROLE=0
SKIP_SCHEMA=0
SKIP_SEED=0
SKIP_MIGRATE=0
PROVIDED_PASSWORD=""

usage() {
    sed -n '2,20p' "$0"
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --layers-json) LAYERS_JSON="$2"; shift 2 ;;
        --password) PROVIDED_PASSWORD="$2"; shift 2 ;;
        --dry-run) DRY_RUN=1; shift ;;
        --skip-role) SKIP_ROLE=1; shift ;;
        --skip-schema) SKIP_SCHEMA=1; shift ;;
        --skip-seed) SKIP_SEED=1; shift ;;
        --skip-migrate) SKIP_MIGRATE=1; shift ;;
        -h|--help) usage ;;
        *) echo "Argumento desconocido: $1" >&2; exit 1 ;;
    esac
done

if [ ! -f "$REPO_ROOT/.env" ]; then
    echo "ERROR: $REPO_ROOT/.env no existe" >&2
    exit 1
fi

set -a
source "$REPO_ROOT/.env"
set +a

: "${POSTGRES_USER:?POSTGRES_USER no esta en .env}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD no esta en .env}"
: "${POSTGRES_DB:?POSTGRES_DB no esta en .env}"

PRIMARY_SERVICE="postgres-primary"
JOBS_SERVICE="jobs"
PRIMARY_CONTAINER="dataengine-primary"
JOBS_CONTAINER="dataengine-jobs"

_exec_primary() {
    docker compose exec -T -e PGPASSWORD="$POSTGRES_PASSWORD" "$PRIMARY_SERVICE" "$@"
}

_exec_jobs() {
    docker compose exec -T "$JOBS_SERVICE" "$@"
}

_check_container_running() {
    local name="$1"
    if ! docker ps --format '{{.Names}}' | grep -q "^${name}$"; then
        echo "ERROR: container $name no esta corriendo. Corre 'make up' primero." >&2
        exit 1
    fi
}

_check_container_running "$PRIMARY_CONTAINER"
_check_container_running "$JOBS_CONTAINER"

echo "=== bootstrap-v14: DataEngine → schema mapalab ==="
echo "  DB:             $POSTGRES_DB"
echo "  dry-run:        $([ $DRY_RUN -eq 1 ] && echo si || echo NO)"
echo "  skip-role:      $SKIP_ROLE"
echo "  skip-schema:    $SKIP_SCHEMA"
echo "  skip-seed:      $SKIP_SEED (requiere --layers-json)"
echo "  skip-migrate:   $SKIP_MIGRATE (migrate public.mapalab_card)"
echo

ML_PASSWORD=""
ROLE_EXISTS=0

if [ $SKIP_ROLE -eq 0 ]; then
    echo "--- Paso 1/5: rol mariachi_layers ---"
    ROLE_EXISTS=$(_exec_primary psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc \
        "SELECT 1 FROM pg_roles WHERE rolname = 'mariachi_layers'" | tr -d '[:space:]' || echo 0)

    if [ "$ROLE_EXISTS" = "1" ]; then
        echo "  Rol mariachi_layers ya existe. Omitiendo creacion."
        if [ -n "$PROVIDED_PASSWORD" ]; then
            ML_PASSWORD="$PROVIDED_PASSWORD"
            if [ $DRY_RUN -eq 0 ]; then
                _exec_primary psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c \
                    "ALTER ROLE mariachi_layers WITH PASSWORD '${ML_PASSWORD}'" >/dev/null
                echo "  Password del rol actualizada."
            fi
        fi
    else
        ML_PASSWORD="${PROVIDED_PASSWORD:-$(python3 -c "import secrets, string; print(''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32)))")}"
        if [ $DRY_RUN -eq 1 ]; then
            echo "  [dry-run] CREATE ROLE mariachi_layers WITH LOGIN PASSWORD '<generado>'"
        else
            _exec_primary psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<SQL
CREATE ROLE mariachi_layers WITH LOGIN PASSWORD '${ML_PASSWORD}';
GRANT CONNECT ON DATABASE ${POSTGRES_DB} TO mariachi_layers;
ALTER ROLE mariachi_layers SET search_path = mapalab, public;
SQL
            echo "  Rol creado."
        fi
    fi
else
    echo "--- Paso 1/5: SKIP rol ---"
fi

if [ $SKIP_SCHEMA -eq 0 ]; then
    echo
    echo "--- Paso 2/5: schema mapalab + ownership ---"
    SCHEMA_EXISTS=$(_exec_primary psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc \
        "SELECT 1 FROM information_schema.schemata WHERE schema_name = 'mapalab'" | tr -d '[:space:]' || echo 0)
    if [ "$SCHEMA_EXISTS" = "1" ]; then
        echo "  Schema mapalab ya existe. Omitiendo CREATE."
    else
        if [ $DRY_RUN -eq 1 ]; then
            echo "  [dry-run] CREATE SCHEMA mapalab AUTHORIZATION mariachi_layers"
        else
            _exec_primary psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<SQL
CREATE SCHEMA mapalab AUTHORIZATION mariachi_layers;
REVOKE CREATE ON SCHEMA public FROM mariachi_layers;
GRANT SELECT ON public.mapalab_card TO mariachi_layers;
SQL
            echo "  Schema creado. CREATE sobre public revocado. SELECT sobre mapalab_card otorgado."
        fi
    fi

    echo
    echo "--- Paso 3/5: aplicar schema (tablas + seed workspaces) ---"
    if [ $DRY_RUN -eq 1 ]; then
        echo "  [dry-run] psql -f v14_schema.sql (via postgres-primary stdin)"
    else
        # El container 'jobs' no tiene psql instalado. Corremos el SQL desde
        # postgres-primary via stdin (el archivo vive en el host).
        _exec_primary psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 \
            < "$REPO_ROOT/jobs/bootstrap/v14_schema.sql" 2>&1 \
            | grep -vE "^(INSERT|COMMIT|BEGIN)" || true
        echo "  Schema aplicado."
    fi
else
    echo "--- Pasos 2-3/5: SKIP schema ---"
fi

if [ $SKIP_SEED -eq 0 ]; then
    echo
    echo "--- Paso 4/5: seed de layers desde JSON ---"
    if [ -z "$LAYERS_JSON" ]; then
        echo "  ERROR: --layers-json es requerido para esta fase (o usa --skip-seed)" >&2
        echo "  El repo trae un baseline: jobs/bootstrap/layers_export.json" >&2
        echo "  Usar: make bootstrap-v14   (toma el baseline por default)" >&2
        echo "        o --layers-json /ruta/custom.json para uno propio" >&2
        exit 1
    fi
    if [ ! -f "$LAYERS_JSON" ]; then
        echo "  ERROR: archivo no encontrado: $LAYERS_JSON" >&2
        exit 1
    fi

    # jobs/ no esta bind-mounted: el codigo vive en la imagen via COPY.
    # Usamos docker cp para meter el JSON al container antes de correr el seed.
    echo "  JSON: $LAYERS_JSON ($(wc -l < "$LAYERS_JSON") lineas)"
    docker cp "$LAYERS_JSON" "$JOBS_CONTAINER:/tmp/_layers_export.json"

    if [ $DRY_RUN -eq 1 ]; then
        _exec_jobs python /app/bootstrap/run_seed_layers.py --input /tmp/_layers_export.json
    else
        _exec_jobs python /app/bootstrap/run_seed_layers.py --input /tmp/_layers_export.json --apply
    fi
    _exec_jobs rm -f /tmp/_layers_export.json
else
    echo "--- Paso 4/5: SKIP seed ---"
fi

if [ $SKIP_MIGRATE -eq 0 ]; then
    echo
    echo "--- Paso 5/5: migrar public.mapalab_card → mapalab.layer_metadata ---"
    if [ $DRY_RUN -eq 1 ]; then
        _exec_jobs python /app/bootstrap/run_migrate_mapalab_card.py
    else
        _exec_jobs python /app/bootstrap/run_migrate_mapalab_card.py --apply
    fi
else
    echo "--- Paso 5/5: SKIP migrate ---"
fi

echo
echo "--- Refresh inicial del cache del tree ---"
if [ $DRY_RUN -eq 0 ]; then
    _exec_jobs python /app/run_refresh_layer_tree.py
fi

echo
echo "--- Post-bootstrap: sellar estado de alembic en mariachi ---"
# Politica (ecosystem §7.3): alembic autoritativo, v14_schema.sql frozen como baseline.
# Stampeamos dataengine@head para que migraciones futuras (0004+) apliquen sin reintentar el baseline.
MARIACHI_CONTAINER=""
for c in mariachi-api mariachi-api-dev; do
    if docker ps --format '{{.Names}}' | grep -q "^${c}$"; then
        MARIACHI_CONTAINER="$c"
        break
    fi
done

if [ -n "$MARIACHI_CONTAINER" ]; then
    if [ $DRY_RUN -eq 1 ]; then
        echo "  [dry-run] docker exec $MARIACHI_CONTAINER alembic -x db=dataengine stamp dataengine@head"
    else
        if docker exec -T "$MARIACHI_CONTAINER" alembic -x db=dataengine stamp dataengine@head >/dev/null 2>&1; then
            echo "  OK: alembic stamped en dataengine@head (container $MARIACHI_CONTAINER)."
        else
            echo "  WARN: alembic stamp fallo. Correr manualmente cuando mariachi este listo:"
            echo "    docker exec $MARIACHI_CONTAINER alembic -x db=dataengine stamp dataengine@head"
        fi
    fi
else
    echo "  Container mariachi no detectado (buscado: mariachi-api, mariachi-api-dev)."
    echo "  Correr manualmente desde mariachi cuando este arriba:"
    echo "    docker compose exec api alembic -x db=dataengine stamp dataengine@head"
fi

echo
echo "=== bootstrap-v14 completado ==="
if [ -n "$ML_PASSWORD" ] && [ "$ROLE_EXISTS" != "1" ]; then
    echo
    echo "⚠️  GUARDA ESTE VALOR EN .env DE MARIACHI:"
    echo "    DATAENGINE_DATABASE_URL=postgresql://mariachi_layers:${ML_PASSWORD}@<dataengine_host>:5432/${POSTGRES_DB}?sslmode=require"
    echo
    echo "    (Solo se muestra una vez. Si lo pierdes: ./scripts/bootstrap-v14.sh --skip-schema --skip-seed --skip-migrate --password <nuevo>)"
fi

echo
echo "========================================================================"
echo " PASOS SIGUIENTES EN PRODUCCION"
echo "========================================================================"
echo
echo " 1. Guardar el DATAENGINE_DATABASE_URL impreso arriba en mariachi:"
echo "      /IIEG/mariachi/.env.production  (archivo no versionado)"
echo
echo " 2. Confirmar tambien en ese .env.production:"
echo "      MAPALAB_BACKEND_URL=http://mapalab-backend:8000"
echo "      COOKIE_DOMAIN=<tu-subdominio>.tu-dominio.com"
echo "      ACERVO_ENDPOINT / ACERVO_ACCESS_KEY / ACERVO_SECRET_KEY"
echo
echo " 3. Restart de mariachi-api para levantar el engine secundario:"
echo "      cd /IIEG/mariachi && docker compose restart api"
echo
echo " 4. Verificar que alembic esta en head (esperado: dataengine@head):"
echo "      docker compose exec api alembic -x db=dataengine current"
echo
echo " 5. Verificar endpoints:"
echo "      curl -sI https://<dominio>/mapalab/api/layers/tree | grep -i etag"
echo "      curl -u admin:<pwd> https://<dominio>/api/administrador/layers | head -c 200"
echo
echo " 6. (Opcional) Si tenias public.mapalab_card en prod, validar paridad con"
echo "    mapalab.layer_metadata antes de hacer DROP:"
echo "      psql ... -f scripts/drop_mapalab_card_validation.sql"
echo
echo " 7. Confirmar que gateway-hub tiene los bloqueos admin activos:"
echo "      curl -X POST https://<dominio>/mapalab/api/layers/refresh-cache"
echo "      (debe responder 403)"
echo
echo "========================================================================"
