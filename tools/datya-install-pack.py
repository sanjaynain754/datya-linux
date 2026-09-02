#!/usr/bin/env python3
"""Plan, verify, and explicitly install a Datya tool pack.

Installation is never implicit: without --install the command only verifies
metadata and prints an apt plan. Packages must be present in the curated
manifest with verification_status=verified and a real SHA-256 checksum.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.request import urlopen


def host_architecture() -> str:
    result = subprocess.run(["dpkg", "--print-architecture"], capture_output=True, text=True, check=False)
    architecture = result.stdout.strip() if result.returncode == 0 else ""
    return architecture if architecture in {"amd64", "arm64"} else ("amd64" if os.uname().machine == "x86_64" else "arm64" if os.uname().machine == "aarch64" else "")
import tomllib

ROOT = Path(__file__).resolve().parents[1]
PACKS = ROOT / "profiles" / "tool-packs.toml"
MANIFEST = ROOT / "packages" / "manifest.json"
SUPPORTED_ARCHES = {"amd64", "arm64"}
PLACEHOLDER_CHECKSUMS = {"a" * 64, "b" * 64}


def load_data() -> tuple[dict, dict]:
    with PACKS.open("rb") as stream:
        packs = tomllib.load(stream)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return packs.get("pack", {}), {item["name"]: item for item in manifest.get("packages", [])}


def resolve(pack_name: str | None, all_packs: bool, packs: dict, manifest: dict) -> tuple[list[str], list[str]]:
    if all_packs:
        selected = packs
    elif pack_name in packs:
        selected = {pack_name: packs[pack_name]}
    else:
        raise ValueError(f"unknown pack: {pack_name}; use --list")

    names = []
    errors = []
    for name, pack in selected.items():
        for tool in pack.get("tools", []):
            if tool in names:
                continue
            record = manifest.get(tool)
            if not record:
                errors.append(f"{name}: {tool} is absent from packages/manifest.json")
                continue
            if record.get("verification_status") != "verified":
                errors.append(f"{tool}: verification_status={record.get('verification_status')!r}, expected 'verified'")
            checksum = str(record.get("sha256", "")).lower()
            if len(checksum) != 64 or not all(char in "0123456789abcdef" for char in checksum) or checksum in PLACEHOLDER_CHECKSUMS:
                errors.append(f"{tool}: real SHA-256 checksum is required")
            if not set(record.get("architectures", [])) & SUPPORTED_ARCHES:
                errors.append(f"{tool}: no supported architecture")
            if not str(record.get("repository", "")).startswith("https://"):
                errors.append(f"{tool}: repository must use HTTPS")
            names.append(tool)
    return names, errors


def verify_downloads(names: list[str], manifest: dict, directory: Path, architecture: str) -> list[Path]:
    downloaded: list[Path] = []
    for name in names:
        record = manifest[name]
        version = record["binary_version"]
        artifact = record["artifacts"][architecture]
        filename = Path(artifact["filename"])
        if filename.is_absolute() or ".." in filename.parts or filename.suffix != ".deb":
            raise RuntimeError(f"invalid artifact filename for {name}")
        package = directory / filename.name
        url = record["repository"].rstrip("/") + "/" + artifact["filename"]
        try:
            with urlopen(url, timeout=30) as response, package.open("wb") as output:
                shutil.copyfileobj(response, output)
        except OSError as exc:
            raise RuntimeError(f"could not download {name}={version}: {exc}") from exc
        expected = str(artifact["sha256"]).lower()
        digest = hashlib.sha256(package.read_bytes()).hexdigest()
        if digest != expected:
            raise RuntimeError(f"checksum mismatch for {package.name}: expected {expected}, got {digest}")
        downloaded.append(package)
    return downloaded


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--pack", help="name of one curated pack")
    group.add_argument("--all", action="store_true", help="resolve all curated packs")
    parser.add_argument("--list", action="store_true", help="list packs before resolving")
    parser.add_argument("--verify-only", action="store_true", help="verify metadata and downloaded artifacts, never install")
    parser.add_argument("--install", action="store_true", help="install only after verification; requires root and --yes")
    parser.add_argument("--yes", action="store_true", help="confirm package installation")
    parser.add_argument("--keep-downloads", action="store_true")
    args = parser.parse_args()

    packs, manifest = load_data()
    if args.list:
        for name, pack in packs.items():
            print(f"{name}: {pack['summary']} ({len(pack.get('tools', []))} tools)")
    if args.install and (os.geteuid() != 0 or not args.yes):
        print("refusing installation: use sudo with --install --yes", file=sys.stderr)
        return 2

    try:
        names, errors = resolve(args.pack, args.all, packs, manifest)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps({"packages": names, "count": len(names), "mode": "install" if args.install else "dry-run"}, indent=2))
    if errors:
        print("verification blocked:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    if not names:
        print("no packages resolved", file=sys.stderr)
        return 1
    print("metadata verification passed")
    if not args.install and not args.verify_only:
        print("dry-run only: no packages were changed")
        return 0

    if shutil.which("apt-get") is None:
        print("apt-get is required for artifact verification/install", file=sys.stderr)
        return 2
    architecture = host_architecture()
    if not architecture:
        print("unsupported host architecture; expected amd64 or arm64", file=sys.stderr)
        return 2
    if any(architecture not in manifest[name].get("artifacts", {}) for name in names):
        print(f"manifest has no artifact for host architecture: {architecture}", file=sys.stderr)
        return 1
    with tempfile.TemporaryDirectory(prefix="datya-pack-") as temp:
        directory = Path(temp)
        try:
            packages = verify_downloads(names, manifest, directory, architecture)
            print(f"artifact verification passed: {len(packages)} package(s)")
            if args.verify_only:
                return 0
            command = ["apt-get", "install", "--yes", "--no-install-recommends", *map(str, packages)]
            completed = subprocess.run(command, check=False)
            if completed.returncode:
                return completed.returncode
            print("installation completed")
            if args.keep_downloads:
                destination = Path.cwd() / "datya-package-downloads"
                destination.mkdir(exist_ok=True)
                for package in packages:
                    shutil.copy2(package, destination / package.name)
                print(f"verified artifacts copied to {destination}")
            return 0
        except (OSError, KeyError, RuntimeError) as exc:
            print(f"installation verification failed: {exc}", file=sys.stderr)
            return 1


if __name__ == "__main__":
    raise SystemExit(main())
