# Changelog

## v0.1.1 — 2026-09-03

This maintenance release hardens the ISO release path and makes the project version explicit.

- Added a canonical `VERSION` file set to `0.1.1`.
- Embedded the Datya version in the ISO build metadata.
- Added versioned ISO filenames to release bundles.
- Added GitHub tag/version consistency checks to prevent mismatched releases.
- Expanded CI validation for the Calamares setup script and release builder.
- Re-ran the Rust, C++, Python, shell, manifest, and unit-test suites; all current checks pass.

This remains a development release until ISO boot, installer behavior, Secure Boot, and target hardware validation are completed.
