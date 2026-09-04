# Datya Linux v0.1.3

Datya Linux v0.1.3 is a Debian Trixie amd64 live-image engineering release. It combines the freedom-first Security Workbench direction with a reproducible live-build path, Calamares-based installation entry point, local-only policy defaults, package provenance checks, sandbox profiles, Guardian collection, and a curated tool manifest.

> **Release status:** v0.1.3 is a validated engineering release, not a claim of universal hardware compatibility or production Secure Boot approval.

## What is included

The release includes the Debian Trixie live ISO builder, XFCE desktop integration, Calamares launcher, Datya dashboard launcher, local privacy and security policy markers, Trixie-compatible syslinux/rsvg/isohybrid handling, strict package-manifest verification, the modular package transaction engine, Bubblewrap sandbox profiles, Guardian userspace collection, and the existing Rust, C, Python, and shell components.

The package manifest contains 38 curated records. Each record has verified Debian artifact metadata, architecture information, uninstall metadata, and an exact-artifact copyright-file audit result. The Debian copyright file remains the authoritative source for the detailed license terms of each package.

## ISO artifact

| Property | Value |
|---|---|
| File | `iso/binary.hybrid.iso` |
| Base | Debian Trixie |
| Architecture | amd64 / x86_64 |
| Size | 856,686,592 bytes |
| SHA-256 | `94b85195d8f7eb7cb598abdd85ae01f695959a35dda45045f8854b4efd0a9416` |
| Volume ID | `DATYA_LINUX` |
| Installer entry point | Calamares launcher inside the live desktop |
| Desktop | XFCE |
| Boot format | El Torito BIOS plus MBR isohybrid |

Verify the embedded live-media files with:

```bash
cd iso/binary
sha256sum -c SHA256SUMS
```

Verify the complete ISO artifact with:

```bash
sha256sum iso/binary.hybrid.iso
```

## Validation completed

The ISO build completed successfully. The embedded live-media checksums returned `OK`; the SquashFS image was readable; xorriso reported a valid El Torito catalog and MBR isohybrid layout; the live kernel, initrd, filesystem, isolinux configuration, Calamares executable, dashboard launcher, and Datya policy files were present. A non-destructive QEMU run kept the ISO process alive for 45 seconds in snapshot mode. That check did not perform installation or write to a real disk.

The strict package manifest gate passed with 38 records:

```text
manifest valid: 38 package records; strict=True
```

The generic benchmark harness also completed. It recorded an average `true` command launch time of 0.817 ms over five repetitions on the build host. Boot-time measurement must be collected on target hardware because `systemd-analyze` is not available in the generic build environment.

## Security and ownership model

Datya does not silently block arbitrary user commands. Risk is surfaced through policy, scope, dry-run defaults, audit evidence, sandbox profiles, and explicit confirmation for destructive package actions. The v0.1.3 ISO does not include a hidden telemetry service. Network-capable security tools remain profile- and scope-oriented rather than auto-running at boot.

The installer must be tested in a disposable virtual machine before use on real storage. Users must make a verified backup before installation and must inspect Calamares partition choices themselves.

## Known limitations

The v0.1.3 artifact is amd64-only for this release. The repository retains arm64 package metadata and build intent, but an arm64 ISO was not built or hardware-tested for this release. Secure Boot signing and Secure Boot verification are not included in the current unsigned engineering artifact. Graphical desktop behavior, Wi-Fi, suspend/resume, GPU acceleration, installer partition workflows, recovery workflows, and device-specific firmware remain hardware-validation tasks.

## Source and release assets

Source code is published in the GitHub repository. The ISO is distributed as a release asset rather than committed into Git because it is a large generated binary. Always verify the SHA-256 value from the signed or otherwise trusted release announcement before writing the image to removable media.

## References

[1]: https://www.debian.org/releases/trixie/ "Debian Trixie Release Information"
[2]: https://www.debian.org/releases/trixie/amd64/ch03s04.en.html "Debian Trixie amd64: Meeting Minimum Hardware Requirements"
[3]: https://www.debian.org/releases/trixie/amd64/ "Debian Trixie Installation Guide for amd64"
