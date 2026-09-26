#!/usr/bin/env bash
set -euo pipefail

ROOT=${1:-$(pwd)}
DESTINATION=${2:-/usr/share/nexa/nexilabs-access/ptb11-sw.js}
SOURCE="$ROOT/infrastructure/deployment/config/nexilabs-ptb11-sw.js"
EXPECTED_SHA256="03478fc7e9f7f7650dbe56779e8944c7fab029b7b3fdb2a5db4186d009f45e7e"

[[ -f "$SOURCE" ]] || { echo "PTB.11 worker source missing: $SOURCE" >&2; exit 2; }
ACTUAL_SHA256=$(sha256sum "$SOURCE" | awk '{print $1}')
[[ "$ACTUAL_SHA256" == "$EXPECTED_SHA256" ]] || {
    echo "PTB.11 worker checksum mismatch" >&2
    exit 3
}

install -D -m 0644 "$SOURCE" "$DESTINATION"
printf 'installed PTB.11 worker sha256=%s destination=%s\n' "$ACTUAL_SHA256" "$DESTINATION"
