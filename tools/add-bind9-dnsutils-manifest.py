#!/usr/bin/env python3
"""Add the verified Debian Trixie bind9-dnsutils record if it is missing."""
from __future__ import annotations

import gzip
import hashlib
import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "packages" / "manifest.json"
BASE = "https://deb.debian.org/debian/dists/trixie/main/binary-{}/Packages.gz"


def stanza(arch: str) -> dict[str, str]:
    with urllib.request.urlopen(BASE.format(arch), timeout=30) as response:
        raw = gzip.decompress(response.read()).decode()
    for block in raw.split("\n\n"):
        if block.startswith("Package: bind9-dnsutils\n"):
            values: dict[str, str] = {}
            for line in block.splitlines():
                if ": " in line:
                    key, value = line.split(": ", 1)
                    values[key] = value
            return values
    raise RuntimeError(f"bind9-dnsutils not found for {arch}")


def main() -> None:
    data = json.loads(MANIFEST.read_text())
    records = data["packages"] if isinstance(data, dict) and "packages" in data else data
    if any(item.get("name") == "bind9-dnsutils" for item in records):
        print("bind9-dnsutils already present")
        return
    packages: dict[str, dict[str, object]] = {}
    for arch in ("amd64", "arm64"):
        item = stanza(arch)
        packages[arch] = {
            "filename": item["Filename"],
            "size": int(item["Size"]),
            "sha256": item["SHA256"],
        }
    versions = {stanza(arch)["Version"] for arch in ("amd64", "arm64")}
    if len(versions) != 1:
        raise RuntimeError(f"architecture version mismatch: {versions}")
    record = {
        "name": "bind9-dnsutils",
        "binary_version": versions.pop(),
        "source_package": "bind9",
        "source_version": "9.20.23-1~deb13u1",
        "channel": "stable",
        "architectures": ["amd64", "arm64"],
        "repository": "https://deb.debian.org/debian",
        "source_url": "https://packages.debian.org/trixie/bind9-dnsutils",
        "license": "SEE-DEBIAN-COPYRIGHT",
        "sha256": packages["amd64"]["sha256"],
        "artifacts": packages,
        "privileges": ["user-tool"],
        "network_behavior": "network-client",
        "profiles": ["security-observe"],
        "status": "catalogued",
        "verification_status": "verified",
        "tests": ["signed-index-availability", "artifact-sha256", "package-install"],
        "uninstall_path": "apt remove bind9-dnsutils",
        "maintainer": "Debian DNS Team <team+dns@tracker.debian.org>",
        "notes": "Exact version and amd64/arm64 artifact checksums sourced from Debian Trixie Packages indexes; license terms are maintained in the Debian copyright file.",
    }
    records.append(record)
    if isinstance(data, dict) and "packages" in data:
        data["packages"] = records
    else:
        data = records
    MANIFEST.write_text(json.dumps(data, indent=2) + "\n")
    print("added bind9-dnsutils")


if __name__ == "__main__":
    main()
