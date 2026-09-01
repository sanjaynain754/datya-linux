# Datya Linux

**Datya Linux** is an open, security-first **cybersecurity Linux distribution** for ethical hackers, blue teams, incident responders, security learners, and researchers using modern laptops, desktops, workstations, Raspberry Pi 5, and other capable x86_64/ARM64 systems.

The project aims to make privacy and system activity understandable without hiding the controls from the user. Datya will ship with no telemetry by default, transparent security signals, verifiable updates, and a modular design that people can customize and redistribute.

## Principles

- **Privacy by default:** no hidden telemetry, analytics, or unnecessary network services.
- **Visible activity:** network, privilege, persistence, and integrity events should be explainable to the user.
- **Secure foundations:** minimal installation, signed updates, encrypted storage support, sandboxing, least privilege, and hardened defaults.
- **Open customization:** themes, packages, policies, services, and images can be changed by users and downstream communities.
- **Verifiable builds:** reproducible build targets and published source/configuration are part of the security model.
- **Honest security:** no claim of perfect anonymity or absolute protection; risks and limitations are documented.

## Current status

This repository contains the initial design documents and a small Rust prototype for collecting local network activity signals. It is **not yet a complete Linux distribution** and should not be used as a security boundary or production intrusion detector.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Threat model](docs/THREAT_MODEL.md)
- [Developer environment](docs/DEVELOPER_ENVIRONMENT.md)
- [Cybersecurity Workbench](docs/CYBERSECURITY_WORKBENCH.md)
- [Secure Boot and kernel sensor](docs/SECURE_BOOT.md)
- [Roadmap](docs/ROADMAP.md)
- [Contributing](CONTRIBUTING.md)

## Prototype

The `guardian` crate is intentionally read-only and unprivileged. It reports locally visible TCP sockets from procfs when available. It does not block traffic, inspect packet contents, deanonymize users, or claim to identify every tracking attempt.

The `datya-sensor` crate is the first cybersecurity system-sensor layer. It reads kernel release, architecture, OS release, CPU model, memory, firmware product information, and Secure Boot state from local procfs/sysfs sources and emits a `datya.system.v1` record. It performs no kernel modification, privilege escalation, packet interception, or remote reporting. Missing firmware fields are reported as `null`, not guessed.

```bash
cargo run -p guardian
cargo test --workspace
```

The first Developer Workspace runner prototype is available at `tools/datya-runner.py`. It emits one JSON result containing the command, profile, output, exit code, duration, and network policy. For example: `python3 tools/datya-runner.py --profile safe -- python3 -c 'print("hello")'`. The runner applies local resource limits, but it is not yet a complete sandbox; real network isolation requires a configured container or virtual machine.

## Target platforms

The first supported targets are **x86_64** and **aarch64**. Raspberry Pi 5 and modern PCs/laptops are in scope; low-end hardware optimization is not a primary project goal. Apple hardware support will depend on upstream Linux support and device-specific firmware/driver work.

## License

The licensing model is not finalized yet. Until it is, contributions should preserve the project's open-source and transparent intent.
