# Security Policy

Datya Linux is a security-focused, freedom-first project. We welcome responsible reports about vulnerabilities in the source tree, build system, ISO, package metadata, sandbox profiles, daemon adapters, kernel integration, and release infrastructure.

## Reporting a vulnerability

Please report security issues privately to **sanjaynain754@users.noreply.github.com** or through [GitHub private vulnerability reporting](https://github.com/sanjaynain754/datya-linux/security/advisories/new). Do not open a public issue for an unpatched vulnerability, include live credentials, or publish exploit details before maintainers have had a reasonable opportunity to investigate.

Your report should include the affected commit, release or ISO checksum, component and file, a concise description of impact, reproduction steps, expected and observed behavior, and any safe mitigation. For hardware-dependent issues, include the device model, firmware version, kernel version, architecture, and exact image checksum.

## Response process

Maintainers will acknowledge a report when practical, reproduce it in an isolated environment, assess severity and affected releases, coordinate a fix or mitigation, and publish a security advisory when disclosure is appropriate. We may ask for additional information or request that sensitive details remain private while a fix is prepared.

Datya Linux is an engineering-stage distribution. The project does not promise a fixed response time, a production security guarantee, or support for every device. A report is still valuable even when the issue affects only an experimental profile or an unverified hardware target.

## Scope and safe testing

Only test systems and networks for which you have explicit authorization. Do not attempt denial-of-service testing, data destruction, persistence, credential theft, privacy-invasive tracking, or access to another person’s data. The repository’s dry-run, scope, confirmation, sandbox, and evidence controls are safety mechanisms; they do not grant permission to test third-party systems.

## Supply-chain and release reports

Reports about tampered release assets, checksum mismatches, dependency confusion, signing-key exposure, leaked credentials, or unsafe build instructions should be treated as security reports and sent privately through the channels above.

## Recognition

With the reporter’s permission, Datya may credit responsible disclosures in the relevant advisory or changelog. Reporters may remain anonymous.
