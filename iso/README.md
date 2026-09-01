# Datya Linux Debian ISO Builder

This directory contains the first Debian `live-build` configuration for a reproducible Datya Linux live image. It creates an intentionally small cybersecurity-oriented base with AppArmor, encrypted-storage tooling, NetworkManager, local build tooling, and visible Datya policy markers. It does not yet install the Guardian kernel module or all 60+ security tools; those must be added as signed, versioned packages after their adapters and policies are reviewed.

## Build

Run on a Debian/Ubuntu build host with root access:

```bash
sudo apt-get update
sudo apt-get install --yes live-build debootstrap squashfs-tools xorriso \
  grub-pc-bin grub-efi-amd64-bin grub-efi-arm64-bin mtools dosfstools
sudo ./build-datya-iso.sh amd64 trixie
```

The script supports `amd64` and `arm64` as build profiles. ARM64 boot is hardware-specific; Raspberry Pi 5 requires a board-tested boot artifact and firmware flow rather than assuming that a generic hybrid ISO will boot directly.

## Reproducibility and release checks

Set `SOURCE_DATE_EPOCH` to a fixed UTC timestamp. For a release build, pin the Debian mirror to a dated snapshot, verify signed Release metadata, record the exact live-build and host package versions, generate an SBOM, and compare the image hash with an independent rebuild. Do not publish signing private keys in this repository.

Secure Boot signing is a separate release step. Sign the boot chain, kernel, initramfs, and any out-of-tree modules with an owner-controlled release key, then publish the corresponding certificate and verification instructions. A build completing successfully is not evidence that the image is secure; it must pass boot, package, policy, recovery, and hardware tests.

## Planned additions

The next ISO iteration should add a signed Datya package repository, the Guardian daemon, the C++ control daemon, a desktop profile, scope-controlled tool adapters, and a tested recovery environment. Tool packages should be optional profiles so users can customize the image without receiving unnecessary capabilities.
