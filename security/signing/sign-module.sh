#!/usr/bin/env bash
set -euo pipefail
umask 077

KEY_DIR="${DATYA_SIGNING_DIR:-/root/datya-signing}"
MODULE="${1:-}"
KERNEL_RELEASE="${2:-$(uname -r)}"

if [[ "$(id -u)" -ne 0 ]]; then echo "Run as root: sudo $0 /path/to/module.ko [kernel-release]" >&2; exit 1; fi
if [[ -z "$MODULE" || ! -f "$MODULE" ]]; then echo "Module .ko path is required" >&2; exit 2; fi
if [[ ! -f "$KEY_DIR/datya-mok.priv" || ! -f "$KEY_DIR/datya-mok.der" ]]; then echo "Signing key or certificate missing in $KEY_DIR" >&2; exit 1; fi

SIGN_FILE="/usr/src/linux-headers-${KERNEL_RELEASE}/scripts/sign-file"
if [[ ! -x "$SIGN_FILE" ]]; then SIGN_FILE="/usr/lib/linux-kbuild-${KERNEL_RELEASE}/scripts/sign-file"; fi
if [[ ! -x "$SIGN_FILE" ]]; then echo "sign-file not found for kernel $KERNEL_RELEASE" >&2; exit 1; fi

cp --preserve=mode,ownership,timestamps "$MODULE" "${MODULE}.unsigned-backup"
"$SIGN_FILE" sha256 "$KEY_DIR/datya-mok.priv" "$KEY_DIR/datya-mok.der" "$MODULE"
modinfo "$MODULE" | grep -E '^(signer|sig_key|sig_hashalgo):' || true
printf '%s\n' "Signed $MODULE for kernel $KERNEL_RELEASE"
printf '%s\n' 'Verify with: modinfo <module.ko> and modprobe --dry-run <module-name>'
