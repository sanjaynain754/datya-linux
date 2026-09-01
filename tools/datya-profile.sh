#!/usr/bin/env bash
set -euo pipefail

# Install an optional Datya profile from the current Debian configuration.
# This intentionally does not add Kali or unrelated distribution repositories.
DRY_RUN=0
if [[ "${1:-}" == "--dry-run" ]]; then DRY_RUN=1; shift; fi
PROFILE="${1:-}"
case "$PROFILE" in
  desktop) PACKAGES=(task-desktop sudo network-manager apparmor) ;;
  security-observe) PACKAGES=(procps psmisc iproute2 iputils-ping dnsutils curl kmod apparmor-utils) ;;
  security-lab) PACKAGES=(podman bubblewrap systemd-container) ;;
  forensics) PACKAGES=(sleuthkit testdisk hashdeep) ;;
  wireless-hardware) PACKAGES=(iw rfkill bluez usbutils) ;;
  cloud-code) PACKAGES=(git python3 cargo rustc cmake build-essential) ;;
  learning) PACKAGES=(python3 python3-venv git) ;;
*) echo "usage: sudo $0 [--dry-run] {desktop|security-observe|security-lab|forensics|wireless-hardware|cloud-code|learning}" >&2; exit 2 ;;
esac

if [[ "$(id -u)" -ne 0 ]]; then echo "run with sudo" >&2; exit 1; fi
command -v apt-get >/dev/null || { echo "apt-get is required" >&2; exit 1; }
if (( DRY_RUN )); then
  printf 'profile=%s\npackages=%s\n' "$PROFILE" "${PACKAGES[*]}"
  printf '%s\n' 'No packages were changed.'
  exit 0
fi
apt-get update
apt-get install --yes "${PACKAGES[@]}"
printf '%s\n' "Profile installed: $PROFILE"
printf '%s\n' 'Review privileges, network behavior, package provenance, and scope before use.'
