# Changelog

## v0.1.2 — 2026-09-03

This stable engineering milestone consolidates the first Datya Linux security-workbench foundation. It is stable as a source and prototype milestone, not a claim that the bootable distribution, kernel module, or hardware matrix is production-complete.

### Included

- Added the modular package-manager reference CLI for catalog search, package information, provenance checks, and non-executing install/remove plans.
- Added fail-closed `safe`, `project`, and `lab` sandbox profiles plus explicit `power-user` mode.
- Added the indexed module repository structure and initial module catalog.
- Added the Rust `datya-root-exec` reference boundary for already-authorized, explicit root actions without shell interpretation or privilege escalation.
- Added configurable IPv6 observation to the read-only Guardian kernel sensor.
- Added package malware/provenance, double-confirmation, rollback, and live-stream social-engineering safety design.
- Added the 12-slide kernel, tool-ecosystem, package-manager, and safety presentation script.
- Added progress-graph artifacts and expanded Python regression coverage.

### Validation

- Python syntax, unit tests, package manifest validation, shell syntax, index smoke tests, and `git diff --check` pass in the available environment.
- Rust workspace, Clippy, and exact-kernel `.ko` compilation remain validation gates for CI or a matching build machine because the local environment lacks `cargo` and target kernel headers.
- Bootable ISO, Secure Boot, installer behavior, hardware compatibility, and production malware review remain explicitly out of scope for this milestone.

## v0.1.1 — 2026-09-03

This maintenance release hardens the ISO release path and makes the project version explicit.

- Added a canonical `VERSION` file set to `0.1.1`.
- Embedded the Datya version in the ISO build metadata.
- Added versioned ISO filenames to release bundles.
- Added GitHub tag/version consistency checks to prevent mismatched releases.
- Expanded CI validation for the Calamares setup script and release builder.
- Re-ran the Rust, C++, Python, shell, manifest, and unit-test suites; all current checks pass.

This remains a development release until ISO boot, installer behavior, Secure Boot, and target hardware validation are completed.
