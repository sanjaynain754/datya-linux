# Datya Linux Roadmap

## Phase 0 — Foundation

- Define threat model and security terminology.
- Establish Rust workspace and testing conventions.
- Build a read-only local activity collector.
- Decide an open-source license and code-of-conduct process.

## Phase 1 — Bootable prototype

- Produce a reproducible Debian-based x86_64 image.
- Add minimal desktop and server profiles.
- Add AppArmor policy set, encrypted-install support, and signed update configuration.
- Add a local event format with provenance, severity, confidence, and retention controls.

## Phase 2 — Security experience

- Add network/process correlation and explainable alerts.
- Add persistence and package-integrity checks.
- Add a reviewable policy editor and emergency recovery mode.
- Test boot, update, suspend, Wi-Fi, graphics, audio, and storage across target hardware.

## Phase 2A — Developer Workspace

The developer workspace is a supporting component of the cybersecurity product, not the primary goal. It will provide the terminal and toolchain needed by the workbench.

## Phase 2B — Cybersecurity Workbench

- Add Learn, Defend, Assess, and Research profiles with visible authorization boundaries.
- Add assessment scope files, target allowlists, rate limits, and local audit logs.
- Add process-to-network correlation, event timelines, evidence hashing, and report export.
- Ship offline training fixtures and a modular catalog of verified security capability groups.

## Phase 3 — ARM64 and release engineering

- Publish Raspberry Pi 5 image and ARM64 build pipeline.
- Add automated image tests, SBOM generation, signatures, and reproducibility reports.
- Establish a security disclosure process and independent review.

## Phase 4 — Android evaluation

- Select supported Android hardware and boot strategy.
- Prototype delivery method with clear isolation boundaries.
- Port only stable, documented interfaces; do not promise universal Android compatibility.

A milestone is complete only when its security behavior, limitations, rollback path, and test results are documented.
