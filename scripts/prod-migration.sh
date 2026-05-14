#!/usr/bin/env bash
# Migracion idempotente de produccion: bootstrap baseline + alembic upgrade head.
#
# Hace en orden:
#   A. (DEFAULT) Pull del Google Sheet -> public.mapalab_card
#      (ETL legacy restaurado temporalmente desde el tag git legacy-etl-snapshot).
#      Default mientras estamos en testing: PULL. El Sheet sigue siendo fuente de
#      verdad hasta el primer go-live a produccion. Tras ese deploy, congelar el
#      Sheet y volver el default a SKIP_ETL=1.
#   B. Bootstrap v1.4.0+: schema mapalab.*, seed de layers, migracion
#      mapalab_card -> layer_metadata + layer_stats, alembic upgrade head.
#
# Idempotente. Re-ejecutable cada vez que hagas deploy con migraciones nuevas.
# El paso B aplica TODAS las migraciones alembic pendientes (0004+, lo que sea).
#
# Uso:
#   ./scripts/prod-migration.sh                     # pull Sheet + bootstrap + alembic (default mientras estamos en testing)
#   ./scripts/prod-migration.sh --skip-etl          # omite pull del Sheet (post go-live a produccion)
#   ./scripts/prod-migration.sh --dry-run           # no aplica cambios
#   ./scripts/prod-migration.sh --layers-json /path # override del baseline JSON

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

SKIP_ETL=0
DRY_RUN=0
LAYERS_JSON="$REPO_ROOT/jobs/bootstrap/layers_export.json"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --skip-etl) SKIP_ETL=1; shift ;;
        --with-etl) SKIP_ETL=0; shift ;;
        --dry-run)  DRY_RUN=1; shift ;;
        --layers-json) LAYERS_JSON="$2"; shift 2 ;;
        -h|--help)  sed -n '2,25p' "$0"; exit 0 ;;
        *) echo "Argumento desconocido: $1" >&2; exit 1 ;;
    esac
done

LEGACY_COMMIT="legacy-etl-snapshot"
SCRATCH_DIR="$REPO_ROOT/jobs/_legacy_etl"

_cleanup() {
    if [ -d "$SCRATCH_DIR" ]; then
        echo "--- limpiando $SCRATCH_DIR ---"
        rm -rf "$SCRATCH_DIR"
    fi
}
trap _cleanup EXIT

[ -f "$REPO_ROOT/.env" ] || { echo "ERROR: $REPO_ROOT/.env no existe" >&2; exit 1; }
set -a; source "$REPO_ROOT/.env"; set +a

: "${POSTGRES_USER:?POSTGRES_USER no esta en .env}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD no esta en .env}"
: "${POSTGRES_DB:?POSTGRES_DB no esta en .env}"

if [ $SKIP_ETL -eq 0 ]; then
    : "${MAPALAB_CARD_GOOGLE_CREDENTIALS_PATH:?MAPALAB_CARD_GOOGLE_CREDENTIALS_PATH no esta en .env (o usa --skip-etl)}"
    : "${MAPALAB_CARD_GOOGLE_SHEET_URL:?MAPALAB_CARD_GOOGLE_SHEET_URL no esta en .env (o usa --skip-etl)}"

    CRED_BASENAME="$(basename "$MAPALAB_CARD_GOOGLE_CREDENTIALS_PATH")"
    CRED_HOST_PATH="$REPO_ROOT/jobs/$CRED_BASENAME"
    if [ ! -f "$CRED_HOST_PATH" ]; then
        echo "ERROR: credencial no existe en el host: $CRED_HOST_PATH" >&2
        echo "       Coloca tu service account JSON en $REPO_ROOT/jobs/ y reintenta." >&2
        echo "       (Esta en .gitignore como 'jobs/iieg2025-cloud-*.json')" >&2
        exit 1
    fi
fi

echo "================================================================"
echo " PROD MIGRATION v1.4.0"
echo "================================================================"
echo "  DB:             $POSTGRES_DB"
echo "  Dry-run:        $([ $DRY_RUN -eq 1 ] && echo si || echo NO)"
echo "  Skip ETL:       $SKIP_ETL"
echo "  Layers JSON:    $LAYERS_JSON"
echo "================================================================"
echo

