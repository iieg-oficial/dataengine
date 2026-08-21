#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
    echo "uso: $0 <base-url-sextante> [--insecure]" >&2
    echo "ejemplo: $0 https://iieg.gob.mx/sextante" >&2
    exit 2
fi

BASE="${1%/}"
shift || true
CURL_OPTS=(-s -m 60 -A "iieg-wfs-check/1.0")
for arg in "$@"; do
    [ "$arg" = "--insecure" ] && CURL_OPTS+=(-k)
done

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "Capabilities: $BASE/ows"
if ! curl "${CURL_OPTS[@]}" -o "$TMP/caps.xml" \
    "$BASE/ows?service=WFS&version=2.0.0&request=GetCapabilities"; then
    echo "no se pudo leer el GetCapabilities" >&2
    exit 1
fi

grep -oP '(?<=<Name>)[^<]+:[^<]+' "$TMP/caps.xml" | sort -u > "$TMP/capas.txt"
TOTAL=$(wc -l < "$TMP/capas.txt")
if [ "$TOTAL" -eq 0 ]; then
    echo "el GetCapabilities no trajo capas" >&2
    exit 1
fi
echo "capas publicadas: $TOTAL"
echo

OK=0
FAIL=0
while read -r capa; do
    ws="${capa%%:*}"
    url="$BASE/$ws/ows?service=WFS&version=2.0.0&request=GetFeature"
    url="$url&typeNames=$capa&count=1&startIndex=0&outputFormat=application/json"
    code=$(curl "${CURL_OPTS[@]}" -o "$TMP/r.out" -w '%{http_code}' "$url" || echo 000)
    if [ "$code" = "200" ]; then
        OK=$((OK + 1))
        printf '  ok    %s\n' "$capa"
    else
        FAIL=$((FAIL + 1))
        motivo=$(grep -oP '(?<=<ows:ExceptionText>)[^<]+' "$TMP/r.out" | head -1)
        printf '  FALLA %s  [%s] %s\n' "$capa" "$code" "${motivo:-sin detalle}"
        printf '%s\n' "$capa" >> "$TMP/fallan.txt"
    fi
done < "$TMP/capas.txt"

echo
echo "paginan: $OK / $TOTAL    fallan: $FAIL"
if [ "$FAIL" -gt 0 ]; then
    echo
    echo "por workspace:"
    sed 's/:.*//' "$TMP/fallan.txt" | sort | uniq -c | sort -rn | sed 's/^/  /'
    exit 1
fi
