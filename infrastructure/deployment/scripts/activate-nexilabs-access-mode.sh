#!/usr/bin/env bash
set -euo pipefail

if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
    echo "run as root" >&2
    exit 2
fi

ROOT=${1:-$(pwd)}
ENV_FILE=${2:-/etc/nexa/nexilabs-access.env}
CADDY_OUTPUT=${3:-/etc/caddy/nexilabs.caddy}

[[ -f "$ENV_FILE" ]] || { echo "access environment not found: $ENV_FILE" >&2; exit 3; }

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

case "$MODE" in
    DEVELOPMENT_PRIVATE)
        ALLOWLIST=$(read_value OAUTH2_PROXY_AUTHENTICATED_EMAILS_FILE)
        [[ "$ALLOWLIST" == "/etc/nexa/nexilabs-access/allowed-emails" ]] || {
            echo "private mode requires the canonical server-side allowlist path" >&2
            exit 4
        }
        [[ -s "$ALLOWLIST" ]] || {
            echo "private mode requires a non-empty allowed-emails file" >&2
            exit 5
        }

        for key in OAUTH2_PROXY_CLIENT_ID OAUTH2_PROXY_CLIENT_SECRET OAUTH2_PROXY_COOKIE_SECRET; do
            value=$(read_value "$key")
            [[ -n "$value" && "$value" != "__SET_ON_SERVER_ONLY__" ]] || {
                echo "private mode requires server-only value for $key" >&2
                exit 6
            }
        done

        "$ROOT/infrastructure/deployment/scripts/render-nexilabs-access-caddy.sh" \
            "$ROOT" "$ENV_FILE" "$CADDY_OUTPUT"

        caddy validate --config "$CADDY_OUTPUT" --adapter caddyfile
        systemctl enable --now nexa-nexilabs-oauth2-proxy
        systemctl reload caddy
        echo "NexiLabs access mode activated: DEVELOPMENT_PRIVATE"
        ;;
    PUBLIC)
        "$ROOT/infrastructure/deployment/scripts/render-nexilabs-access-caddy.sh" \
            "$ROOT" "$ENV_FILE" "$CADDY_OUTPUT"

        caddy validate --config "$CADDY_OUTPUT" --adapter caddyfile
        systemctl disable --now nexa-nexilabs-oauth2-proxy >/dev/null 2>&1 || true
        systemctl reload caddy
        echo "NexiLabs access mode activated: PUBLIC"
        ;;
    *)
        echo "invalid NEXILABS_ACCESS_MODE; refusing activation" >&2
        exit 7
        ;;
esac
