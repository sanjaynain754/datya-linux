# Datya Defensive Hardening Design

## Scope and boundary

Datya Linux will strengthen boot trust, reduce kernel attack surface, and make tampering visible. It will not include anti-forensics, log wiping, covert persistence, monitoring evasion, identity hiding, or mechanisms intended to make activity untraceable. Security tooling must preserve evidence and support authorized incident response.

## Secure Boot trust chain

The release image uses a documented chain: platform firmware verifies a Datya-signed first-stage loader; the loader verifies a signed kernel and initramfs; the kernel enforces signed modules; package metadata and updates are verified against a release key. The platform owner may enroll an organization key or their own key, with recovery documentation and key rotation procedures.

Measured boot is complementary to Secure Boot. A TPM-backed measurement log can record firmware, loader, kernel, initramfs, and policy measurements for local attestation. Measurements should be exported only with explicit user consent and should be verifiable by the device owner. A failed measurement must enter recovery or warning mode rather than silently bypassing the trust policy.

## Kernel hardening profile

The Datya kernel profile should enable supported upstream protections such as module signature enforcement, kernel lockdown when Secure Boot is active, strict kernel pointer exposure settings, restricted access to debug interfaces, hardened usercopy, randomization, read-only-after-init data, and a minimized set of enabled drivers. Each change requires compatibility testing across x86_64, ARM64, and Raspberry Pi 5 hardware.

Hardening must not silently break recovery. Datya should ship a signed recovery kernel or recovery environment, a documented rollback path, and a clear indicator when a user has selected a weaker compatibility profile.

## Defensive kernel modules

Kernel modules should be kept as small as possible and preferably replaced by upstream tracepoints, audit rules, or a privileged-but-confined user-space collector. Where a module is necessary, it must be signed, version-matched to the kernel, built reproducibly, and limited to observation or explicit policy enforcement.

A defensive module may emit tamper-evident events for module load/unload, credential transitions, policy changes, protected-file writes, debug-interface activation, and unusual persistence attempts. It must not delete or rewrite logs, conceal processes, alter timestamps, hide network sockets, bypass security controls, or interfere with forensic collection.

## Tamper-evident event pipeline

Events should be written locally to journald or an append-only evidence store with monotonic sequence numbers, boot ID, timestamp source, event type, actor, object, and a hash-chain link to the previous record. The chain detects ordinary modification but is not proof against a fully privileged attacker; periodic TPM-backed sealing or export to a user-controlled offline destination can improve assurance.

Privacy remains local by default. The system should collect the minimum metadata needed for the selected profile, expose retention controls, and show which services can read the evidence. Redaction and export are user-controlled and must preserve an original immutable copy when incident-response mode is enabled.

## Recovery and incident response

On integrity failure, Datya should stop high-risk policy changes, show the measured-boot and module-signature reason, preserve available evidence, and offer a signed recovery environment. The user can boot a known-good image, compare measurements, rotate credentials from a clean device, and export an evidence bundle. Recovery must not erase the suspected system by default.

## Test gates

A release candidate is acceptable only after signed-boot verification, unsigned-module rejection, rollback testing, event-chain tamper detection, evidence-retention tests, recovery boot tests, and performance tests on target hardware. Claims must state exactly what is measured and what remains outside the trust boundary.
