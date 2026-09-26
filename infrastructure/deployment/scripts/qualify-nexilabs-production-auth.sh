#!/usr/bin/env bash
set -euo pipefail

UNIT=nexa-nexilabs-production-auth
ENV_FILE=/etc/nexa/nexilabs-production-auth.env

systemctl is-active --quiet "$UNIT" || { echo "$UNIT is not active" >&2; exit 2; }
[[ -f "$ENV_FILE" ]] || { echo "Production-auth environment missing" >&2; exit 2; }
if grep -Eq 'NEXILABS_PRODUCTION_AUTH_ALLOWED_ORIGINS=.*\*' "$ENV_FILE"; then
  echo "wildcard Production-auth Origin is forbidden" >&2
  exit 3
fi

LISTENERS=$(ss -ltnH 'sport = :8767' || true)
[[ -n "$LISTENERS" ]] || { echo "no Production-auth listener on 8767" >&2; exit 4; }
if printf '%s
' "$LISTENERS" | grep -Eq '(^|[[:space:]])(0\.0\.0\.0|\[::\]|\*):8767'; then
  echo "Production-auth has a public/wildcard listener" >&2
  exit 5
fi
printf '%s
' "$LISTENERS" | grep -Eq '127\.0\.0\.1:8767|\[::1\]:8767' || { echo "Production-auth listener is not loopback" >&2; exit 5; }

HEALTH=$(curl --fail --silent --show-error http://127.0.0.1:8767/health)
printf '%s
' "$HEALTH" | grep -q '"service":"nexilabs-production-auth"'
printf '%s
' "$HEALTH" | grep -q '"bootstrapHttpExposed":false'

# Canonical Admin namespace must resolve through the successor adapter. An
# unauthenticated request is expected to be rejected as missing session, not 404.
STATUS=$(curl --silent --output /tmp/nexilabs-auth-qualify.json --write-out '%{http_code}'   -H 'Origin: https://nexilabs.nexaecosystem.com'   http://127.0.0.1:8767/auth/admin/eligibility)
[[ "$STATUS" == "401" ]] || { echo "canonical /auth/admin namespace did not reach locked authority (HTTP $STATUS)" >&2; exit 6; }

BAD_STATUS=$(curl --silent --output /tmp/nexilabs-auth-origin-reject.json --write-out '%{http_code}'   -H 'Origin: https://untrusted.invalid'   http://127.0.0.1:8767/health)
[[ "$BAD_STATUS" == "403" ]] || { echo "untrusted Origin was not rejected (HTTP $BAD_STATUS)" >&2; exit 7; }

BOOTSTRAP_STATUS=$(curl --silent --output /tmp/nexilabs-auth-bootstrap.json --write-out '%{http_code}'   http://127.0.0.1:8767/bootstrap-admin)
[[ "$BOOTSTRAP_STATUS" == "404" ]] || { echo "bootstrap HTTP boundary changed unexpectedly" >&2; exit 8; }

echo "P006.UI.10.4 Production-auth runtime qualification: PASS"
