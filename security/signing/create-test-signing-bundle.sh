#!/usr/bin/env bash
set -euo pipefail
umask 077

# Create disposable test signing material and sign a Guardian module for one exact kernel.
# This script never enrolls a key, changes firmware settings, or disables Secure Boot.
# Run on a test machine only; keep production keys and release ceremonies separate.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
KEY_DIR="${DATYA_TEST_SIGNING_DIR:-$ROOT_DIR/.test-signing}"
KERNEL_RELEASE="${DATYA_KERNEL_RELEASE:-$(uname -r)}"
MODULE_PATH="${DATYA_MODULE_PATH:-$ROOT_DIR/kernel/datya_guardian.ko}"
COMMON_NAME="${DATYA_TEST_KEY_NAME:-Datya Linux v0.1.1 Secure Boot Test Key}"
GENERATE_ONLY=0
BUILD_MODULE=0

fail() { echo "ERROR: $*" >&2; exit 1; }
need() { command -v "$1" >/dev/null 2>&1 || fail "required command missing: $1"; }
usage() {
  cat <<EOF
Usage: sudo $0 [options]

Options:
  --key-dir DIR       Disposable key directory (default: .test-signing)
  --kernel RELEASE    Exact target kernel release (default: uname -r)
  --module PATH       Existing .ko to sign
  --build-module      Build kernel/datya_guardian.ko before signing
  --generate-only     Generate and verify test key material only
  -h, --help          Show this help

The script never enrolls a certificate in MOK, changes firmware, or disables Secure Boot.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --key-dir) [[ $# -ge 2 ]] || fail "--key-dir requires a value"; KEY_DIR="$2"; shift 2 ;;
    --kernel) [[ $# -ge 2 ]] || fail "--kernel requires a value"; KERNEL_RELEASE="$2"; shift 2 ;;
    --module) [[ $# -ge 2 ]] || fail "--module requires a value"; MODULE_PATH="$2"; shift 2 ;;
    --build-module) BUILD_MODULE=1; shift ;;
    --generate-only) GENERATE_ONLY=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) fail "unknown option: $1" ;;
  esac
done

[[ "$(id -u)" -eq 0 ]] || fail "run as root: sudo $0 ..."
need openssl
need sha256sum
need make
need modinfo
SIGN_FILE="/usr/src/linux-headers-${KERNEL_RELEASE}/scripts/sign-file"
[[ -x "$SIGN_FILE" ]] || SIGN_FILE="/usr/lib/linux-kbuild-${KERNEL_RELEASE}/scripts/sign-file"
[[ -x "$SIGN_FILE" ]] || fail "sign-file not found for kernel $KERNEL_RELEASE; install matching linux headers"

if [[ -e "$KEY_DIR" ]]; then
  [[ -f "$KEY_DIR/datya-mok.priv" && -f "$KEY_DIR/datya-mok.der" ]] || fail "key directory exists but is incomplete: $KEY_DIR"
else
  "$ROOT_DIR/security/signing/generate-mok.sh" "$KEY_DIR" "$COMMON_NAME"
fi
chmod 0700 "$KEY_DIR"
chmod 0600 "$KEY_DIR/datya-mok.priv"
chmod 0644 "$KEY_DIR/datya-mok.der"

FINGERPRINT="$(openssl x509 -inform DER -in "$KEY_DIR/datya-mok.der" -noout -fingerprint -sha256 | cut -d= -f2)"
CERT_HASH="$(sha256sum "$KEY_DIR/datya-mok.der" | cut -d' ' -f1)"
echo "Test certificate SHA-256 fingerprint: $FINGERPRINT"
echo "Test certificate file hash: $CERT_HASH"

if [[ "$GENERATE_ONLY" == 1 ]]; then
  echo "Test signing key generated and verified in $KEY_DIR"
  echo "Enrollment is intentionally not performed. Review the fingerprint before any manual test enrollment."
  exit 0
fi

if [[ "$BUILD_MODULE" == 1 ]]; then
  [[ -f "$ROOT_DIR/kernel/Makefile" ]] || fail "Datya Guardian kernel Makefile missing"
  make -C "$ROOT_DIR/kernel" KDIR="/lib/modules/${KERNEL_RELEASE}/build"
  MODULE_PATH="$ROOT_DIR/kernel/datya_guardian.ko"
fi
[[ -f "$MODULE_PATH" ]] || fail "module not found: $MODULE_PATH"
[[ "$MODULE_PATH" == *.ko ]] || fail "module must have a .ko extension"

BACKUP="${MODULE_PATH}.unsigned-backup"
[[ -e "$BACKUP" ]] && fail "refusing to overwrite existing backup: $BACKUP"
cp --preserve=mode,ownership,timestamps "$MODULE_PATH" "$BACKUP"
"$SIGN_FILE" sha256 "$KEY_DIR/datya-mok.priv" "$KEY_DIR/datya-mok.der" "$MODULE_PATH"

modinfo "$MODULE_PATH" | grep -E '^(signer|sig_key|sig_hashalgo):' || fail "signed module metadata is missing"
EVIDENCE="${MODULE_PATH}.signing-evidence"
{
  printf 'kernel_release=%s\n' "$KERNEL_RELEASE"
  printf 'module=%s\n' "$MODULE_PATH"
  printf 'module_sha256=%s\n' "$(sha256sum "$MODULE_PATH" | cut -d' ' -f1)"
  printf 'certificate_sha256=%s\n' "$CERT_HASH"
  printf 'certificate_fingerprint_sha256=%s\n' "$FINGERPRINT"
  printf 'sign_file=%s\n' "$SIGN_FILE"
  printf 'signed_at_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} > "$EVIDENCE"
chmod 0600 "$EVIDENCE"

echo "Signed module: $MODULE_PATH"
echo "Unsigned backup: $BACKUP"
echo "Evidence: $EVIDENCE"
echo "No MOK enrollment was performed. Verify the fingerprint before manually enrolling this disposable test certificate on test hardware."
