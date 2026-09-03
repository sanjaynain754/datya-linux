# Datya Linux eight-step implementation status

This report records the current state after the Verified Foundation work. A step is only marked complete when its repository implementation and available validation evidence both exist.

| Step | Area | Status | Evidence |
|---:|---|---|---|
| 1 | Rust toolchain and CI | Complete | `cargo fmt --all -- --check`, workspace build/test, and workspace Clippy pass on the installed stable toolchain. |
| 2 | Guardian kernel build | Partial | Source compiles against Linux 6.17 headers through C compilation, but `modpost` cannot link the external module because the target tracepoint symbols are not exported. Primary userspace tracefs/eBPF-compatible collector is implemented instead. |
| 3 | Package transaction engine | Complete prototype | `datya-pkg` supports verified plans, record-only install/remove transactions, state snapshots, exact acknowledgement, and rollback. It does not invoke apt/dpkg yet. |
| 4 | Strict manifest cleanup | Blocked/pending review | Existing manifest records use `metadata-verified` and `DEBIAN-COPYRIGHT-REVIEW-REQUIRED`. Strict validation correctly remains failing until maintainer/license review evidence is supplied. |
| 5 | Sandbox hardening | Complete prototype | Bubblewrap profiles fail closed without `bwrap`; available profiles drop capabilities, isolate namespaces, unshare network where applicable, and apply process/file limits. `power-user` remains explicit and unsandboxed. |
| 6 | Guardian-to-dashboard wiring | Complete prototype | Collector emits `datya.guardian.event.v1`; Guardian daemon accepts both raw kernel lines and collector JSON; local JSON alert output remains observe-only. |
| 7 | ISO/installer/recovery smoke test | Partial | Script syntax and live-build bootstrap pass. Auto/config recursion and Trixie security mirror defects were fixed. Full build currently hits the installed live-build version’s obsolete `/trixie/updates` security-suite behavior; boot, installer, and recovery cannot be claimed yet. |
| 8 | Performance baseline | Complete baseline harness | `tools/datya-benchmark.py` and `make benchmark` record architecture, kernel, CPU count, available memory, and repeated tool-launch latency. Target-image boot timing remains a required follow-up. |

## Current release interpretation

Datya is a strong source-level and prototype milestone with passing Rust and Python validation, but it is not yet a production-ready bootable operating-system release. The two release blockers are independent and concrete: package provenance/license review and a compatible live-build/security-suite path for Trixie. No unverified package or boot claim should be promoted to stable production status until those gates pass.

## Recommended next gates

First complete real Debian copyright/license review records and teach the strict validator to consume those records. In parallel, either upgrade live-build to a Trixie-aware release or add a tested, explicit security-source generation path that produces `trixie-security` rather than the obsolete `trixie/updates`. Then run the ISO in a VM, test installer and recovery, and capture boot/RAM/CPU/tool-launch results from that image.
