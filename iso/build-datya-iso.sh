#!/usr/bin/env bash
set -euo pipefail

# Datya Linux Debian live-build ISO builder.
# Run on Debian/Ubuntu with root-capable live-build installed.
# Usage: sudo ./build-datya-iso.sh [amd64|arm64] [bookworm|trixie]

ARCHITECTURE="${1:-amd64}"
SUITE="${2:-trixie}"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION_FILE="$PROJECT_DIR/../VERSION"
[[ -f "$VERSION_FILE" ]] || { echo "VERSION file is required" >&2; exit 1; }
DATYA_VERSION="$(tr -d '[:space:]' < "$VERSION_FILE")"
[[ "$DATYA_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "invalid Datya version: $DATYA_VERSION" >&2; exit 1; }
export DEBIAN_FRONTEND=noninteractive
export SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-1704067200}"

case "$ARCHITECTURE" in amd64|arm64) ;; *) echo "unsupported architecture: $ARCHITECTURE" >&2; exit 2 ;; esac
case "$SUITE" in bookworm|trixie) ;; *) echo "unsupported suite: $SUITE" >&2; exit 2 ;; esac

if [[ "$(id -u)" -ne 0 ]]; then echo "run with sudo: sudo $0 $*" >&2; exit 1; fi
command -v lb >/dev/null || { echo "live-build is required (install package: live-build)" >&2; exit 1; }

cd "$PROJECT_DIR"
rm -rf config cache chroot binary .build
mkdir -p auto config/package-lists config/includes.chroot/etc/datya config/includes.chroot/usr/local/bin config/includes.chroot/usr/bin
# Restore tracked Calamares and security-hook templates after the clean build reset.
cp -a "$PROJECT_DIR/templates/calamares/." config/includes.chroot/etc/calamares/
mkdir -p config/hooks/normal
cp -a "$PROJECT_DIR/templates/hooks/normal/." config/hooks/normal/
# live-build invokes the legacy `rsvg` name; Trixie provides `rsvg-convert`.
cat > config/includes.chroot/usr/bin/rsvg <<'EOF'
#!/bin/sh
set -eu
# Compatibility for: rsvg --format png --height H --width W input.svg output.png
format=png
height=
width=
while [ "$#" -gt 0 ]; do
  case "$1" in
    --format) format="$2"; shift 2 ;;
    --height) height="$2"; shift 2 ;;
    --width) width="$2"; shift 2 ;;
    --*) shift 2 ;;
    *) break ;;
  esac
done
input="${1:?missing input SVG}"
output="${2:?missing output PNG}"
exec /usr/bin/rsvg-convert --format "$format" --height "$height" --width "$width" "$input" --output "$output"
EOF
chmod 0755 config/includes.chroot/usr/bin/rsvg
mkdir -p config/includes.chroot/usr/src/datya/cpp-control/src config/includes.chroot/usr/src/datya/kernel
cp -a "$PROJECT_DIR/../cpp-control/." config/includes.chroot/usr/src/datya/cpp-control/
cp -a "$PROJECT_DIR/../kernel/." config/includes.chroot/usr/src/datya/kernel/
mkdir -p config/includes.chroot/etc/systemd/system
cp "$PROJECT_DIR/../systemd/datya-control.service" config/includes.chroot/etc/systemd/system/

ARCHITECTURE="$ARCHITECTURE" DEBIAN_SUITE="$SUITE" ./auto/config

# Debian Trixie installs syslinux modules below /usr/lib/syslinux/modules/bios,
# while this live-build release ships absolute symlinks to /usr/lib/syslinux.
# Provide a local isolinux template with real files so ISO assembly is portable.
if [[ "$ARCHITECTURE" == "amd64" ]]; then
  mkdir -p config/bootloaders/isolinux
  cp -a /usr/share/live/build/bootloaders/isolinux/. config/bootloaders/isolinux/
  rm -f config/bootloaders/isolinux/isolinux.bin config/bootloaders/isolinux/vesamenu.c32
  cp /usr/lib/ISOLINUX/isolinux.bin config/bootloaders/isolinux/isolinux.bin
  cp /usr/lib/syslinux/modules/bios/vesamenu.c32 config/bootloaders/isolinux/vesamenu.c32
  # The Ubuntu live-build script unconditionally repacks this legacy archive.
  (cd /tmp && printf '' | cpio -o -H newc > "$PROJECT_DIR/config/bootloaders/isolinux/bootlogo")
fi

# Ubuntu's packaged live-build currently emits the obsolete ${SUITE}/updates
# security suite for Debian derivatives. Disable that generated stanza above and
# provide the current signed Debian security suite explicitly for Trixie.
if [[ "$SUITE" == "trixie" ]]; then
  mkdir -p config/archives
  cat > config/archives/datya-security.list.chroot <<'EOF'
deb https://security.debian.org/debian-security trixie-security main contrib non-free-firmware
EOF
  cp config/archives/datya-security.list.chroot config/archives/datya-security.list.binary
fi

cat > config/package-lists/datya.list.chroot <<'PACKAGES'
sudo
apparmor apparmor-utils apparmor-profiles
cryptsetup-initramfs cryptsetup
polkitd pkexec
ca-certificates gnupg
syslinux-utils
openssh-client
network-manager
procps psmisc iproute2 iputils-ping dnsutils curl
python3
rustc cargo
build-essential cmake pkg-config libssl-dev kmod
live-boot live-config live-config-systemd
xfce4 xfce4-goodies lightdm lightdm-gtk-greeter
firefox-esr xterm dbus-x11
calamares
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
DATYA_VERSION=$DATYA_VERSION
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

# Default desktop integration: a visible launcher opens the local dashboard.
mkdir -p config/includes.chroot/usr/share/applications config/includes.chroot/usr/share/datya
cp "$PROJECT_DIR/../dashboard/index.html" config/includes.chroot/usr/share/datya/dashboard.html
cat > config/includes.chroot/usr/local/bin/datya-dashboard <<'EOF'
#!/bin/sh
set -eu
exec firefox-esr --new-window file:///usr/share/datya/dashboard.html
EOF
chmod 0755 config/includes.chroot/usr/local/bin/datya-dashboard
cat > config/includes.chroot/usr/share/applications/datya-dashboard.desktop <<'EOF'
[Desktop Entry]
Type=Application
Name=Datya Security Dashboard
Comment=Local collaboration and security event dashboard
Exec=/usr/local/bin/datya-dashboard
Icon=security-high
Terminal=false
Categories=Security;System;
EOF
cat > config/includes.chroot/usr/share/applications/calamares.desktop <<'EOF'
[Desktop Entry]
Type=Application
Name=Install Datya Linux
Comment=Install Datya Linux to this computer
Exec=pkexec calamares
Icon=system-software-install
Terminal=false
Categories=System;Settings;
EOF

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
