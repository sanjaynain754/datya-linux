# Datya Linux progress graph data

Status is a repository-grounded maturity assessment, not a percentage completion claim.

| Status | Count |
|---|---:|
| Complete / tested | 1 |
| Working prototype | 6 |
| Partial / validation pending | 3 |
| Design documented | 1 |
| Planned | 1 |

| Workstream | Status | Evidence / next gap |
|---|---|---|
| Nmap policy adapter | Complete / tested | Implemented, unit-tested, policy-controlled |
| Explicit root-control API | Working prototype | Rust validation/audit boundary; no privilege escalation |
| Indexed module repository | Working prototype | Catalog structure and index CLI with initial modules |
| Kernel Guardian sensor | Working prototype | Read-only exec/socket tracepoints; exact-kernel .ko build pending |
| Package manager planning CLI | Working prototype | Search, info, verify, install/remove plans; no transaction executor yet |
| Sandbox launcher | Working prototype | Safe/project/lab profiles; fail-closed without Bubblewrap |
| Security Center dashboard | Working prototype | Interactive local dashboard UI; backend event wiring pending |
| Bootable ISO / Secure Boot | Partial / validation pending | Build/release scripts and validation plans exist; hardware verification pending |
| Collaboration sessions | Partial / validation pending | Four-operator transport and access-control tests exist; hardening continues |
| Repository baseline / CI | Partial / validation pending | CI and policy checks exist; Rust/kernel builds remain environment-dependent |
| Privacy / cryptographic customization | Design documented | Architecture and policy defined; implementation roadmap item |
| Hardware / CPU optimization | Planned | Benchmark matrix and platform tuning are next-phase work |
