#!/bin/bash
set -euo pipefail

RESTORE_DIR="./restore"
DEBUG="${DEBUG:-0}"
FILE=""

for arg in "$@"; do
    if [ "$arg" = "--debug" ]; then
        DEBUG=1
    elif [ -z "$FILE" ]; then
        FILE="$arg"
    fi
done

format_size() {
    awk -v b="$1" 'BEGIN {
        if (b >= 1073741824)   printf "%.1f GB", b / 1073741824
        else if (b >= 1048576) printf "%.1f MB", b / 1048576
        else if (b >= 1024)    printf "%.1f KB", b / 1024
        else                   printf "%d B",    b
    }'
}

if [ -z "$FILE" ]; then
    if [ ! -d "$RESTORE_DIR" ]; then
        echo "Error: directorio '$RESTORE_DIR' no existe"
        exit 1
    fi

    mapfile -t files < <(ls -1p "$RESTORE_DIR" 2>/dev/null | grep -v '/' | grep -v '^\.' | grep -vE '\.sh$' || true)
    count=${#files[@]}

    if [ "$count" -eq 0 ]; then
        echo "Error: no hay archivos en '$RESTORE_DIR'"
        exit 1
    elif [ "$count" -eq 1 ]; then
        FILE="${files[0]}"
        BYTES=$(stat -c "%s" "$RESTORE_DIR/$FILE" 2>/dev/null || echo 0)
        printf "Archivo detectado: %s (%s)\n" "$FILE" "$(format_size "$BYTES")"
    else
        printf "Archivos disponibles en %s:\n\n" "$RESTORE_DIR"
        for i in "${!files[@]}"; do
            BYTES=$(stat -c "%s" "$RESTORE_DIR/${files[$i]}" 2>/dev/null || echo 0)
            printf "  [%d] %-45s %s\n" "$((i + 1))" "${files[$i]}" "$(format_size "$BYTES")"
        done
        echo ""
        printf "Seleccionar [1-%d]: " "$count"
        read -r choice

        if ! [[ "$choice" =~ ^[0-9]+$ ]] || [ "$choice" -lt 1 ] || [ "$choice" -gt "$count" ]; then
            echo "Seleccion invalida"
            exit 1
        fi
        FILE="${files[$((choice - 1))]}"
        echo "Seleccionado: $FILE"
    fi
fi

if [ "$(basename -- "$FILE")" != "$FILE" ]; then
    echo "Error: FILE debe ser un nombre de archivo sin rutas"
    exit 1
fi

if [ ! -f "$RESTORE_DIR/$FILE" ]; then
    echo "Error: archivo no encontrado: $RESTORE_DIR/$FILE"
    exit 1
fi

LOGFILE=$(mktemp)
DOCKER_PID=""
cleanup() { rm -f "$LOGFILE"; [ -n "$DOCKER_PID" ] && kill "$DOCKER_PID" 2>/dev/null || true; }
trap cleanup EXIT

START=$(date +%s)
FRAMES=('⣾' '⣽' '⣻' '⢿' '⡿' '⣟' '⣯' '⣷')
SP_LEN=${#FRAMES[@]}
i=0
LAST_LINE=0

printf "\n  Restaurando: %s\n\n" "$FILE"

docker compose exec -T -e DEBUG=$DEBUG postgres-primary /restore/restore.sh "$FILE" > "$LOGFILE" 2>&1 &
DOCKER_PID=$!

flush_log() {
    local current
    current=$(wc -l < "$LOGFILE")
    if [ "$current" -gt "$LAST_LINE" ]; then
        printf "\r\033[K"
        tail -n +"$((LAST_LINE + 1))" "$LOGFILE" | while IFS= read -r line; do
            printf "  %s\n" "$line"
        done
        LAST_LINE=$current
    fi
}

while kill -0 "$DOCKER_PID" 2>/dev/null; do
    ELAPSED=$(( $(date +%s) - START ))
    FRAME="${FRAMES[$((i % SP_LEN))]}"
    flush_log
    printf "\r\033[K  %s  %02d:%02d" "$FRAME" "$((ELAPSED / 60))" "$((ELAPSED % 60))"
    sleep 0.15
    i=$((i + 1))
done

STATUS=0
wait "$DOCKER_PID" || STATUS=$?
ELAPSED=$(( $(date +%s) - START ))
printf "\r\033[K"
flush_log
echo ""

if [ "$STATUS" -eq 0 ]; then
    printf "  Completado en %dm %ds\n\n" "$((ELAPSED / 60))" "$((ELAPSED % 60))"
else
    printf "  Error en la restauracion (codigo: %d)\n\n" "$STATUS" >&2
    exit "$STATUS"
fi
