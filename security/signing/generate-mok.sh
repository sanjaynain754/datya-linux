#!/usr/bin/env bash
set -euo pipefail
umask 077

# Generate an owner-controlled certificate for Linux kernel module signing.
# Keep the private key offline or in a hardware-backed signing service.
OUT_DIR="${1:-/root/datya-signing}"
COMMON_NAME="${2:-Datya Linux Module Signing}"
DAYS="${DAYS:-3650}"
KEY_BITS="${KEY_BITS:-3072}"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run as root so the output directory can be protected: sudo $0 [output-dir] [common-name]" >&2
  exit 1
fi
if [[ -e "$OUT_DIR" ]]; then
  echo "Refusing to overwrite existing directory: $OUT_DIR" >&2
  exit 1
fi
if ! command -v openssl >/dev/null; then
  echo "openssl is required" >&2
  exit 1
fi

install -d -m 0700 "$OUT_DIR"
openssl req -new -x509 -newkey "rsa:${KEY_BITS}" \
  -keyout "$OUT_DIR/datya-mok.priv" \
  -outform DER -out "$OUT_DIR/datya-mok.der" \
  -nodes -days "$DAYS" \
  -subj "/CN=${COMMON_NAME}/" \
  -addext "basicConstraints=critical,CA:FALSE" \
  -addext "keyUsage=critical,digitalSignature" \
  -addext "extendedKeyUsage=codeSigning"

chmod 0600 "$OUT_DIR/datya-mok.priv"
chmod 0644 "$OUT_DIR/datya-mok.der"
openssl x509 -inform DER -in "$OUT_DIR/datya-mok.der" -out "$OUT_DIR/datya-mok.pem"
chmod 0644 "$OUT_DIR/datya-mok.pem"
openssl x509 -inform DER -in "$OUT_DIR/datya-mok.der" -noout -subject -fingerprint -sha256
printf '%s\n' "Created signing material in $OUT_DIR"
printf '%s\n' 'Back up datya-mok.priv offline; never commit or copy it into an ISO.'
printf '%s\n' "Enroll only datya-mok.der on machines you administer, then reboot through the firmware/MOK enrollment screen."
