#!/usr/bin/env bash
set -euo pipefail

ROOT=${1:-$(pwd)}
DESTINATION=${2:-/usr/share/nexa/nexilabs-access/ptb11-sw.js}
SOURCE="$ROOT/infrastructure/deployment/config/nexilabs-ptb11-sw.js"
EXPECTED_SHA256="25b5d67499bcd1a9ddef13492788348e8dbedc13c4cdd0d231fb543f46334a4e"

[[ -f "$SOURCE" ]] || { echo "PTB.11 worker source missing: $SOURCE" >&2; exit 2; }
ACTUAL_SHA256=$(sha256sum "$SOURCE" | awk '{print $1}')
[[ "$ACTUAL_SHA256" == "$EXPECTED_SHA256" ]] || {
    echo "PTB.11 worker checksum mismatch" >&2
    exit 3
}

install -D -m 0644 "$SOURCE" "$DESTINATION"
printf 'installed PTB.11 worker sha256=%s destination=%s\n' "$ACTUAL_SHA256" "$DESTINATION"
