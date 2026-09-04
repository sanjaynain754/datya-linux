#!/usr/bin/env bash
set -euo pipefail

# Datya Linux release builder.
# Builds an ISO, creates a source snapshot and signed/hashed release bundle.
# This script never publishes artifacts, changes a disk, or runs Calamares.
# Usage: sudo ./iso/build-release.sh [amd64|arm64] [bookworm|trixie]

ARCHITECTURE="${1:-amd64}"
SUITE="${2:-trixie}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ISO_DIR="$ROOT_DIR/iso"
VERSION_FILE="$ROOT_DIR/VERSION"
RELEASE_DIR="${DATYA_RELEASE_DIR:-$ROOT_DIR/releases/${SUITE}-${ARCHITECTURE}}"
SKIP_TESTS="${DATYA_SKIP_TESTS:-0}"
SIGNING_KEY="${DATYA_RELEASE_SIGNING_KEY:-}"
export SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-1704067200}"

fail() { echo "ERROR: $*" >&2; exit 1; }
need() { command -v "$1" >/dev/null 2>&1 || fail "required command missing: $1"; }
usage() {
  cat <<EOF
Usage: sudo $0 [amd64|arm64] [bookworm|trixie]
Environment: DATYA_RELEASE_DIR, DATYA_SKIP_TESTS=1, DATYA_RELEASE_SIGNING_KEY, SOURCE_DATE_EPOCH
The command builds locally and never uploads or publishes an artifact.
EOF
}
if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then usage; exit 0; fi
[[ "$(id -u)" -eq 0 ]] || fail "run with sudo/root; live-build uses chroot"
[[ -f "$VERSION_FILE" ]] || fail "VERSION file missing"
DATYA_VERSION="$(tr -d '[:space:]' < "$VERSION_FILE")"
[[ "$DATYA_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || fail "invalid Datya version: $DATYA_VERSION"
if [[ "${GITHUB_REF_NAME:-}" == v* && "${GITHUB_REF_NAME#v}" != "$DATYA_VERSION" ]]; then
  fail "tag ${GITHUB_REF_NAME} does not match VERSION $DATYA_VERSION"
fi
case "$ARCHITECTURE" in amd64|arm64) ;; *) fail "unsupported architecture: $ARCHITECTURE" ;; esac
case "$SUITE" in bookworm|trixie) ;; *) fail "unsupported Debian suite: $SUITE" ;; esac
[[ "$SKIP_TESTS" == 0 || "$SKIP_TESTS" == 1 ]] || fail "DATYA_SKIP_TESTS must be 0 or 1"
for command in bash sha256sum tar git lb; do need "$command"; done
if [[ "$SKIP_TESTS" == 0 ]]; then for command in cargo cmake python3; do need "$command"; done; fi
[[ -f "$ROOT_DIR/packages/manifest.json" ]] || fail "package manifest missing"
[[ -f "$ISO_DIR/auto/config" ]] || fail "live-build configuration missing"
[[ -f "$ISO_DIR/build-datya-iso.sh" ]] || fail "ISO build entrypoint missing"
for file in "$ISO_DIR/templates/calamares/settings.conf" "$ISO_DIR/templates/calamares/modules/partition.conf" "$ISO_DIR/templates/calamares/branding/datya/branding.desc"; do
  [[ -f "$file" ]] || fail "Calamares file missing: $file"
done

