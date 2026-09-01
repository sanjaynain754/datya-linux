# Datya Linux Threat Model

## Security objective

Datya Linux should help a user detect and understand unexpected activity while reducing unnecessary data collection. It is not an anonymity system and cannot guarantee that a compromised endpoint, network observer, malicious website, or hardware vendor is unable to observe activity.

## Threats in scope

- Unwanted telemetry from the operating system or preinstalled applications.
- Suspicious outbound connections, unexpected listeners, and persistence mechanisms.
- Tampered packages, unsigned updates, or compromised build infrastructure.
- Excessive privileges and silent access to camera, microphone, removable media, or sensitive files.
- Local attackers attempting to hide changes or escalate privileges.
- Misleading security alerts that train users to ignore real warnings.

## Out of scope for the first release

- Detecting every commercial tracker or advanced nation-state implant.
- Proving that a remote server is benign based only on its IP address or certificate.
- Protecting a device whose firmware, boot chain, or physical hardware is already compromised.
- Providing guaranteed anonymity or untraceability.

## Security controls

| Risk | Initial control | Later work |
|---|---|---|
| Hidden telemetry | No telemetry by default; package and service inventory | Reproducible network-policy tests |
| Unexpected network activity | Read-only local socket inventory and explainable alerts | DNS/process correlation, policy enforcement |
| Package tampering | Signed repositories and update verification | Reproducible builds and independent attestations |
| Privilege abuse | AppArmor, least privilege, separate service accounts | Capability-based service design |
| Data theft | Encryption support and explicit removable-media policy | Fine-grained file access auditing |
| Alert fatigue | Severity, confidence, provenance, and user feedback | Tested detection rules and benchmarks |

## Security principles

1. **Evidence before accusation:** report observable facts and confidence, not unsupported claims.
2. **Fail safely:** collectors should be read-only by default; blocking must be an explicit, reversible policy action.
3. **Minimize collected data:** retain event metadata only as long as configured by the user.
4. **Make tampering visible:** logs and policy changes should have integrity protections, while acknowledging that a fully privileged attacker can alter a live system.
5. **Publish limitations:** each release must document what it can and cannot detect.
