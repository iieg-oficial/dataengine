REFRESH_DEFAULT='periodicity layer-tree layer-stats'
REFRESH_ALL='periodicity layer-tree layer-stats municipios cleanup-shares dump-layers-csv'

require_production() {
    if [ "${ENV:-}" != 'production' ]; then
        fail "Entorno:ENV=${ENV:-vacio}, este target solo corre en produccion" \
             'Ajusta ENV=production en el .env de la VM.'
    fi
    row 'Entorno' 'production' "$C_GREEN"
}

_migrate_report() {
    local err
    if ! err=$(dc prod exec -T jobs true 2>&1 >/dev/null); then
        printf '  %s! No se pudo acceder al contenedor jobs.%s\n' "$C_YELLOW" "$C_RESET"
        local reason
        reason=$(printf '%s\n' "$err" |
            grep -iE 'invalid spec|is not set|no such|not running|no configuration' | tail -1 || true)
        [ -n "$reason" ] && printf '  %sMotivo: %s%s\n' "$C_DIM" "$reason" "$C_RESET"
        if printf '%s' "$err" | grep -qiE 'invalid spec|is not set'; then
            printf '  %sFalta cargar el .env de este directorio.%s\n' "$C_DIM" "$C_RESET"
        else
            printf "  %sLevantalo con 'make up' o 'make migrate'.%s\n" "$C_DIM" "$C_RESET"
        fi
        return 0
    fi
    dc prod exec -T jobs alembic history --indicate-current 2>/dev/null | awk \
        -v cur="$C_CYAN" -v pen="$C_YELLOW" -v app="$C_DIM" \
        -v grn="$C_GREEN" -v bold="$C_BOLD" -v rst="$C_RESET" '
        { if ($0 ~ /^[[:space:]]*$/) next
          n++; arr[n]=$0; if (index($0,"(current)")>0) curidx=n }
        END {
          if (n==0) { printf "  %s(sin historial de migraciones)%s\n", app, rst; exit }
          if (curidx==0) pend=n; else pend=curidx-1
          if (pend==0) printf "  %s* Al dia%s -- %d migracion(es) aplicada(s), 0 pendientes\n\n", grn, rst, n
          else printf "  %s* %d pendiente(s)%s de %d totales\n\n", pen, pend, rst, n
          for (i=1;i<=n;i++) {
            if (curidx>0 && i==curidx) printf "  %s%s>%s %s%s  (actual)%s\n", cur, bold, rst, cur, arr[i], rst
            else if (curidx==0 || i<curidx) printf "  %so %s  (pendiente)%s\n", pen, arr[i], rst
            else printf "  %s+ %s%s\n", app, arr[i], rst
          }
        }'
}

refresh_script() {
    case "$1" in
        periodicity)     printf 'run_refresh_periodicity.py' ;;
        layer-tree)      printf 'run_refresh_layer_tree.py' ;;
        layer-stats)     printf 'run_refresh_layer_stats.py' ;;
        municipios)      printf 'run_refresh_municipios.py' ;;
        cleanup-shares)  printf 'run_cleanup_shares.py' ;;
        dump-layers-csv) printf 'run_dump_layers_csv.py' ;;
    esac
}

run_refresh() {
    local job=$1 forced=${2:-}
    local -a args=("$(refresh_script "$job")")
    [ "$job" = 'layer-stats' ] && [ -n "$forced" ] && args+=(--force)
    run_step "$job" dc prod exec -T jobs python "${args[@]}"
}

ingest_metadata() {
    local dep source
    printf '  Dependencia: '
    read -r dep </dev/tty || dep=''
    printf '  Fuente (ruta o URL): '
    read -r source </dev/tty || source=''
    if [ -z "$dep" ] || [ -z "$source" ]; then
        fail 'Ingesta:faltan la dependencia o la fuente' \
             'Ambas son obligatorias; la fuente puede ser un CSV local o una URL.'
    fi
    if ! printf '%s' "$source" | grep -qE '^https?://'; then
        docker cp "$source" dataengine-jobs:/tmp/ingest_source.csv
        source=/tmp/ingest_source.csv
    fi
    rule
    printf '\n  %sPlan (dry-run)%s\n\n' "$C_BOLD" "$C_RESET"
    dc prod exec -T jobs python ingest/run_ingest_metadata.py \
        --dependencia "$dep" --source "$source"
    printf '\n'
    confirm 'Revisa el plan de arriba antes de escribir en la base.' 'aplicar'
    dc prod exec -T jobs python ingest/run_ingest_metadata.py \
        --dependencia "$dep" --source "$source" --apply
}
