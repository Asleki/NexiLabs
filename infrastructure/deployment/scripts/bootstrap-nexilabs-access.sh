#!/usr/bin/env bash
set -euo pipefail

if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
    echo "run as root" >&2
    exit 2
fi

command -v oauth2-proxy >/dev/null 2>&1 || {
    echo "oauth2-proxy must be installed at /usr/local/bin/oauth2-proxy before bootstrap" >&2
    exit 3
}
[[ "$(command -v oauth2-proxy)" == "/usr/local/bin/oauth2-proxy" ]] || {
    echo "oauth2-proxy must resolve to /usr/local/bin/oauth2-proxy" >&2
    exit 4
}

id -u nexa-access >/dev/null 2>&1 || \
    useradd --system --home /nonexistent --shell /usr/sbin/nologin nexa-access

install -d -m 0750 -o root -g nexa-access /etc/nexa/nexilabs-access
install -d -m 0755 -o root -g root /usr/share/nexa/nexilabs-access

if [[ ! -e /etc/nexa/nexilabs-access/allowed-emails ]]; then
    install -m 0640 -o root -g nexa-access /dev/null \
        /etc/nexa/nexilabs-access/allowed-emails
fi

install -m 0644 \
    infrastructure/deployment/config/nexilabs-private-sw.js \
    /usr/share/nexa/nexilabs-access/private-sw.js

install -m 0644 \
    infrastructure/deployment/config/nexilabs-oauth2-proxy.service \
    /etc/systemd/system/nexa-nexilabs-oauth2-proxy.service

systemctl daemon-reload

cat <<'EOF'
NexiLabs access bootstrap complete.

Before activation:
  1. create /etc/nexa/nexilabs-access.env from the repository template;
  2. populate /etc/nexa/nexilabs-access/allowed-emails with exact approved emails;
  3. set real Google OAuth client ID, client secret and cookie secret;
  4. keep NEXILABS_ACCESS_MODE=DEVELOPMENT_PRIVATE;
  5. run activate-nexilabs-access-mode.sh only after DNS/TLS/PWA upstream are ready.

No access mode was activated by bootstrap.
EOF
