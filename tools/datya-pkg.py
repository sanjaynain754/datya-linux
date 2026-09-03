#!/usr/bin/env python3
"""Datya package manager reference CLI: catalog, verify, and safe transaction plans."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "packages" / "manifest.json"
PACKS = ROOT / "profiles" / "tool-packs.toml"


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def packages() -> list[dict]:
    return load_manifest().get("packages", [])


def find_package(name: str) -> dict:
    for package in packages():
        if package.get("name") == name:
            return package
    raise SystemExit(f"error: package not found: {name}")


def host_arch() -> str:
    return {"x86_64": "amd64", "aarch64": "arm64"}.get(platform.machine(), platform.machine())


def package_summary(package: dict) -> dict:
    arch = host_arch()
    artifact = package.get("artifacts", {}).get(arch, {})
    return {
        "name": package.get("name"),
        "version": package.get("binary_version"),
        "channel": package.get("channel"),
        "source_url": package.get("source_url"),
        "repository": package.get("repository"),
        "license": package.get("license"),
        "architecture": arch,
        "artifact": artifact.get("filename"),
        "artifact_sha256": artifact.get("sha256"),
        "privileges": package.get("privileges", []),
        "network_behavior": package.get("network_behavior"),
        "profiles": package.get("profiles", []),
        "status": package.get("status"),
        "verification_status": package.get("verification_status"),
        "tests": package.get("tests", []),
        "uninstall_path": package.get("uninstall_path"),
    }


def verify_package(package: dict) -> tuple[bool, list[str]]:
    errors: list[str] = []
    arch = host_arch()
    artifact = package.get("artifacts", {}).get(arch)
    if arch not in package.get("architectures", []):
        errors.append(f"unsupported host architecture: {arch}")
    if not artifact:
        errors.append(f"missing artifact metadata for architecture: {arch}")
    if package.get("verification_status") not in {"verified", "metadata-verified"}:
        errors.append("package verification status is not trusted")
    if not str(package.get("repository", "")).startswith("https://"):
        errors.append("repository is not HTTPS")
    if not str(package.get("source_url", "")).startswith("https://"):
        errors.append("source URL is not HTTPS")
    if artifact and not artifact.get("sha256"):
        errors.append("artifact checksum is missing")
    return not errors, errors


def install_plan(name: str) -> dict:
    package = find_package(name)
    ok, errors = verify_package(package)
    return {
        "schema": "datya.transaction.plan.v1",
        "operation": "install",
        "package": package_summary(package),
        "verification": {"passed": ok, "errors": errors},
        "auto_execute": False,
        "requires_confirmation": True,
        "profile_opt_in_required": "security-lab" in package.get("profiles", []),
        "warning": "Review maintainer scripts, services, privileges, and network behavior before confirming.",
    }


def remove_plan(name: str, purge: bool) -> dict:
    package = find_package(name)
    return {
        "schema": "datya.transaction.plan.v1",
        "operation": "purge" if purge else "remove",
        "package": package_summary(package),
        "affected_paths": [package.get("uninstall_path")],
        "shared_dependency_check": "required-before-execution",
        "rollback": "transaction-snapshot-required",
        "auto_execute": False,
        "double_confirmation": True,
        "typed_acknowledgement": name,
        "warning": "This action can remove files, configuration, dependencies, or profile access.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="datya-pkg")
    parser.add_argument("command", choices=("search", "info", "verify", "plan-install", "plan-remove"))
    parser.add_argument("query", nargs="?")
    parser.add_argument("--purge", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "search":
        query = (args.query or "").lower()
        result = [package_summary(p) for p in packages() if query in p.get("name", "").lower() or query in p.get("source_package", "").lower()]
    else:
        if not args.query:
            parser.error("this command requires a package name")
        package = find_package(args.query)
        if args.command == "info":
            result = package_summary(package)
        elif args.command == "verify":
            passed, errors = verify_package(package)
            result = {"package": args.query, "passed": passed, "errors": errors}
        elif args.command == "plan-install":
            result = install_plan(args.query)
        else:
            result = remove_plan(args.query, args.purge)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
