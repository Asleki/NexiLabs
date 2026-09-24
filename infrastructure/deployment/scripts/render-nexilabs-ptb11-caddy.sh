#!/usr/bin/env bash
set -euo pipefail

ROOT=${1:-$(pwd)}
ENV_FILE=${2:-/etc/nexa/nexilabs-access.env}
OUTPUT=${3:-/tmp/nexilabs-ptb11.caddy}

[[ -f "$ENV_FILE" ]] || { echo "access environment not found: $ENV_FILE" >&2; exit 2; }

read_value() {
    local key=$1
    awk -F= -v key="$key" '
        $0 ~ "^[[:space:]]*" key "=" {
            sub("^[[:space:]]*" key "=", "", $0)
            print $0
            exit
        }
    ' "$ENV_FILE"
}

MODE=$(read_value NEXILABS_ACCESS_MODE)
HOST=$(read_value NEXILABS_PUBLIC_HOSTNAME)
PWA_UPSTREAM=$(read_value NEXILABS_PWA_UPSTREAM)
INFRASTRUCTURE_API_UPSTREAM=$(read_value NEXILABS_INFRASTRUCTURE_API_UPSTREAM)
PRODUCTION_AUTH_UPSTREAM=$(read_value NEXILABS_PRODUCTION_AUTH_UPSTREAM)

INFRASTRUCTURE_API_UPSTREAM=${INFRASTRUCTURE_API_UPSTREAM:-127.0.0.1:8000}
PRODUCTION_AUTH_UPSTREAM=${PRODUCTION_AUTH_UPSTREAM:-127.0.0.1:8767}

case "$MODE" in
    DEVELOPMENT_PRIVATE)
        TEMPLATE="$ROOT/infrastructure/deployment/config/Caddyfile.nexilabs.development-private.ptb11.template"
        ;;
    PUBLIC)
        TEMPLATE="$ROOT/infrastructure/deployment/config/Caddyfile.nexilabs.public.ptb11.template"
        ;;
    *)
        echo "invalid NEXILABS_ACCESS_MODE; refusing to render PTB.11 access" >&2
        exit 3
        ;;
esac

[[ "$HOST" =~ ^[A-Za-z0-9.-]+$ ]] || {
    echo "invalid NEXILABS_PUBLIC_HOSTNAME" >&2
    exit 4
}

validate_private_upstream() {
    local name=$1
    local value=$2
    [[ "$value" =~ ^(127\.0\.0\.1|localhost|10\.[0-9.]+|172\.(1[6-9]|2[0-9]|3[01])\.[0-9.]+|192\.168\.[0-9.]+):[0-9]{2,5}$ ]] || {
        echo "$name must be loopback or RFC1918 host:port" >&2
        exit 5
    }
}

validate_private_upstream NEXILABS_PWA_UPSTREAM "$PWA_UPSTREAM"
validate_private_upstream NEXILABS_INFRASTRUCTURE_API_UPSTREAM "$INFRASTRUCTURE_API_UPSTREAM"
validate_private_upstream NEXILABS_PRODUCTION_AUTH_UPSTREAM "$PRODUCTION_AUTH_UPSTREAM"
[[ -f "$TEMPLATE" ]] || { echo "template missing: $TEMPLATE" >&2; exit 6; }

mkdir -p "$(dirname "$OUTPUT")"
TMP=$(mktemp)
trap 'rm -f "$TMP"' EXIT

sed \
    -e "s|__NEXILABS_PUBLIC_HOSTNAME__|$HOST|g" \
    -e "s|__NEXILABS_PWA_UPSTREAM__|$PWA_UPSTREAM|g" \
    -e "s|__NEXILABS_INFRASTRUCTURE_API_UPSTREAM__|$INFRASTRUCTURE_API_UPSTREAM|g" \
    -e "s|__NEXILABS_PRODUCTION_AUTH_UPSTREAM__|$PRODUCTION_AUTH_UPSTREAM|g" \
    "$TEMPLATE" > "$TMP"

if grep -q '__NEXILABS_' "$TMP"; then
    echo "unresolved NexiLabs Caddy placeholder" >&2
    exit 7
fi

install -m 0644 "$TMP" "$OUTPUT"
printf 'rendered ptb11 mode=%s host=%s pwa=%s api=%s auth=%s output=%s\n' \
    "$MODE" "$HOST" "$PWA_UPSTREAM" "$INFRASTRUCTURE_API_UPSTREAM" \
    "$PRODUCTION_AUTH_UPSTREAM" "$OUTPUT"
