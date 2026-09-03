#!/usr/bin/env bash
set -euo pipefail

# Build and package a Datya Linux ISO release. This script never publishes artifacts.
# Usage: sudo ./iso/build-release.sh [amd64|arm64] [bookworm|trixie]

ARCHITECTURE="${1:-amd64}"
SUITE="${2:-trixie}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ISO_DIR="$ROOT_DIR/iso"
RELEASE_DIR="${DATYA_RELEASE_DIR:-$ROOT_DIR/releases/${SUITE}-${ARCHITECTURE}}"
SKIP_TESTS="${DATYA_SKIP_TESTS:-0}"
SIGNING_KEY="${DATYA_RELEASE_SIGNING_KEY:-}"
export SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-1704067200}"

fail() { echo "ERROR: $*" >&2; exit 1; }
need() { command -v "$1" >/dev/null 2>&1 || fail "required command missing: $1"; }
[[ "$(id -u)" -eq 0 ]] || fail "run with sudo/root; ISO build uses chroot"
case "$ARCHITECTURE" in amd64|arm64) ;; *) fail "unsupported architecture: $ARCHITECTURE" ;; esac
case "$SUITE" in bookworm|trixie) ;; *) fail "unsupported Debian suite: $SUITE" ;; esac
need bash; need sha256sum; need tar; need git
[[ "$SKIP_TESTS" == 1 ]] || { need cargo; need cmake; need python3; }
need lb
[[ -f "$ROOT_DIR/packages/manifest.json" ]] || fail "package manifest missing"
[[ -f "$ISO_DIR/auto/config" ]] || fail "live-build configuration missing"
[[ -f "$ISO_DIR/config/includes.chroot/etc/calamares/settings.conf" ]] || fail "Calamares settings missing"
[[ -f "$ISO_DIR/config/includes.chroot/etc/calamares/modules/partition.conf" ]] || fail "Calamares partition configuration missing"

cd "$ROOT_DIR"
if [[ "$SKIP_TESTS" != 1 ]]; then
  echo "[1/6] Running source and policy checks"
  cargo fmt --all -- --check
  cargo test --workspace --locked
  cmake -S cpp-control -B build -DCMAKE_BUILD_TYPE=Release >/dev/null
  cmake --build build --parallel >/dev/null
  python3 -m py_compile tools/*.py tests/*.py
  python3 tools/verify-package-manifest.py packages/manifest.json
  bash -n iso/build-datya-iso.sh iso/auto/config iso/config/hooks/normal/*.hook.chroot
  python3 - <<'PY'
import json
from pathlib import Path
json.loads(Path('packages/manifest.json').read_text())
print('manifest JSON valid')
PY
else
  echo "[1/6] Source checks skipped by DATYA_SKIP_TESTS=1"
fi

# Ensure build script receives only controlled environment values.
echo "[2/6] Building Debian live image (${SUITE}/${ARCHITECTURE})"
SOURCE_DATE_EPOCH="$SOURCE_DATE_EPOCH" bash "$ISO_DIR/build-datya-iso.sh" "$ARCHITECTURE" "$SUITE"
ISO_PATH="$(find "$ISO_DIR/binary" -maxdepth 1 -type f -name '*.iso' -print -quit)"
[[ -n "$ISO_PATH" && -f "$ISO_PATH" ]] || fail "live-build completed without an ISO"

rm -rf "$RELEASE_DIR"
mkdir -p "$RELEASE_DIR/source" "$RELEASE_DIR/metadata"
echo "[3/6] Collecting ISO and component bundle"
cp -f "$ISO_PATH" "$RELEASE_DIR/Datya-Linux-${SUITE}-${ARCHITECTURE}.iso"
[[ -f "$ISO_DIR/SHA256SUMS" ]] && cp -f "$ISO_DIR/SHA256SUMS" "$RELEASE_DIR/metadata/live-build-SHA256SUMS"
cat > "$RELEASE_DIR/metadata/release-info" <<EOF
project=Datya Linux
suite=$SUITE
architecture=$ARCHITECTURE
source_date_epoch=$SOURCE_DATE_EPOCH
git_commit=$(git rev-parse HEAD)
built_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)
installer=calamares
desktop=xfce
EOF

# Source bundle excludes build output, private signing material, and VCS metadata.
git archive --format=tar --prefix="datya-linux-${SUITE}-${ARCHITECTURE}/" HEAD | tar -xf - -C "$RELEASE_DIR/source"
find "$RELEASE_DIR" -type f -not -name 'SHA256SUMS' -print0 | sort -z | xargs -0 sha256sum > "$RELEASE_DIR/SHA256SUMS"
if [[ -n "$SIGNING_KEY" ]]; then
  need gpg
  echo "[4/6] Signing release checksum manifest"
  gpg --batch --local-user "$SIGNING_KEY" --armor --detach-sign --output "$RELEASE_DIR/SHA256SUMS.asc" "$RELEASE_DIR/SHA256SUMS"
else
  echo "[4/6] GPG signing not requested; release remains unsigned"
fi

cat > "$RELEASE_DIR/README.txt" <<EOF
Datya Linux release bundle

This bundle contains a Debian live ISO, source snapshot, metadata, and SHA256SUMS.
Verify before use:
  sha256sum --check SHA256SUMS
If SHA256SUMS.asc exists, verify it with:
  gpg --verify SHA256SUMS.asc SHA256SUMS

This is not a stable release until Debian metadata, package checksums, Secure Boot
signatures, installer behavior, and target hardware have passed independent review.
EOF

echo "[5/6] Verifying release checksums"
(cd "$RELEASE_DIR" && sha256sum --check SHA256SUMS >/dev/null)
echo "[6/6] Release bundle ready: $RELEASE_DIR"
find "$RELEASE_DIR" -maxdepth 2 -type f -printf '%P\n' | sort
