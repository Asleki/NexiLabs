#!/usr/bin/env bash
set -euo pipefail

ROOT=${1:-$(pwd)}
ENV_FILE=${2:-/etc/nexa/nexilabs-access.env}

python -m pytest -q \
    "$ROOT/infrastructure/tests/contract/test_nexilabs_public_access_boundary.py" \
    "$ROOT/infrastructure/tests/contract/test_nexilabs_ptb11_offline_live_authority_boundary.py"

# Historical frontend worker remains a locked predecessor. PTB.11 publishes a
# separate edge-served worker at /sw.js.
node --check "$ROOT/frontend/sw.js"
node --check "$ROOT/infrastructure/deployment/config/nexilabs-ptb11-sw.js"
node --test \
    "$ROOT/frontend/tests/service-worker-contract.test.mjs" \
    "$ROOT/frontend/tests/ptb11-offline-live-authority-boundary.test.mjs"

bash -n "$ROOT/infrastructure/deployment/scripts/render-nexilabs-ptb11-caddy.sh"
bash -n "$ROOT/infrastructure/deployment/scripts/install-nexilabs-ptb11-worker.sh"

if [[ -f "$ENV_FILE" ]]; then
    "$ROOT/infrastructure/deployment/scripts/render-nexilabs-ptb11-caddy.sh" \
        "$ROOT" "$ENV_FILE" /tmp/nexilabs-ptb11-qualified.caddy
    if command -v caddy >/dev/null 2>&1; then
        caddy validate --config /tmp/nexilabs-ptb11-qualified.caddy --adapter caddyfile
    fi
fi

echo "PTB.11 Offline Capability & Live Authority Trust Boundary qualification passed"
