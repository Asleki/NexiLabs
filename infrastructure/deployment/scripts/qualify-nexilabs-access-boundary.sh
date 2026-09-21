#!/usr/bin/env bash
set -euo pipefail

ROOT=${1:-$(pwd)}
ENV_FILE=${2:-/etc/nexa/nexilabs-access.env}

python -m pytest -q \
    "$ROOT/infrastructure/tests/contract/test_nexilabs_public_access_boundary.py"

for script in \
    "$ROOT/infrastructure/deployment/scripts/render-nexilabs-access-caddy.sh" \
    "$ROOT/infrastructure/deployment/scripts/bootstrap-nexilabs-access.sh" \
    "$ROOT/infrastructure/deployment/scripts/activate-nexilabs-access-mode.sh"
do
    bash -n "$script"
done

node --check "$ROOT/infrastructure/deployment/config/nexilabs-private-sw.js"

if [[ -f "$ENV_FILE" ]]; then
    MODE=$(awk -F= '/^[[:space:]]*NEXILABS_ACCESS_MODE=/{sub(/^[^=]*=/,""); print; exit}' "$ENV_FILE")
    case "$MODE" in
        DEVELOPMENT_PRIVATE|PUBLIC) ;;
        *) echo "invalid deployed access mode" >&2; exit 3 ;;
    esac
fi

echo "NEXILABS.PAB.1 qualification passed"
