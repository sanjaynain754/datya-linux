#!/usr/bin/env python3
"""Synchronize and validate Debian repository metadata without installing packages."""
from __future__ import annotations
import argparse, bz2, gzip, hashlib, json, lzma, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ARCHES = {"amd64", "arm64"}
HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")

def fetch(url: str, destination: Path) -> None:
    request = Request(url, headers={"User-Agent": "Datya-Debian-Sync/1.0"})
    try:
        with urlopen(request, timeout=30) as response, destination.open("wb") as output:
            shutil.copyfileobj(response, output)
    except (HTTPError, URLError, OSError) as exc:
        raise RuntimeError(f"download failed for {url}: {exc}") from exc

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""): digest.update(block)
    return digest.hexdigest()

def verify_inrelease(path: Path, keyring: Path | None) -> str:
    if keyring is None:
        raise RuntimeError("a Debian archive keyring is required; pass --keyring")
    if not keyring.is_file(): raise RuntimeError(f"keyring does not exist: {keyring}")
    result = subprocess.run(["gpgv", "--keyring", str(keyring), str(path)], capture_output=True, text=True)
    if result.returncode != 0: raise RuntimeError(f"InRelease signature verification failed: {result.stderr.strip()}")
    raw = path.read_text(encoding="utf-8", errors="strict")
    marker = "-----BEGIN PGP SIGNATURE-----"
    payload = raw.split(marker, 1)[0] if marker in raw else ""
    payload = payload.replace("-----BEGIN PGP SIGNED MESSAGE-----\n", "", 1)
    payload = re.sub(r"^Hash: .*\n\n", "", payload, count=1, flags=re.MULTILINE)
    if not payload.startswith("Origin:") and "\nOrigin:" not in payload: raise RuntimeError("signed InRelease payload is malformed")
    return payload

def release_hashes(payload: str) -> dict[str, tuple[str, int]]:
    hashes: dict[str, tuple[str, int]] = {}; in_sha = False
    for line in payload.splitlines():
        if line == "SHA256:": in_sha = True; continue
        if in_sha and line and not line.startswith(" "): break
        if in_sha:
            fields = line.split()
            if len(fields) == 3 and HEX64.fullmatch(fields[0]): hashes[fields[2]] = (fields[0].lower(), int(fields[1]))
    return hashes

def decompress(path: Path) -> bytes:
    suffix = path.suffix
    data = path.read_bytes()
    if suffix == ".gz": return gzip.decompress(data)
    if suffix == ".bz2": return bz2.decompress(data)
    if suffix == ".xz": return lzma.decompress(data)
    return data

def parse_packages(raw: bytes) -> dict[tuple[str, str], dict[str, str]]:
    records: dict[tuple[str, str], dict[str, str]] = {}; current: dict[str, str] = {}; last = ""
    for line in raw.decode("utf-8", "replace").splitlines() + [""]:
        if not line.strip():
            if current.get("Package") and current.get("Version"): records[(current["Package"], current["Version"])] = current
            current = {}; last = ""; continue
        if line.startswith((" ", "\t")) and last: current[last] += "\n" + line.strip(); continue
        if ": " not in line: continue
        key, value = line.split(": ", 1); current[key] = value; last = key
    return records

def load_manifest(path: Path) -> dict:
    try: return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc: raise RuntimeError(f"manifest read failed: {exc}") from exc

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default="packages/manifest.json")
    parser.add_argument("--repository", default="https://deb.debian.org/debian")
    parser.add_argument("--suite", default="trixie")
    parser.add_argument("--components", default="main")
    parser.add_argument("--architecture", default="amd64", choices=sorted(ARCHES))
    parser.add_argument("--keyring", default="/usr/share/keyrings/debian-archive-keyring.gpg")
    parser.add_argument("--cache", default=".cache/datya-debian-sync")
    parser.add_argument("--report", default="/tmp/datya-debian-sync-report.json")
    parser.add_argument("--write-manifest", action="store_true", help="write only verified availability metadata; never changes package checksums")
    parser.add_argument("--allow-insecure-no-signature", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not args.repository.startswith("https://"): print("ERROR: repository must use HTTPS", file=sys.stderr); return 2
    manifest = load_manifest(Path(args.manifest)); base = manifest.get("base", {})
    if base.get("distribution") != "debian" or args.suite != base.get("suite", args.suite): print("ERROR: repository does not match manifest Debian base", file=sys.stderr); return 2
    cache = Path(args.cache); cache.mkdir(parents=True, exist_ok=True); suite_root = f"{args.repository.rstrip('/')}/dists/{args.suite}"
    inrelease = cache / f"{args.suite}-InRelease"
    try:
        fetch(f"{suite_root}/InRelease", inrelease)
        try: payload = verify_inrelease(inrelease, Path(args.keyring))
        except RuntimeError:
            if not args.allow_insecure_no_signature: raise
            payload = inrelease.read_text(encoding="utf-8"); print("WARNING: signature verification bypassed", file=sys.stderr)
        hashes = release_hashes(payload)
        if not hashes: raise RuntimeError("signed metadata contains no SHA256 index hashes")
        package_files = [f"{args.components}/binary-{args.architecture}/Packages.xz", f"{args.components}/binary-{args.architecture}/Packages.gz", f"{args.components}/binary-{args.architecture}/Packages"]
        index_file = next((item for item in package_files if item in hashes), None)
        if not index_file: raise RuntimeError(f"no supported package index listed for {args.components}/{args.architecture}")
        index_path = cache / Path(index_file).name; fetch(f"{suite_root}/{index_file}", index_path)
        expected_hash, expected_size = hashes[index_file]; actual_size = index_path.stat().st_size
        if actual_size != expected_size or sha256(index_path) != expected_hash: raise RuntimeError(f"package index hash/size mismatch: {index_file}")
        available = parse_packages(decompress(index_path)); results=[]; failures=[]
        for package in manifest.get("packages", []):
            name, version = package.get("name"), package.get("binary_version")
            record = {"name": name, "requested_version": version, "architecture": args.architecture, "repository": args.repository}
            candidate = available.get((name, version))
            if candidate is None: record["status"] = "missing"; failures.append(f"{name}={version} is unavailable")
            else:
                record["status"] = "available"; record["source_package"] = candidate.get("Source", candidate.get("Package")); record["section"] = candidate.get("Section", "")
            results.append(record)
        report = {"schema_version":"datya.sync.v1", "repository":args.repository, "suite":args.suite, "architecture":args.architecture, "signature":"verified" if not args.allow_insecure_no_signature else "bypassed", "index": {"path":index_file,"sha256":expected_hash,"size":expected_size}, "packages":results, "failures":failures}
        Path(args.report).parent.mkdir(parents=True, exist_ok=True); Path(args.report).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        if args.write_manifest and not failures:
            manifest["sync"] = {"repository":args.repository,"suite":args.suite,"architecture":args.architecture,"inrelease_sha256":sha256(inrelease),"package_index":report["index"],"signature":"verified"}
            Path(args.manifest).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        print(f"sync valid: signature={report['signature']} index={index_file} packages={len(results)} failures={len(failures)} report={args.report}")
        return 1 if failures else 0
    except RuntimeError as exc: print(f"ERROR: {exc}", file=sys.stderr); return 2

if __name__ == "__main__": sys.exit(main())
