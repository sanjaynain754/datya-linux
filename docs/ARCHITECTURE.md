# Datya Linux Architecture

## Direction

Datya Linux will be a Debian-derived distribution with a small, auditable base and a clearly separated security layer. Debian is selected for its broad hardware support, mature package ecosystem, and reliable security maintenance. Datya-specific components should remain modular so that users and downstream distributions can replace them.

## Layers

1. **Firmware and boot:** UEFI/ARM boot support, Secure Boot where practical, measured boot integration, and a documented recovery path.
2. **Kernel:** upstream Linux with a small, documented hardening configuration. Security changes must be reviewable and benchmarked rather than blindly enabled.
3. **Base OS:** minimal Debian packages, AppArmor profiles, automatic security updates, signed package metadata, and encrypted-storage tooling.
4. **Policy and identity:** declarative system policy, least-privilege defaults, explicit consent for sensitive capabilities, and a local audit log.
5. **Guardian services:** read-only collectors and policy evaluators for network, process, persistence, authentication, and integrity signals. A separate UI can consume events.
6. **User environments:** desktop and server profiles, with customization through packages, themes, policies, and image build configuration.

## Technology choices

- **Rust** for new security-sensitive user-space services: memory safety, strong typing, and good static-linking/tooling options.
- **C** only where required by kernel, boot, libc, or mature low-level interfaces.
- **Go** for operational tooling when fast iteration and simple distribution are more valuable than tight system integration.
- **Shell/Python** for build and test orchestration, not for privileged long-running security services.

## Activity transparency

The system should present event provenance, not vague accusations. For example, an alert should identify the process, executable path, user, destination, DNS context when available, and reason for suspicion. A connection is not automatically tracking: the UI must distinguish ordinary service traffic, user-requested traffic, blocked policy violations, and uncertain signals.

The first prototype reads procfs without root and reports TCP socket metadata. Future collectors may use eBPF, auditd, fanotify, or kernel security hooks only after privacy, performance, and maintenance costs are understood.

## Customization contract

All defaults should be represented as versioned configuration. Users may select profiles, replace policy files, build custom images, add repositories, and disable non-essential services. Security-critical defaults should be changeable only with a clear warning and an audit entry—not made impossible to customize.

## Android direction

Android is a future distribution target, not a simple launch layer. The project will first stabilize the Linux architecture and interfaces, then evaluate Android-compatible delivery through a supported device image, container/VM approach, or a downstream Android integration. Device boot chains, drivers, sandboxing, licensing, and update trust must be assessed separately.