if [ $SKIP_ETL -eq 0 ]; then
    echo "=== A. Pull final del Google Sheet -> public.mapalab_card ==="
    echo "  Restaurando ETL legacy desde git ($LEGACY_COMMIT)..."

    rm -rf "$SCRATCH_DIR"
    mkdir -p "$SCRATCH_DIR"
    git archive "$LEGACY_COMMIT" \
        jobs/run_bootstrap.py \
        jobs/core \
        | tar -C "$SCRATCH_DIR" --strip-components=1 -xf -

    sed -i '/Logger.info(f"Len rows:/d; /Logger.info(f"Rows preview:/d' \
        "$SCRATCH_DIR/core/mapalab_card/actions/actbackup.py"

    echo "  ETL restaurado en $SCRATCH_DIR"

    echo "  Copiando ETL y credencial dentro del container dataengine-jobs..."
    docker cp "$SCRATCH_DIR" dataengine-jobs:/tmp/legacy_etl
    CONTAINER_CRED_PATH="/tmp/google-creds.json"
    docker cp "$CRED_HOST_PATH" "dataengine-jobs:$CONTAINER_CRED_PATH"

    if [ $DRY_RUN -eq 1 ]; then
        echo "  [dry-run] saltando ejecucion del ETL"
        ETL_CMD="echo '[dry-run] ETL skipped'"
    else
        ETL_CMD="python run_bootstrap.py"
    fi

    docker compose exec -T \
        -e FORCE_LEGACY_ETL=1 \
        -e MAPALAB_CARD_GOOGLE_CREDENTIALS_PATH="$CONTAINER_CRED_PATH" \
        -e MAPALAB_CARD_GOOGLE_SHEET_URL="$MAPALAB_CARD_GOOGLE_SHEET_URL" \
        jobs bash -c "
            set -e
            export MAPALAB_CARD_DB_USER=\"\${DATAENGINE_DB_USER:-\$POSTGRES_USER}\"
            export MAPALAB_CARD_DB_PASSWORD=\"\${DATAENGINE_DB_PASSWORD:-\$POSTGRES_PASSWORD}\"
            export MAPALAB_CARD_DB_HOST=\"\${DATAENGINE_DB_HOST:-postgres-primary}\"
            export MAPALAB_CARD_DB_PORT=\"\${DATAENGINE_DB_PORT:-5432}\"
            export MAPALAB_CARD_DB_NAME=\"\${DATAENGINE_DB_NAME:-\$POSTGRES_DB}\"
            export MAPALAB_CARD_DB_SSLMODE=\"\${DATAENGINE_DB_SSLMODE:-require}\"
            cd /tmp/legacy_etl
            pip install --no-cache-dir --quiet pandas==3.0.0 gspread==6.2.1 google-auth==2.48.0
            $ETL_CMD
            rm -rf /tmp/legacy_etl $CONTAINER_CRED_PATH
        "

    echo "  ETL completado. public.mapalab_card actualizado con ultimo pull del Sheet."
    echo
else
    echo "=== A. Pull del Sheet: SKIP (--skip-etl) ==="
    echo
fi

echo "=== B. Bootstrap v1.4.0 + seed + migrate + stamp ==="
BOOTSTRAP_ARGS=(--layers-json "$LAYERS_JSON")
[ $DRY_RUN -eq 1 ] && BOOTSTRAP_ARGS+=(--dry-run)

"$SCRIPT_DIR/bootstrap-v14.sh" "${BOOTSTRAP_ARGS[@]}"

echo
echo "================================================================"
echo " VALIDACION POST-MIGRACION"
echo "================================================================"
if [ $DRY_RUN -eq 1 ]; then
    echo " (saltada en --dry-run)"
else
    docker compose exec -T -e PGPASSWORD="$POSTGRES_PASSWORD" postgres-primary \
        psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "
SELECT
  (SELECT COUNT(*) FROM public.mapalab_card)         AS legacy_card,
  (SELECT COUNT(*) FROM mapalab.layers)              AS layers,
  (SELECT COUNT(*) FROM mapalab.layer_metadata)      AS metadata,
  (SELECT COUNT(*) FROM mapalab.layer_stats)         AS stats,
  (SELECT COUNT(*) FROM mapalab.workspaces)          AS workspaces,
  (SELECT COUNT(*) FROM mapalab.initial_layer_order) AS initial_order,
  (SELECT layer_count FROM mapalab.layer_tree_cache WHERE id=1) AS cache,
  (SELECT etag FROM mapalab.layer_tree_cache WHERE id=1)        AS etag;" 2>&1 || true
fi

echo
echo "================================================================"
echo " PROD MIGRATION v1.4.0 COMPLETADA"
echo "================================================================"
echo
echo " Validacion adicional opcional:"
echo "   - Paridad Sheet vs layer_metadata:"
echo "        psql -f scripts/drop_mapalab_card_validation.sql"
echo "   - Smoke test del endpoint:"
echo "        curl -sI https://<dominio>/mapalab/api/layers/tree | grep -i etag"
echo
echo " Post-migracion:"
echo "   - Congelar el Sheet (comunicar al equipo 'no mas ediciones alli')."
echo "   - Deployar mariachi con DATAENGINE_DATABASE_URL apuntando a este cluster."
echo "   - Ver PASOS SIGUIENTES que imprimio bootstrap-v14 arriba."
echo "   - En X dias con confianza: DROP public.mapalab_card + eliminar run_migrate_mapalab_card.py."
echo
echo "================================================================"
