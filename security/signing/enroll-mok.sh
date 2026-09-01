#!/usr/bin/env bash
set -euo pipefail

CERT="${1:-/root/datya-signing/datya-mok.der}"

if [[ "$(id -u)" -ne 0 ]]; then echo "Run as root: sudo $0 /path/to/datya-mok.der" >&2; exit 1; fi
if [[ ! -f "$CERT" ]]; then echo "DER certificate not found: $CERT" >&2; exit 1; fi
if ! command -v mokutil >/dev/null; then echo "mokutil is required" >&2; exit 1; fi

openssl x509 -inform DER -in "$CERT" -noout -subject -fingerprint -sha256
printf '%s\n' 'The certificate above will be staged for enrollment on the next reboot.'
printf '%s\n' 'Only continue on hardware and an operating system you administer.'
mokutil --import "$CERT"
printf '%s\n' 'Enrollment is pending. Reboot and approve it in the firmware MOK Manager screen.'
printf '%s\n' 'After reboot verify with: mokutil --sb-state && mokutil --list-enrolled'
