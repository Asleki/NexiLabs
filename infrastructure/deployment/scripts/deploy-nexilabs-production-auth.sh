#!/usr/bin/env bash
set -euo pipefail

[[ ${EUID:-$(id -u)} -eq 0 ]] || { echo "run as root" >&2; exit 2; }
REPO_ROOT=${1:?repository root required}
RELEASE_ID=${2:?release id required}
EXPECTED_HEAD=7f312b1f9f86031e07664f6a126d88cabab2b11b
BASE=/opt/nexa/nexilabs-production-auth
RELEASE="$BASE/releases/$RELEASE_ID"

[[ -d "$REPO_ROOT/.git" ]] || { echo "not an NPP Git worktree" >&2; exit 2; }
[[ "$(git -C "$REPO_ROOT" rev-parse HEAD)" == "$EXPECTED_HEAD" ]] || {
  echo "repository HEAD does not match P006.UI.10.4 source lock" >&2
  exit 2
}
[[ "$RELEASE_ID" =~ ^[A-Za-z0-9._-]{1,96}$ ]] || { echo "invalid release id" >&2; exit 2; }
[[ -f "$REPO_ROOT/backend/auth/production_auth_transport/server.py" ]] || { echo "P006.UI.10.4 transport missing" >&2; exit 2; }
[[ -f /etc/nexa/nexilabs-production-auth.env ]] || { echo "private Production-auth environment missing" >&2; exit 3; }
[[ -x "$BASE/shared/venv/bin/python" ]] || { echo "Production-auth virtualenv missing; run installer first" >&2; exit 3; }

if grep -Eq '__SET_ON_SERVER_ONLY__|^[[:space:]]*PGPASSWORD=[[:space:]]*$' /etc/nexa/nexilabs-production-auth.env; then
  echo "Production-auth environment still contains placeholders" >&2
  exit 4
fi

rm -rf "$RELEASE"
install -d -o root -g nexa-auth -m 0750 "$RELEASE"
# Copy only the public backend package required by the service. The ignored
# development/auth/private boundary is outside this copy by construction.
cp -a "$REPO_ROOT/backend" "$RELEASE/backend"
find "$RELEASE" -type f -name '*.py' -exec chmod 0644 {} +
find "$RELEASE" -type d -exec chmod 0755 {} +

"$BASE/shared/venv/bin/python" -m compileall -q "$RELEASE/backend"
CURRENT_TARGET=$(readlink -f "$BASE/current" || true)
[[ -n "$CURRENT_TARGET" ]] && ln -sfn "$CURRENT_TARGET" "$BASE/previous"
ln -sfn "$RELEASE" "$BASE/current"

systemctl enable nexa-nexilabs-production-auth >/dev/null
systemctl restart nexa-nexilabs-production-auth
sleep 2
if ! curl --fail --silent --show-error http://127.0.0.1:8767/health | grep -q '"bootstrapHttpExposed":false'; then
  if [[ -L "$BASE/previous" ]]; then
    ln -sfn "$(readlink -f "$BASE/previous")" "$BASE/current"
    systemctl restart nexa-nexilabs-production-auth
  fi
  echo "Production-auth health qualification failed; previous release restored when available" >&2
  exit 5
fi

echo "deployed Production-auth release: $RELEASE_ID"
