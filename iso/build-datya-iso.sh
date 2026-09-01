#!/usr/bin/env bash
set -euo pipefail

# Datya Linux Debian live-build ISO builder.
# Run on Debian/Ubuntu with root-capable live-build installed.
# Usage: sudo ./build-datya-iso.sh [amd64|arm64] [bookworm|trixie]

ARCHITECTURE="${1:-amd64}"
SUITE="${2:-trixie}"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export DEBIAN_FRONTEND=noninteractive
export SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-1704067200}"

case "$ARCHITECTURE" in amd64|arm64) ;; *) echo "unsupported architecture: $ARCHITECTURE" >&2; exit 2 ;; esac
case "$SUITE" in bookworm|trixie) ;; *) echo "unsupported suite: $SUITE" >&2; exit 2 ;; esac

if [[ "$(id -u)" -ne 0 ]]; then echo "run with sudo: sudo $0 $*" >&2; exit 1; fi
command -v lb >/dev/null || { echo "live-build is required (install package: live-build)" >&2; exit 1; }

cd "$PROJECT_DIR"
rm -rf config cache chroot binary .build
mkdir -p auto config/package-lists config/includes.chroot/etc/datya config/includes.chroot/usr/local/bin
mkdir -p config/includes.chroot/usr/src/datya/cpp-control/src config/includes.chroot/usr/src/datya/kernel
cp -a "$PROJECT_DIR/../cpp-control/." config/includes.chroot/usr/src/datya/cpp-control/
cp -a "$PROJECT_DIR/../kernel/." config/includes.chroot/usr/src/datya/kernel/
mkdir -p config/includes.chroot/etc/systemd/system
cp "$PROJECT_DIR/../systemd/datya-control.service" config/includes.chroot/etc/systemd/system/

ARCHITECTURE="$ARCHITECTURE" DEBIAN_SUITE="$SUITE" ./auto/config

cat > config/package-lists/datya.list.chroot <<'PACKAGES'
systemd-sysv
sudo
apparmor apparmor-utils apparmor-profiles
cryptsetup-initramfs cryptsetup
policykit-1
ca-certificates gnupg
openssh-client
network-manager
procps psmisc iproute2 iputils-ping dnsutils curl
python3
rustc cargo
build-essential cmake pkg-config libssl-dev kmod
live-boot live-config
PACKAGES

if [[ "$ARCHITECTURE" == "amd64" ]]; then
  cat >> config/package-lists/datya.list.chroot <<'PACKAGES'
linux-image-amd64
linux-headers-amd64
firmware-linux-free
PACKAGES
else
  # arm64 live ISO boot support is hardware-specific; validate on target boards.
cat >> config/package-lists/datya.list.chroot <<'PACKAGES'
linux-image-arm64
linux-headers-arm64
PACKAGES
fi

cat > config/includes.chroot/etc/datya/build-info <<EOF
DATYA_SUITE=$SUITE
DATYA_ARCHITECTURE=$ARCHITECTURE
SOURCE_DATE_EPOCH=$SOURCE_DATE_EPOCH
EOF

cat > config/includes.chroot/usr/local/bin/datya-first-boot <<'EOF'
#!/bin/sh
set -eu
printf '%s\n' 'Datya Linux live environment'
printf '%s\n' 'Privacy: local-only defaults; inspect scope before authorized testing.'
EOF
chmod 0755 config/includes.chroot/usr/local/bin/datya-first-boot

# Disable common unnecessary telemetry/reporting services when present.
mkdir -p config/includes.chroot/etc/systemd/system
ln -sf /dev/null config/includes.chroot/etc/systemd/system/apt-daily.service
ln -sf /dev/null config/includes.chroot/etc/systemd/system/apt-daily-upgrade.service

# Add a visible, non-secret policy marker. Actual Guardian binaries are packaged
# only after their signed build artifacts have been independently verified.
cat > config/includes.chroot/etc/datya/policy <<'EOF'
telemetry=disabled-by-default
network-assessment=requires-explicit-scope
kernel-module-policy=signed-only
remote-reporting=disabled-by-default
EOF
chmod 0644 config/includes.chroot/etc/datya/policy

# Build with checksums. For a release, pin a Debian snapshot and verify its
# signed Release metadata before publishing the resulting SHA256SUMS file.
lb build
printf '%s\n' 'ISO build complete. Review binary/live-image-*.iso and SHA256SUMS before release.'
