# RustScan Integration

Datya Linux integrates RustScan 2.4.1 as an **opt-in security-lab capability**. The pinned artifacts come from the official RustScan GitHub release rather than an unverified floating download. The upstream project identifies RustScan as GPL-3.0 licensed and documents Debian release assets, Cargo builds, Nmap integration, and the effect of open-file limits on scanning.[1] [2]

## Lifecycle

| Stage | Datya status |
|---|---|
| Catalogued | Yes, in `profiles/catalog.toml` |
| Metadata verified | Yes, exact amd64/arm64 release-asset hashes and sizes are recorded |
| Packaged | The ISO build hook installs the pinned binary after checksum verification |
| Tested | Dry-run, scope, confirmation, hash-chain, and daemon-route tests pass |
| Profile available | Yes, through the `security-lab` network pack |
| Enabled by user | No; no startup service or automatic scan is created |

## Safety behavior

RustScan is a network-capable tool. Datya therefore requires an authorized target, defaults to dry-run, requires the `--confirm` operator gate for execution, limits timeout and captured output, uses a fixed executable path without shell interpretation, and records a local hash-chain action event. The adapter does not automatically pipe results into Nmap. An explicit separate user action and separate policy decision would be required for any Nmap follow-up.

The ISO build hook only installs the binary. It does not execute RustScan, create a systemd service, add a background timer, or run a scan during first boot. The `security-lab` pack is catalogue metadata and does not imply that a scan is automatically enabled.

## Daemon usage

The control daemon starts in dry-run mode:

```text
scope add example.org
run rustscan-network-scan example.org
```

Expected result:

```json
{"schema":"datya.action.v1","tool":"rustscan","target":"example.org","mode":"dry-run","status":"planned"}
```

Execution requires both an authorized scope and an explicit mode/confirmation sequence:

```text
scope add 192.0.2.10
mode execute
run rustscan-network-scan 192.0.2.10 --confirm
```

Only scan hosts, networks, and systems for which the operator has clear permission. Datya’s scope check is a safety control, not a legal authorization.

## Pinned artifact metadata

| Architecture | Upstream asset | SHA-256 |
|---|---|---|
| amd64 | `x86_64-linux-rustscan.tar.gz.zip` | `f3a4365d939e3b81f25ba8c37852ce9ac9e938c3cc882c5b3e6fff6152c740be` |
| arm64 | `aarch64-linux-rustscan.zip` | `4f49103e2dfc9e9709a36da2cd61f1f81613f8d0a203307f750439fc3ce39eae` |

The package manifest records these values and strict validation passes only when the artifact hashes are valid. The ISO hook fails closed if download or checksum verification fails.

## References

[1]: https://github.com/bee-san/RustScan "Official RustScan repository and GPL-3.0 license"
[2]: https://github.com/RustScan/RustScan/wiki/Installation-Guide "Official RustScan installation guide"
[3]: https://github.com/bee-san/RustScan/releases/tag/2.4.1 "Pinned RustScan 2.4.1 release assets"
