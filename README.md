# Datya Linux

**Datya Linux** is an open, security-first **general-purpose Linux distribution** with a built-in cybersecurity workbench for ethical hackers, blue teams, incident responders, security learners, researchers, developers, administrators, and everyday users using modern laptops, desktops, workstations, Raspberry Pi 5, and other capable x86_64/ARM64 systems.

The project aims to make privacy and system activity understandable without hiding the controls from the user. Datya will ship with no telemetry by default, transparent security signals, verifiable updates, and a modular design that people can customize and redistribute. It is a general-purpose operating system, not a guarantee that every use or outcome can be controlled by its maintainers.

## Principles

- **Privacy by default:** no hidden telemetry, analytics, or unnecessary network services.
- **Visible activity:** network, privilege, persistence, and integrity events should be explainable to the user.
- **Secure foundations:** minimal installation, signed updates, encrypted storage support, sandboxing, least privilege, and hardened defaults.
- **Open customization:** themes, packages, policies, services, and images can be changed by users and downstream communities.
- **Verifiable builds:** reproducible build targets and published source/configuration are part of the security model.
- **Honest security:** no claim of perfect anonymity or absolute protection; risks and limitations are documented.

## Current status

This repository contains the initial design documents and a small Rust prototype for collecting local network activity signals. It is **not yet a complete Linux distribution** and should not be used as a security boundary or production intrusion detector.

GitHub Actions now checks Rust formatting/tests/clippy, the C++17 daemon build, shell syntax, private-key safeguards, and Datya policy markers on every push and pull request.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Project scope](docs/PROJECT_SCOPE.md)
- [Four-user collaboration](docs/COLLABORATION.md)
- [Collaboration transport protocol](docs/COLLABORATION_PROTOCOL.md)
- [Feature parity and modular profiles](docs/FEATURE_PARITY.md)
- [Security audit](docs/SECURITY_AUDIT.md)
- [Package ecosystem](docs/PACKAGE_ECOSYSTEM.md)
- [Debian sync tool](tools/datya-debian-sync.py)
- [Threat model](docs/THREAT_MODEL.md)
- [Developer environment](docs/DEVELOPER_ENVIRONMENT.md)
- [Cybersecurity Workbench](docs/CYBERSECURITY_WORKBENCH.md)
- [Secure Boot and kernel sensor](docs/SECURE_BOOT.md)
- [Defensive hardening](docs/DEFENSIVE_HARDENING.md)
- [Debian ISO builder](iso/README.md)
- [Roadmap](docs/ROADMAP.md)
- [Contributing](CONTRIBUTING.md)
- [Dashboard prototype](dashboard/README.md)
- [Collaboration server](tools/datya-collab-server.py)
- [Collaboration token issuer](tools/issue-collab-token.sh)

## Prototype

The `guardian` crate is intentionally read-only and unprivileged. It reports locally visible TCP sockets from procfs when available. It does not block traffic, inspect packet contents, deanonymize users, or claim to identify every tracking attempt.

The `datya-sensor` crate is the first cybersecurity system-sensor layer. It reads kernel release, architecture, OS release, CPU model, memory, firmware product information, and Secure Boot state from local procfs/sysfs sources and emits a `datya.system.v1` record. It performs no kernel modification, privilege escalation, packet interception, or remote reporting. Missing firmware fields are reported as `null`, not guessed.

The `datya-control-daemon` is the keyboard-first general-purpose workbench orchestrator. It exposes a modular catalog of 77 security capabilities, supports scope management, defaults to dry-run planning, and blocks network-capable actions unless the target is explicitly authorized. The `datya-collab-session` crate provides a four-participant shared audit core for proposals, approvals, command state, and bounded result summaries. Individual tool adapters will be added only with their own permission, timeout, rate-limit, and evidence policies.

The `datya-tool-adapters` crate provides the adapter policy layer. It executes only fixed allowlisted binaries without a shell, supports dry-run and execute modes, validates scoped targets, enforces a minimum interval between runs, applies a timeout, caps captured output, and writes evidence to a local temporary path. Read-only adapters currently cover sockets, routes, DNS, HTTP headers, process posture, kernel posture, firewall status, and AppArmor status; additional tools must be added deliberately with a reviewable policy.

Optional capability profiles are catalogued in `profiles/catalog.toml` and can be reviewed without changes using `tools/datya-profile.sh --dry-run <profile>` or installed from the current Debian repositories. Datya does not mix Kali repositories into its Debian base or claim that every Linux feature is installed; each capability must carry provenance, license, architecture, privilege, network, test, and uninstall metadata.

The read-only `tools/datya-security-audit.sh` checks filesystem permissions, ownership, SUID/SGID, writable paths, sensitive files, symlinks, ACLs, and available authentication-log indicators. It supports text and JSON reports and severity-based exit codes; it does not modify the system or prove historical access.

The curated Debian package manifest is `packages/manifest.json`. Validate its structure with `python3 tools/verify-package-manifest.py packages/manifest.json`; release automation must use `--strict` only after real signed artifact checksums and review metadata replace the catalogued placeholders.

`tools/datya-debian-sync.py` validates signed Debian `InRelease` metadata, package-index hashes/sizes, and curated package availability without installing packages. Its systemd service/timer templates support reviewed periodic metadata reports.

The `cpp-control` directory contains a C++17 control-daemon reference implementation. It exposes the 77-tool catalog, keeps actions in dry-run planning mode, requires an authorized scope for network tools, and writes local append-only hash-chained events. Build it with CMake and OpenSSL: `cmake -S cpp-control -B build && cmake --build build`. Run `./build/datya-control /var/lib/datya/events.log`, then use `scope add <target>`, `run <tool> <target>`, and `verify`.

```bash
cargo run -p guardian
cargo test --workspace
```

Interactive prototype:

```text
datya> tools
datya> scope add 10.10.0.10
datya> run dns-inspect 10.10.0.10
datya> quit
```

The first Developer Workspace runner prototype is available at `tools/datya-runner.py`. It emits one JSON result containing the command, profile, output, exit code, duration, and network policy. For example: `python3 tools/datya-runner.py --profile safe -- python3 -c 'print("hello")'`. The runner applies local resource limits, but it is not yet a complete sandbox; real network isolation requires a configured container or virtual machine.

## Target platforms

The first supported targets are **x86_64** and **aarch64**. Raspberry Pi 5 and modern PCs/laptops are in scope; low-end hardware optimization is not a primary project goal. Apple hardware support will depend on upstream Linux support and device-specific firmware/driver work.

## License

The licensing model is not finalized yet. Until it is, contributions should preserve the project's open-source and transparent intent.
