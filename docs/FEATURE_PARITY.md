# Datya Linux Feature Parity and Modular Profiles

Datya will not copy Kali Linux, Debian, Ubuntu, Fedora, Arch, or every Linux distribution wholesale. That would be technically unmaintainable, would mix incompatible repositories, and could violate project licenses, trademarks, attribution requirements, or security update assumptions. Kali's official documentation describes its own approach as **metapackages**: selectable dependency groups such as core, desktop, wireless, forensics, reporting, and labs. Datya adopts the useful idea of selectable profiles while keeping its own base, policies, names, and packaging provenance.

## Profile strategy

The base image remains general-purpose and privacy-first. Users opt into capability profiles:

| Profile | Purpose | Default posture |
|---|---|---|
| `desktop` | Daily computing, development, accessibility, and administration | No assessment tools enabled |
| `security-observe` | Local posture, logs, network visibility, and integrity evidence | Read-only and dry-run |
| `security-lab` | Authorized lab adapters and disposable test environments | Explicit scope and isolation required |
| `forensics` | Evidence collection and timeline workflows | Read-only source mounts |
| `wireless-hardware` | Hardware, Bluetooth, SDR, and Wi-Fi capability packages | Hardware permissions visible |
| `cloud-code` | SAST, dependency, SBOM, IaC, and container review | Local evidence by default |
| `learning` | Training labs and guided exercises | Isolated targets only |

A profile is not permission to attack a target. Network-capable actions still require explicit scope, and execution remains subject to the adapter policy, dry-run default, rate limit, timeout, output cap, and local audit log.

## Integration rules

Every imported capability must have a source URL, package name/version, license, maintainer, checksum/signature provenance, privilege declaration, network behavior, supported architectures, test status, and uninstall path. Prefer Debian packages and upstream signed repositories. Do not add Kali repositories to a Debian-based Datya image as a shortcut; repository mixing can create dependency and trust failures.

The catalog may describe capabilities before an adapter is implemented. A catalog entry is not a claim that the binary is installed or production-ready. Datya's release notes must distinguish **catalogued**, **packaged**, **tested**, and **enabled** states.

Reference: [Kali Linux Metapackages](https://www.kali.org/docs/general-use/metapackages/) explains the upstream metapackage model and category grouping.