cd "$ROOT_DIR"
if [[ "$SKIP_TESTS" == 0 ]]; then
  echo "[1/6] Running source, policy, shell, and Calamares checks"
  cargo fmt --all -- --check
  cargo test --workspace --locked
  cmake -S cpp-control -B build -DCMAKE_BUILD_TYPE=Release >/dev/null
  cmake --build build --parallel >/dev/null
  python3 -m py_compile tools/*.py tests/*.py
  python3 tools/verify-package-manifest.py packages/manifest.json
  bash -n iso/build-datya-iso.sh iso/auto/config iso/templates/hooks/normal/*.hook.chroot
  python3 - <<'PY'
import json
from pathlib import Path
json.loads(Path('packages/manifest.json').read_text(encoding='utf-8'))
print('manifest JSON valid')
try:
    import yaml
except ImportError:
    raise SystemExit('python3-yaml is required for Calamares validation')
root = Path('iso/templates/calamares')
for path in root.rglob('*.conf'):
    yaml.safe_load(path.read_text(encoding='utf-8'))
branding = yaml.safe_load((root / 'branding/datya/branding.desc').read_text(encoding='utf-8'))
settings = yaml.safe_load((root / 'settings.conf').read_text(encoding='utf-8'))
partition = yaml.safe_load((root / 'modules/partition.conf').read_text(encoding='utf-8'))
assert branding.get('componentName') == 'datya'
assert settings.get('branding') == 'datya'
assert settings.get('prompt-install') is True
assert partition.get('initialPartitioningChoice') == 'none'
assert partition.get('allowManualPartitioning') is True
print('Calamares configuration valid and interactive partitioning is enforced')
PY
else
  echo "[1/6] Source checks skipped by DATYA_SKIP_TESTS=1"
fi

BUILD_START="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "[2/6] Building Debian live image (${SUITE}/${ARCHITECTURE})"
SOURCE_DATE_EPOCH="$SOURCE_DATE_EPOCH" bash "$ISO_DIR/build-datya-iso.sh" "$ARCHITECTURE" "$SUITE"
mapfile -t ISO_FILES < <(find "$ISO_DIR" -maxdepth 1 -type f -name '*.iso' -print | sort)
[[ "${#ISO_FILES[@]}" -eq 1 ]] || fail "expected exactly one ISO, found ${#ISO_FILES[@]}"
ISO_PATH="${ISO_FILES[0]}"

rm -rf "$RELEASE_DIR"
mkdir -p "$RELEASE_DIR/source" "$RELEASE_DIR/metadata"
echo "[3/6] Collecting ISO and source bundle"
cp -f "$ISO_PATH" "$RELEASE_DIR/Datya-Linux-v${DATYA_VERSION}-${SUITE}-${ARCHITECTURE}.iso"
[[ -f "$ISO_DIR/binary/SHA256SUMS" ]] && cp -f "$ISO_DIR/binary/SHA256SUMS" "$RELEASE_DIR/metadata/live-build-SHA256SUMS"
git archive --format=tar --prefix="datya-linux-${SUITE}-${ARCHITECTURE}/" HEAD | tar -xf - -C "$RELEASE_DIR/source"
cat > "$RELEASE_DIR/metadata/release-info" <<EOF
project=Datya Linux
version=$DATYA_VERSION
suite=$SUITE
architecture=$ARCHITECTURE
source_date_epoch=$SOURCE_DATE_EPOCH
git_commit=$(git rev-parse HEAD)
built_at_utc=$BUILD_START
installer=calamares
desktop=xfce
EOF

cat > "$RELEASE_DIR/README.txt" <<EOF
Datya Linux release bundle

Files include a Debian live ISO, source snapshot, metadata, and SHA256SUMS.
Verify from this directory with:
  sha256sum --check SHA256SUMS
If SHA256SUMS.asc exists, verify it with:
  gpg --verify SHA256SUMS.asc SHA256SUMS

This build is not a stable-release approval. Debian metadata, package checksums,
Secure Boot signatures, installer behavior, and target hardware require separate
review before distribution. Test in a disposable VM before using real hardware.
EOF

# Hash stable relative paths from inside the release directory.
(cd "$RELEASE_DIR" && find . -type f ! -name SHA256SUMS ! -name SHA256SUMS.asc -printf '%P\n' | LC_ALL=C sort | while IFS= read -r relative; do sha256sum "$relative"; done) > "$RELEASE_DIR/SHA256SUMS"
if [[ -n "$SIGNING_KEY" ]]; then
  need gpg
  echo "[4/6] Signing release checksum manifest"
  gpg --batch --local-user "$SIGNING_KEY" --armor --detach-sign --output "$RELEASE_DIR/SHA256SUMS.asc" "$RELEASE_DIR/SHA256SUMS"
else
  echo "[4/6] GPG signing not requested; release remains unsigned"
fi

echo "[5/6] Verifying release checksums"
(cd "$RELEASE_DIR" && sha256sum --check SHA256SUMS >/dev/null)
echo "[6/6] Release bundle ready: $RELEASE_DIR"
find "$RELEASE_DIR" -maxdepth 2 -type f -printf '%P\n' | LC_ALL=C sort
