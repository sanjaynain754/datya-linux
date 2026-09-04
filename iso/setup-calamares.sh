#!/usr/bin/env bash
set -euo pipefail

# Prepare a Debian/Ubuntu host for building and testing the Datya Calamares installer.
# This script installs build dependencies but never partitions disks or starts Calamares.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ISO_DIR="$ROOT_DIR/iso"
CHECK_ONLY=0
INSTALL_DEPS=1

usage() {
  cat <<'EOF'
Usage: sudo ./iso/setup-calamares.sh [options]

Options:
  --check-only   Validate scripts and Calamares YAML without installing packages.
  --no-install   Skip apt installation and only perform local checks.
  -h, --help     Show this help.

This setup does not format disks, modify partition tables, or launch Calamares.
EOF
}

for arg in "$@"; do
  case "$arg" in
    --check-only) CHECK_ONLY=1; INSTALL_DEPS=0 ;;
    --no-install) INSTALL_DEPS=0 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "ERROR: unknown option: $arg" >&2; usage >&2; exit 2 ;;
  esac
done

fail() { echo "ERROR: $*" >&2; exit 1; }
need_file() { [[ -f "$1" ]] || fail "missing file: $1"; }

need_file "$ISO_DIR/auto/config"
need_file "$ISO_DIR/build-datya-iso.sh"
need_file "$ISO_DIR/templates/calamares/settings.conf"
need_file "$ISO_DIR/templates/calamares/modules/partition.conf"
need_file "$ISO_DIR/templates/calamares/branding/datya/branding.desc"

if [[ "$INSTALL_DEPS" == 1 ]]; then
  [[ "$(id -u)" -eq 0 ]] || fail "run with sudo to install dependencies"
  command -v apt-get >/dev/null || fail "apt-get is required on Debian/Ubuntu"
  export DEBIAN_FRONTEND=noninteractive
  apt-get update
  apt-get install --yes \
    calamares live-build debootstrap squashfs-tools xorriso \
    grub-pc-bin grub-efi-amd64-bin grub-efi-arm64-bin \
    mtools dosfstools python3-yaml
fi

command -v bash >/dev/null || fail "bash is required"
command -v python3 >/dev/null || fail "python3 is required"

bash -n "$ISO_DIR/auto/config"
bash -n "$ISO_DIR/build-datya-iso.sh"
bash -n "$ISO_DIR/build-release.sh"

python3 - "$ISO_DIR" <<'PY'
import sys
from pathlib import Path
try:
    import yaml
except ImportError:
    raise SystemExit("python3-yaml is required; install it or use the host dependency mode")
root = Path(sys.argv[1]) / "templates/calamares"
for path in root.rglob("*.conf"):
    yaml.safe_load(path.read_text(encoding="utf-8"))
branding = yaml.safe_load((root / "branding/datya/branding.desc").read_text(encoding="utf-8"))
settings = yaml.safe_load((root / "settings.conf").read_text(encoding="utf-8"))
partition = yaml.safe_load((root / "modules/partition.conf").read_text(encoding="utf-8"))
assert branding.get("componentName") == "datya"
assert settings.get("branding") == "datya"
assert settings.get("prompt-install") is True
assert settings.get("dont-chroot") is False
assert partition.get("initialPartitioningChoice") == "none"
assert partition.get("allowManualPartitioning") is True
assert partition["efi"]["mountPoint"] == "/boot/efi"
print("Calamares YAML and Datya safety settings valid")
PY

grep -q -- '--debian-installer false' "$ISO_DIR/auto/config" || fail "Calamares live-image installer mode is not selected"
grep -q 'calamares' "$ISO_DIR/build-datya-iso.sh" || fail "Calamares is not in the ISO package list"
grep -q 'xfce4' "$ISO_DIR/build-datya-iso.sh" || fail "XFCE is not in the ISO package list"

if [[ "$CHECK_ONLY" == 1 ]]; then
  echo "Calamares setup checks passed (no packages installed)."
  exit 0
fi

command -v calamares >/dev/null || fail "Calamares executable is unavailable after installation"
command -v lb >/dev/null || fail "live-build executable is unavailable after installation"

echo "Calamares host setup complete."
echo "Next safe step: sudo ./iso/build-release.sh amd64 trixie"
echo "Test the resulting ISO in a disposable VM before using a real disk."
