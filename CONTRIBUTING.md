# Contributing to Datya Linux

Datya Linux is intended to be open and customizable. Contributions are welcome in code, documentation, testing, packaging, hardware validation, accessibility, and security review.

## Before submitting work

Read the architecture and threat model. Prefer small, reviewable changes. Security-sensitive changes must explain the threat addressed, the trust assumptions, the data collected, and how a user can disable or undo the behavior.

## Development

New privileged or long-running system services should be written in Rust unless a lower-level interface requires C. Keep collectors read-only unless an explicit policy-enforcement design has been reviewed. Do not add telemetry, remote reporting, opaque binaries, or undisclosed network endpoints.

Run the test suite before opening a pull request:

```bash
cargo fmt --all -- --check
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace
```

Please report suspected vulnerabilities privately through a security contact once one is established; do not publish exploit details before maintainers can assess them.
