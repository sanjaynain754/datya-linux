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
