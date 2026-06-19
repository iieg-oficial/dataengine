#!/bin/bash

DEBUG="${DEBUG:-0}"

for arg in "$@"; do
    if [ "$arg" = "--debug" ]; then
        DEBUG=1
    fi
done

LOGFILE=$(mktemp)
DOCKER_PID=""
FINISHED=0
cleanup() {
    rm -f "$LOGFILE"
    if [ "$FINISHED" -eq 0 ] && [ -n "$DOCKER_PID" ]; then
        kill "$DOCKER_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT

START=$(date +%s)
FRAMES=('⣾' '⣽' '⣻' '⢿' '⡿' '⣟' '⣯' '⣷')
SP_LEN=${#FRAMES[@]}
i=0
LAST_LINE=0

printf "\n  Generando backup...\n\n"

docker compose exec -T -e DEBUG=$DEBUG -e BACKUP_UID=$(id -u) -e BACKUP_GID=$(id -g) pg-backup /scripts/backup.sh > "$LOGFILE" 2>&1 &
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
FINISHED=1
ELAPSED=$(( $(date +%s) - START ))
printf "\r\033[K"
flush_log
echo ""

if [ "$STATUS" -eq 0 ]; then
    printf "  Completado en %dm %ds\n\n" "$((ELAPSED / 60))" "$((ELAPSED % 60))"
else
    printf "  Error en el backup (codigo: %d)\n\n" "$STATUS" >&2
    exit "$STATUS"
fi
