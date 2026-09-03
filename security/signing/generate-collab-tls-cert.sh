#!/usr/bin/env bash
set -euo pipefail
umask 077

# Generate a self-signed certificate for local/testing WSS only.
# Do not use this certificate for production or public deployments.

OUT_DIR="${1:-/root/datya-tls}"
COMMON_NAME="${2:-localhost}"

[[ "$(id -u)" -eq 0 ]] || { echo "Run as root: sudo $0 [output-dir] [common-name]" >&2; exit 1; }
command -v openssl >/dev/null 2>&1 || { echo "openssl is required" >&2; exit 1; }
[[ ! -e "$OUT_DIR" ]] || { echo "Refusing to overwrite existing directory: $OUT_DIR" >&2; exit 1; }

install -d -m 0700 "$OUT_DIR"
openssl req -x509 -newkey rsa:3072 -sha256 -nodes -days 30 \
  -keyout "$OUT_DIR/server.key" \
  -out "$OUT_DIR/server.crt" \
  -subj "/CN=${COMMON_NAME}/" \
  -addext "basicConstraints=critical,CA:FALSE" \
  -addext "keyUsage=critical,digitalSignature,keyEncipherment" \
  -addext "extendedKeyUsage=serverAuth" \
  -addext "subjectAltName=DNS:${COMMON_NAME},IP:127.0.0.1"

chmod 0600 "$OUT_DIR/server.key"
chmod 0644 "$OUT_DIR/server.crt"
openssl x509 -in "$OUT_DIR/server.crt" -noout -subject -dates -fingerprint -sha256
printf '%s\n' "Created local test TLS certificate in $OUT_DIR"
printf '%s\n' 'This certificate is self-signed and must not be used for production/public clients.'
