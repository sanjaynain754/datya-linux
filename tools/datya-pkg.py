#!/usr/bin/env python3
"""Datya package manager reference engine.

The default backend is record-only: it creates auditable transaction state but
never invokes apt/dpkg. A future privileged backend must consume the same plan
and confirmation contract.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "packages" / "manifest.json"
DEFAULT_STATE = ROOT / "build" / "datya-package-state.json"


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
        "profile_opt_in_required": bool(package.get("profiles")),
        "backend": "record-only-until-privileged-backend-is-reviewed",
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
        "backend": "record-only-until-privileged-backend-is-reviewed",
        "warning": "This action can remove files, configuration, dependencies, or profile access.",
    }


def load_state(path: Path) -> dict:
    if not path.exists():
        return {"schema": "datya.package-state.v1", "installed": {}, "transactions": []}
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(state, handle, indent=2, sort_keys=True)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)


def transaction_id(plan: dict) -> str:
    payload = json.dumps(plan, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload + str(time.time_ns()).encode("ascii")).hexdigest()[:16]


def commit_record(plan: dict, state_path: Path, acknowledgement: str) -> dict:
    if not plan.get("verification", {}).get("passed", True):
        raise SystemExit("error: verification failed; transaction was not recorded")
    if acknowledgement != plan["package"]["name"]:
        raise SystemExit("error: exact package acknowledgement did not match; transaction cancelled")
    state = load_state(state_path)
    previous = json.loads(json.dumps(state["installed"]))
    name = plan["package"]["name"]
    if plan["operation"] == "install":
        state["installed"][name] = plan["package"]
    else:
        state["installed"].pop(name, None)
    record = {
        "id": transaction_id(plan),
        "plan": plan,
        "previous_installed": previous,
        "new_installed": state["installed"],
        "backend": "record-only",
        "timestamp": int(time.time()),
    }
    state["transactions"].append(record)
    save_state(state_path, state)
    return record


def rollback(state_path: Path, txid: str) -> dict:
    state = load_state(state_path)
    for record in reversed(state["transactions"]):
        if record["id"] == txid:
            state["installed"] = record["previous_installed"]
            state["transactions"].append({
                "id": transaction_id(record["plan"]),
                "operation": "rollback",
                "rolled_back": txid,
                "previous_installed": record["new_installed"],
                "new_installed": state["installed"],
                "backend": "record-only",
                "timestamp": int(time.time()),
            })
            save_state(state_path, state)
            return state["transactions"][-1]
    raise SystemExit(f"error: transaction not found: {txid}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="datya-pkg")
    parser.add_argument("command", choices=("search", "info", "verify", "plan-install", "plan-remove", "install", "remove", "rollback", "state"))
    parser.add_argument("query", nargs="?")
    parser.add_argument("--purge", action="store_true")
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--ack", help="type the exact package name for destructive confirmation")
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    args = parser.parse_args(argv)
    if args.command == "search":
        query = (args.query or "").lower()
        result = [package_summary(p) for p in packages() if query in p.get("name", "").lower() or query in p.get("source_package", "").lower()]
    elif args.command == "state":
        result = load_state(args.state)
    elif args.command == "rollback":
        if not args.query:
            parser.error("rollback requires a transaction id")
        result = rollback(args.state, args.query)
    else:
        if not args.query:
            parser.error("this command requires a package name")
        if args.command == "info":
            result = package_summary(find_package(args.query))
        elif args.command == "verify":
            passed, errors = verify_package(find_package(args.query))
            result = {"package": args.query, "passed": passed, "errors": errors}
        elif args.command == "plan-install":
            result = install_plan(args.query)
        elif args.command == "plan-remove":
            result = remove_plan(args.query, args.purge)
        elif args.command == "install":
            plan = install_plan(args.query)
            if not args.confirm:
                result = plan
            else:
                result = commit_record(plan, args.state, args.ack or "")
        else:
            plan = remove_plan(args.query, args.purge)
            if not args.confirm:
                result = plan
            else:
                result = commit_record(plan, args.state, args.ack or "")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
