# Datya Debian Package Ecosystem

Datya's package ecosystem is a curated layer over a Debian base. It does not mix Kali repositories or copy package metadata without attribution. The manifest records what Datya intends to catalogue; a package is not considered installable merely because it appears in the catalog.

## Manifest structure

`packages/manifest.json` has four layers. `base` defines the Debian suite and supported architectures. `channels` defines promotion policy. Each `packages` record identifies the Debian binary and source package, exact versions, repository and upstream URLs, SPDX-style license, artifact SHA-256, supported architectures, privilege requirements, network behavior, Datya profiles, tests, uninstall path, maintainer, and verification status.

A future signed release should add repository snapshot identifiers, InRelease signature fingerprints, source tarball checksums, SBOM digest, vulnerability scan result, reproducible-build result, and review approvals. Placeholder checksums are acceptable only while a record is `catalogued` and never for a release artifact.

## Channel rules

| Channel | Promotion gate | Intended use |
|---|---|---|
| `stable` | Signed Debian metadata, exact artifact checksum, license/provenance review, install and regression tests, vulnerability review | Release images and default profiles |
| `testing` | Automated install/tests and maintainer review | Candidate updates |
| `experimental` | Explicit maintainer approval and isolation note | Early or hardware-specific work |

No package reaches `stable` with a floating version, missing license, unverified source, placeholder checksum, unsupported architecture, unknown privilege behavior, or failed tests. Network-capable packages require a declared behavior and explicit Datya scope policy.

## Verification command

```bash
python3 tools/verify-package-manifest.py packages/manifest.json
python3 tools/verify-package-manifest.py --strict packages/manifest.json
```

Normal mode validates structure and reports pending records as warnings. Strict mode is a release gate and fails until every record is verified and placeholder metadata is removed. The verifier is metadata-only: it never downloads or installs packages. A release pipeline must separately verify Debian repository signatures, artifact checksums, SBOMs, vulnerability status, and reproducible builds before producing an ISO.

## Automated repository sync

`tools/datya-debian-sync.py` downloads Debian `InRelease`, verifies it with `gpgv` and an explicitly supplied archive keyring, selects the architecture-specific `Packages` index, verifies its SHA-256 and byte size against the signed metadata, and checks every manifest package/version for availability. It writes a JSON report and never installs or upgrades packages.

```bash
python3 tools/datya-debian-sync.py \
  --manifest packages/manifest.json \
  --architecture amd64 \
  --keyring /usr/share/keyrings/debian-archive-keyring.gpg \
  --report /var/lib/datya/debian-sync/report.json
```

The command fails closed when HTTPS, the keyring, the signature, the signed index hash, or the index size is invalid. A report exit status of `1` means metadata was valid but one or more curated versions were unavailable; `2` means a validation or operational error. `--allow-insecure-no-signature` exists only for local development and must not be used in release automation. `--write-manifest` is conservative: it records verified sync metadata only when every requested package is available and never replaces package checksums with unverified values.

For a host with systemd, review and install the example service and timer files under `systemd/`. The timer performs metadata synchronization only; package installation remains a separate reviewed release step.
