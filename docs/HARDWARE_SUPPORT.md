# Datya Linux v0.1.3 Hardware and Device Support

## How to read this document

This document distinguishes **minimum possible**, **minimum practical**, **recommended**, and **verified**. Debian’s installer documentation gives lower general-purpose figures, but Datya v0.1.3 includes an XFCE desktop, a large security-workbench package set, a browser, Calamares, Rust tooling, and local evidence components. Datya therefore needs more headroom than a minimal Debian text installation.

## Requirements at a glance

| Category | Minimum possible for experimentation | Minimum practical for Datya v0.1.3 | Recommended for a good experience |
|---|---:|---:|---:|
| CPU | 64-bit x86_64 processor, 2 threads | 2 modern x86_64 cores | 4 or more modern x86_64 cores |
| Memory | 2 GiB with swap, limited tools | 4 GiB RAM plus 4 GiB swap | 8 GiB RAM or more |
| Storage | 20 GiB available, limited package growth | 30 GiB available | 60 GiB or more, especially for tool caches and evidence |
| Installation media | 8 GiB USB drive | 16 GiB USB drive | 16 GiB or larger, verified before writing |
| Firmware | Legacy BIOS may boot the current image | UEFI or legacy BIOS with USB boot | UEFI with Secure Boot capability, pending Datya signing support |
| Network | Not required for live boot | Recommended for package updates and downloads | Wired Ethernet or a supported Wi-Fi adapter |
| GPU/display | VGA-compatible display | Hardware capable of XFCE | Modern integrated or discrete GPU with Debian-supported driver |

Debian’s official Trixie amd64 guide lists 1 GiB RAM and 10 GiB disk as recommended minimums for a desktop installation, while also noting that graphical installers require more memory and that those figures assume a non-live image and swap. Datya’s higher practical recommendation accounts for its live image, XFCE session, browser, security tools, package cache, and evidence files.[1] [2]

## Supported and target device classes

| Device class | v0.1.3 status | Notes |
|---|---|---|
| Modern Intel or AMD desktop PC | Primary target | The published ISO is amd64 and is intended for this class. Validate GPU, Wi-Fi, and Secure Boot behavior on the specific model. |
| Modern Intel or AMD laptop | Target, not universal guarantee | Basic boot is expected where Debian Trixie supports the hardware. Suspend, fingerprint readers, special keys, hybrid graphics, and Wi-Fi require model-specific testing. |
| x86_64 virtual machine | Smoke-tested path | The ISO was inspected as an ISO-hybrid and run non-destructively in QEMU snapshot mode. Graphical installer interaction still requires a manual VM test. |
| Raspberry Pi 5 and other ARM64 boards | Future/experimental target | The project contains arm64 package metadata and build intent, but v0.1.3 does not publish an arm64 ISO or claim board-level validation. Board firmware, UEFI, GPU, Wi-Fi, storage, and bootloader support vary. |
| Apple Silicon Macs | Not supported by this release | No Apple Silicon image, firmware path, or hardware validation is included. |
| 32-bit x86 PCs | Not supported | The v0.1.3 ISO is amd64. Debian Trixie treats i386 as a co-architecture rather than a normal new-installation target.[3] |
| Phones, tablets, Chromebooks, and embedded boards | Not supported by this release | Device-specific boot chains, firmware, drivers, and storage layouts require separate ports. |

Debian Trixie lists amd64 and AArch64 among its supported architectures, along with several other architectures. Datya v0.1.3 narrows the published artifact to amd64 while retaining arm64 as a development target; Debian architecture support therefore must not be mistaken for Datya hardware validation.[3]

## Installation safety requirements

Before installing to physical storage, back up personal files and confirm the target disk by model and size. Use a disposable VM first. Calamares is present as a live-desktop launcher, but the current engineering release does not silently install, partition, or erase disks. The user must explicitly review every partitioning choice.

Secure Boot is a design requirement for the final production distribution, but the v0.1.3 ISO is not yet signed with Datya production keys. A system configured to accept only trusted Secure Boot signatures may refuse this unsigned engineering image. Do not disable Secure Boot on a managed or security-sensitive device without understanding the consequence.

## What still needs device testing

The following items remain open for a production hardware matrix: UEFI Secure Boot signing and verification; Intel and AMD graphics acceleration; NVIDIA driver choices; Wi-Fi and Bluetooth firmware; suspend and resume; encrypted installation; disk encryption recovery; ARM64 board boot; external monitors; audio; camera; fingerprint readers; Thunderbolt and USB4; and recovery from interrupted package transactions.

## References

[1]: https://www.debian.org/releases/trixie/amd64/ch03s04.en.html "Debian Trixie amd64: Meeting Minimum Hardware Requirements"
[2]: https://www.debian.org/releases/trixie/amd64/ "Debian Trixie Installation Guide for amd64"
[3]: https://www.debian.org/releases/trixie/ "Debian Trixie Release Information and supported architectures"
