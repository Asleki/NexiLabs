#!/usr/bin/env bash
set -euo pipefail

[[ ${EUID:-$(id -u)} -eq 0 ]] || { echo "run as root" >&2; exit 2; }
REPO_ROOT=${1:-$(pwd)}
[[ -d "$REPO_ROOT/.git" ]] || { echo "not an NPP Git worktree: $REPO_ROOT" >&2; exit 2; }
[[ -f "$REPO_ROOT/backend/auth/first_admin_bootstrap/server.py" ]] || { echo "NPP Production-auth predecessor missing" >&2; exit 2; }

getent group nexa-auth >/dev/null || groupadd --system nexa-auth
id -u nexa-auth >/dev/null 2>&1 || useradd --system --gid nexa-auth --home-dir /nonexistent --shell /usr/sbin/nologin nexa-auth

BASE=/opt/nexa/nexilabs-production-auth
install -d -o root -g nexa-auth -m 0750 "$BASE" "$BASE/releases" "$BASE/shared"
[[ -d /etc/nexa ]] || install -d -o root -g root -m 0755 /etc/nexa
install -d -o root -g nexa-auth -m 0750 /etc/nexa/nexilabs-auth-private /etc/nexa/nexilabs-auth-private/enigma

if [[ ! -x "$BASE/shared/venv/bin/python" ]]; then
  python3 -m venv "$BASE/shared/venv"
fi
"$BASE/shared/venv/bin/python" -m pip install --disable-pip-version-check 'psycopg[binary]>=3.2,<4'

install -o root -g root -m 0644   "$REPO_ROOT/infrastructure/deployment/config/nexilabs-production-auth.service"   /etc/systemd/system/nexa-nexilabs-production-auth.service

if [[ ! -e /etc/nexa/nexilabs-production-auth.env ]]; then
  install -o root -g nexa-auth -m 0640     "$REPO_ROOT/infrastructure/deployment/config/nexilabs-production-auth.env.example"     /etc/nexa/nexilabs-production-auth.env
  echo "installed Production-auth environment TEMPLATE; replace placeholders privately before start"
fi

systemctl daemon-reload
echo "Production-auth host foundation installed. Service was not started."
echo "Private Enigma material was not generated, copied, or changed."
