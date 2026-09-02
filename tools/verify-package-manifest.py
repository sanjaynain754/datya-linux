#!/usr/bin/env python3
"""Verify Datya's curated package manifest structure; never installs packages."""
import argparse, hashlib, json, re, sys
from pathlib import Path

CHANNELS = {"stable", "testing", "experimental"}
ARCHES = {"amd64", "arm64"}
HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")
REQUIRED = {"name", "binary_version", "source_package", "source_version", "channel", "architectures", "repository", "source_url", "license", "sha256", "privileges", "network_behavior", "profiles", "status", "tests", "uninstall_path", "maintainer", "verification_status"}

def fail(errors, message): errors.append(message)
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", nargs="?", default="packages/manifest.json")
    parser.add_argument("--strict", action="store_true", help="fail on pending checks/placeholders")
    args = parser.parse_args()
    try: data = json.loads(Path(args.manifest).read_text())
    except (OSError, json.JSONDecodeError) as exc: print(f"manifest error: {exc}", file=sys.stderr); return 2
    errors=[]; warnings=[]
    if data.get("schema_version") != "datya.package.v1": fail(errors, "unsupported schema_version")
    base=data.get("base", {}); arches=set(base.get("architectures", []))
    if base.get("distribution") != "debian" or not arches.issubset(ARCHES): fail(errors, "base must be Debian with supported architectures")
    packages=data.get("packages")
    if not isinstance(packages, list) or not packages: fail(errors, "packages must be a non-empty list"); packages=[]
    seen=set()
    for index, package in enumerate(packages):
        prefix=f"packages[{index}]"
        if not isinstance(package, dict): fail(errors, f"{prefix} must be an object"); continue
        missing=REQUIRED-set(package)
        if missing: fail(errors, f"{prefix} missing: {','.join(sorted(missing))}")
        name=package.get("name", "")
        if name in seen: fail(errors, f"duplicate package: {name}")
        seen.add(name)
        if package.get("channel") not in CHANNELS: fail(errors, f"{prefix} invalid channel")
        if not package.get("architectures") or not set(package.get("architectures", [])).issubset(arches): fail(errors, f"{prefix} architecture not in base")
        for field in ("repository", "source_url"):
            if not str(package.get(field, "")).startswith("https://"): fail(errors, f"{prefix}.{field} must use https")
        if not package.get("license") or package.get("license") == "UNKNOWN": fail(errors, f"{prefix}.license is not acceptable")
        if not HEX64.fullmatch(str(package.get("sha256", ""))): fail(errors, f"{prefix}.sha256 must be 64 lowercase/hex characters")
        if package.get("verification_status") != "verified":
            warnings.append(f"{name}: verification_status={package.get('verification_status')}")
        if "placeholder" in str(package.get("notes", "")).lower() or set(str(package.get("sha256", "")).lower()) in ({"a"}, {"b"}):
            warnings.append(f"{name}: placeholder checksum or note")
    if args.strict and warnings: errors.extend(warnings)
    for warning in warnings: print(f"WARNING: {warning}", file=sys.stderr)
    if errors:
        for error in errors: print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"manifest valid: {len(packages)} package records; strict={args.strict}")
    return 0

if __name__ == "__main__": sys.exit(main())
