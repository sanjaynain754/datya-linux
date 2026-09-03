# Datya Linux Debian ISO Builder

This directory builds the first installable Datya Linux desktop image from Debian live-build. The default image targets `amd64` and `arm64`, boots into XFCE with LightDM, includes the local Datya dashboard launcher, and exposes an interactive Calamares installer. The installer is deliberately not unattended: users must review partitioning, locale, keyboard, user creation, and bootloader settings before committing an installation.

## Build

Run on a Debian/Ubuntu build host with live-build, root access, and sufficient disk space:

```bash
sudo apt-get update
sudo apt-get install --yes live-build debootstrap squashfs-tools xorriso \
  grub-pc-bin grub-efi-amd64-bin grub-efi-arm64-bin mtools dosfstools calamares
sudo ./build-datya-iso.sh amd64 trixie
```

The ISO is written under `iso/binary/live-image-*.iso` by live-build. Review `SHA256SUMS`, boot it in a virtual machine, and verify the installer and desktop before distributing it.

## Release status

The build configuration is an installable desktop prototype, not yet a signed stable release. Release maintainers must pin and verify Debian `InRelease` metadata, replace catalogued package placeholders with real checksums, provide signed Datya kernel-module artifacts, test Secure Boot, and validate hardware on representative laptops, PCs, and Raspberry Pi 5 boards. ARM64 ISO boot is hardware-specific and must not be advertised as universal.

## Desktop integration

`config/hooks/normal/0950-configure-desktop.hook.chroot` configures XFCE and LightDM, disables guest login, sets the graphical default target, and writes `/etc/datya/desktop`. The dashboard is copied to `/usr/share/datya/dashboard.html`; its launcher opens the local file and does not send telemetry. `calamares.desktop` starts the interactive installer through `pkexec`.

The ISO build currently compiles the C++ reference daemon and experimental Guardian module in a chroot. A production stable release must fail closed unless the module is signed with the project's trusted key and independently verified.

## Automated release bundle

`build-release.sh` is the end-to-end orchestrator. It runs Rust, C++, Python, shell, manifest, and Calamares checks; invokes the Debian live-build; copies the ISO; creates a Git source snapshot and release metadata; writes a complete `SHA256SUMS`; and verifies the resulting bundle. It does not upload, publish, or install anything.

```bash
sudo ./iso/build-release.sh amd64 trixie
```

The output is `releases/trixie-amd64/`. To add a detached GPG signature, set `DATYA_RELEASE_SIGNING_KEY` to a local key identifier. `DATYA_SKIP_TESTS=1` is available only for controlled debugging when build dependencies are unavailable. A successful script run is not by itself a stable-release approval: the release gates described above still require signed package metadata, real package checksums, Secure Boot validation, installer testing, and hardware testing.

## Calamares verification

The Datya Calamares configuration is installed under `/etc/calamares` in the image. The verified workflow presents welcome, locale, keyboard, partition, user, and summary pages, then executes the reviewed installation jobs and shows a finished page. `prompt-install: true` requires an explicit confirmation before disk changes.

The partition policy uses a 512 MiB EFI recommendation, ext4 as the default filesystem, optional ext4/btrfs/xfs choices, optional swap, LUKS2 support, manual partitioning, and an initial `none` choice so the user cannot accidentally proceed without selecting a disk action. These settings must still be tested in a disposable virtual machine before any real disk is used.
