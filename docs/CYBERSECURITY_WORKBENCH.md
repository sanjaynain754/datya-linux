# Datya Cybersecurity Workbench

## Product goal

Datya Linux is primarily a **cybersecurity operating system** for security learners, blue teams, authorized penetration testers, incident responders, and researchers. The developer toolchain exists to support this mission; it is not the product's center.

The workbench should make an ethical hacker's workflow clear and reproducible: define an authorized scope, discover assets, inspect services, validate findings in a controlled lab, collect evidence, write a report, and clean up. The interface must keep authorization and scope visible throughout the workflow.

## Operating modes

| Mode | Purpose | Default behavior |
|---|---|---|
| Learn | Training labs and CTF-style exercises | Offline fixtures and intentionally vulnerable targets only |
| Defend | Monitoring and incident response | Read-only collection, local alerts, evidence preservation |
| Assess | Authorized security assessment | Scope file required; rate limits, audit log, and explicit target confirmation |
| Research | Malware or exploit research | Disposable VM, no host mounts, no unrestricted network |

Datya must never imply that a tool is safe merely because it is installed. Before an assessment begins, the user should provide a signed or locally stored scope definition containing permitted targets, time window, contact, rate limit, and excluded systems. The workbench displays this scope before each action and records the result locally.

## Capability groups

The initial image should be modular rather than shipping every tool by default. Profiles can install and update capability groups such as asset inventory, DNS and certificate inspection, packet and flow analysis, web testing, wireless diagnostics, vulnerability validation, digital forensics, reverse engineering, cloud/container assessment, and defensive detection engineering.

Tools should come from verified, signed repositories. Every tool page should state what permissions it needs, whether it sends network traffic, what data it stores, and how to remove it. The system should offer a local SBOM and package provenance view.

## Real-time visibility

Guardian should correlate process, user, executable hash, socket, DNS request, certificate, and policy event when data is available. Alerts should show evidence and confidence: for example, an unknown process opened a connection to an unapproved target, or a package changed a monitored executable. Datya should not label an IP address as malicious solely because it appears on a list, and it should distinguish an authorized scan from unexpected activity.

The workbench should provide a timeline, terminal output, packet/flow summaries, findings, and an evidence vault. Evidence collection must be local by default, integrity-protected, time-stamped, and exportable to common report formats. Retention is controlled by the user.

## Safety boundaries

Datya supports lawful, authorized security work. It should help users practice against local labs, CTF targets, and systems for which they have permission. It should not silently scan arbitrary public targets, bypass access controls, steal credentials, persist on third-party systems, or hide unauthorized activity. High-impact actions require an explicit scope and a second confirmation inside the workbench.

These boundaries are product safety controls, not a substitute for law, contracts, or responsible disclosure.

## First cybersecurity MVP

1. Create a scope file format and display it before an assessment.
2. Add Guardian process-to-network correlation and a local event timeline.
3. Ship a Learn profile with offline intentionally vulnerable fixtures.
4. Add assessment command wrappers that enforce target scope and rate limits.
5. Add evidence hashing and a local assessment report generator.
6. Test the workbench on x86_64 and ARM64, including Raspberry Pi 5.
