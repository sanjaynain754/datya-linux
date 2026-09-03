# Datya Linux v0.1.1: Real-Disk Installer and Secure Boot Validation Plan

**Author:** Manus AI  
**Status:** Proposed validation plan  
**Scope:** Datya Linux v0.1.1 on x86_64 PCs/laptops and Raspberry Pi 5 ARM64 targets

## Executive decision

Datya Linux should not be installed on a primary computer or a disk containing user data until the installer has passed three independent gates: destructive-install testing in a virtual machine, installation testing on a disposable physical disk, and Secure Boot testing with a recoverable key-enrollment procedure. The validation process must preserve an untouched recovery path, record evidence for every test, and stop automatically when partitioning, booting, signature verification, or rollback behavior differs from the expected result.

A successful test does not prove that Datya Linux is universally secure or compatible with every device. It establishes only that the tested ISO, hardware, firmware configuration, installer path, and signing artifacts behaved as documented.

## Safety rules

The first two phases are non-destructive to user data. The virtual-machine phase uses only virtual disks. The disposable-hardware phase uses a blank SSD or USB-connected test disk whose contents may be erased. A primary laptop or PC must not be used until the disposable-hardware gate is complete.

Before every real-disk test, record the device identifier, capacity, serial number, firmware mode, and a photograph or exported copy of the current boot configuration. Never select a disk by its position alone. Confirm the device model and size twice before allowing the Calamares installation job to write changes.

Create and verify an independent backup before any destructive test. A backup is considered verified only when a sample of files has been restored and its checksum matches the source. Do not treat the ISO checksum as a backup of the target disk.

Keep a second bootable recovery medium available. The recovery medium must boot independently of the Datya disk and must contain tools for restoring the previous bootloader, inspecting partitions, and copying data. Stop the test if the recovery medium cannot boot before installation begins.

## Validation stages and release gates

| Stage | Environment | Main purpose | Destructive to user data? | Exit condition |
|---|---|---|---:|---|
| 0. Artifact preparation | Build host | Freeze ISO, checksums, source, and signing inputs | No | Reproducible artifact set recorded |
| 1. VM installer tests | QEMU/KVM or equivalent | Exercise every installer page and partition path | No | Automated and manual cases pass |
| 2. VM Secure Boot tests | UEFI VM with Secure Boot | Verify trust chain and failure behavior | No | Signed path boots; unsigned path is rejected or clearly warned |
| 3. Disposable physical disk | Test PC/laptop | Verify real firmware, storage, Wi-Fi, graphics, and installer behavior | Yes, test disk only | Install, reboot, recovery, and rollback pass |
| 4. Target hardware matrix | Representative x86_64 and Pi 5 devices | Identify device-specific compatibility limits | Yes, test media only | Results documented per device |
| 5. Limited release approval | Maintainer review | Decide whether to label the ISO test, preview, or stable | No | Evidence reviewed and unresolved risks accepted explicitly |

## Stage 0: Freeze and prepare the artifact

Use the exact v0.1.1 commit and the `v0.1.1` tag. Record the Git commit, Debian suite, architecture, `SOURCE_DATE_EPOCH`, builder image or host version, and the SHA-256 checksum of the ISO. The release bundle must contain the ISO, source snapshot, release metadata, and checksum manifest.

Run the existing Rust, C++, Python, shell, manifest, and Calamares checks before the installer campaign. Do not use `DATYA_SKIP_TESTS=1` for a release candidate. If package metadata is still pending license review or contains placeholder verification data, label the build as a development or preview artifact rather than a stable release.

For Secure Boot, create a separate test key hierarchy. Do not use the production signing key during exploratory testing. Store the private key offline or in the approved secret store. Record the public certificate fingerprint and the exact kernel/module artifact hashes. Keep private key files outside the repository and verify that CI rejects private signing material.

## Stage 1: Virtual-machine installer validation

Create fresh UEFI virtual machines with at least one virtual disk and a second empty disk for negative and manual-partitioning cases. Test both an encrypted and an unencrypted installation. Use snapshots before every destructive installer test so the same scenario can be repeated.

The installer must begin with the Datya-branded welcome screen and must show an explicit installation confirmation before disk changes. The partition page must not silently select a disk or destructive operation. Manual partitioning must expose the selected device, filesystem, mount points, bootloader target, and encryption settings clearly enough for an operator to review.

The following cases are mandatory:

| ID | Test case | Expected result |
|---|---|---|
| VM-01 | Boot ISO in UEFI mode | Datya boot menu and desktop load without errors |
| VM-02 | Open installer from desktop launcher | Calamares starts with Datya branding and no privilege prompt loop |
| VM-03 | Welcome, locale, keyboard, and user pages | Each page accepts valid input and rejects invalid required input |
| VM-04 | Attempt to continue without choosing a partition action | Installer blocks progress and explains the missing choice |
| VM-05 | Guided install on an empty virtual disk | Partitions match the reviewed plan and installation completes |
| VM-06 | Manual partitioning with EFI and root partitions | Mount points and filesystem choices are preserved |
| VM-07 | LUKS2 encrypted installation | Unlock is requested at boot and the system reaches the login screen |
| VM-08 | Cancel before the final confirmation | No disk changes occur after cancellation |
| VM-09 | Simulated low-space disk | Installer reports insufficient space without corrupting the disk |
| VM-10 | Reboot after installation | Installed system boots from the intended disk and reaches XFCE/LightDM |
| VM-11 | Remove the ISO after installation | Installed system does not depend on the live medium |
| VM-12 | Inspect privacy and policy markers | Telemetry-disabled and scope-policy settings are present and visible |

Capture the Calamares log, partition table before and after installation, `journalctl -b`, kernel version, `/etc/datya/build-info`, and a screenshot of the final summary page. The test passes only when the observed partition table matches the planned table and the bootloader is installed in the intended UEFI system partition.

## Stage 2: Secure Boot validation

Secure Boot validation must test both the successful trust path and the failure path. A green boot alone is insufficient because it may indicate that firmware validation is disabled or that a different trust key is being used.

Use a UEFI virtual machine first. Reset its enrolled keys to a controlled test state where possible. Enroll only the test certificate through the firmware's documented enrollment screen. Record the certificate fingerprint before booting the signed image. Confirm the firmware reports Secure Boot as enabled from both the firmware UI and the running operating system.

The signed path should cover every artifact that the firmware or boot chain is expected to verify, including the bootloader and any Datya kernel module that is loaded during the test. The validation record must identify which component is signed by which key. Do not describe a kernel module as Secure Boot validated merely because the bootloader is signed.

| ID | Test case | Expected result |
|---|---|---|
| SB-01 | Boot signed ISO with test key enrolled | Firmware accepts the boot chain and the live system starts |
| SB-02 | Boot with Secure Boot enabled but test key absent | Firmware rejects the untrusted component or shows a clear enrollment path |
| SB-03 | Load the signed Guardian module | Module loads and its signature state is visible in system evidence |
| SB-04 | Attempt to load an altered module | Kernel rejects it; no silent fallback occurs |
| SB-05 | Attempt to load an unsigned module | Kernel rejects it under the configured policy |
| SB-06 | Revoke or remove the test certificate | Previously trusted test artifact no longer passes the intended trust check |
| SB-07 | Enroll a new test certificate through firmware | Enrollment requires deliberate operator action and is observable |
| SB-08 | Boot a recovery medium after a trust failure | Recovery path remains available and documented |
| SB-09 | Upgrade the kernel/module in a test environment | New artifacts are signed and the old trust assumptions are not silently reused |

Record `mokutil --sb-state` where supported, the firmware Secure Boot state, enrolled certificate fingerprints, `modinfo` output, kernel log messages, and the exact signature verification commands. If the target firmware does not support the same enrollment workflow as a PC, document it as a separate platform result rather than extrapolating from x86_64.

For Raspberry Pi 5, do not assume PC-style UEFI Secure Boot or MOK behavior. Validate the actual boot firmware and secure-boot mechanism used by the selected Pi boot chain. If the tested Pi path does not provide equivalent signature enforcement, state that limitation in the hardware compatibility documentation instead of claiming feature parity.

## Stage 3: Disposable physical-disk installation

Use a blank SSD or a dedicated test machine. Disconnect other storage devices where practical. If other devices must remain connected, identify them by model and serial number and verify that the intended bootloader target is the test disk.

Repeat VM-01 through VM-12 on physical hardware, then add suspend/resume, reboot cycles, wired and wireless networking, display resolution, audio, USB devices, and encrypted-disk unlock. Run at least three cold boots and three warm reboots after installation. Confirm that the system remains usable when the live USB is removed.

The physical-disk gate fails if the installer writes to an unintended disk, creates an unreviewed partition, loses the recovery path, leaves the system unable to boot, loads an unsigned security module, or hides a network or privacy behavior from the operator.

## Stage 4: Hardware test matrix

The minimum matrix should include one modern x86_64 UEFI desktop, one x86_64 laptop with Wi-Fi and suspend support, one system with Secure Boot enabled by default, and one Raspberry Pi 5 with the selected supported storage and boot firmware. Add an ARM64 laptop or MacBook only when its boot path and device support are explicitly defined.

| Device class | Required observations |
|---|---|
| x86_64 desktop | UEFI boot, graphics, storage, Ethernet, USB, installer, reboot |
| x86_64 laptop | Wi-Fi, suspend/resume, battery reporting, keyboard, touchpad, display |
| Secure Boot PC/laptop | Key enrollment, signed boot, signed module, rejection of altered module |
| Raspberry Pi 5 | Boot medium, firmware mode, HDMI, USB, Ethernet/Wi-Fi, storage, policy limits |
| ARM laptop/MacBook | Only if supported boot firmware and drivers are documented |

Produce one result row per device. A result of “not tested” must not be represented as “supported.” Hardware-specific failures must be linked to the device model, firmware version, kernel version, and exact ISO checksum.

## Evidence and sign-off

Store test evidence in a release directory outside the source tree or in an approved test-results repository. Include the ISO checksum, commit, test operator, UTC timestamp, hardware identity, firmware settings, logs, screenshots, partition tables, Secure Boot fingerprints, and pass/fail outcome. Remove private keys and personal data from logs before sharing them.

A release candidate may be promoted only when all mandatory tests pass or every exception has a written owner, impact assessment, workaround, and follow-up issue. The maintainer must sign a checklist confirming that the artifact was tested in a VM, on a disposable physical disk, and with the documented Secure Boot state. The release notes must state the tested hardware scope and the untested scope.

## Rollback and recovery procedure

If installation fails, stop modifying the disk. Boot the independent recovery medium, copy diagnostic logs to separate storage, and record the last successful step. Restore the previous bootloader only after preserving evidence. If encryption or partitioning was involved, do not recreate partitions during troubleshooting because that can destroy recovery data.

If Secure Boot blocks a test artifact, do not disable Secure Boot as the default workaround. First verify the certificate fingerprint, signature, boot mode, and artifact hash. Use a documented temporary test-key enrollment or a recovery boot path. Any production key change requires a separate approval and key-rotation record.

## Recommended execution order

Begin with the existing v0.1.1 ISO in a UEFI VM. Complete the installer matrix and collect logs. Then run the Secure Boot matrix in a separate VM with disposable test keys. After both VM gates pass, use one blank physical SSD on one x86_64 machine. Expand to the remaining hardware classes only after the first physical-disk result is reproducible. Do not use a primary user disk during this release cycle.

The next implementation work should be a test harness that records ISO checksums, VM configuration, Calamares logs, partition snapshots, and Secure Boot state into a timestamped evidence directory. The harness should fail closed when the target disk identity is missing or when the expected Secure Boot state is not detected.

## References

[1]: https://calamares.io/docs/ "Calamares documentation"
[2]: https://wiki.debian.org/SecureBoot "Debian SecureBoot documentation"
[3]: https://wiki.debian.org/UEFI "Debian UEFI documentation"
[4]: https://www.kernel.org/doc/html/latest/admin-guide/module-signing.html "Linux kernel module signing facility"
[5]: https://www.qemu.org/docs/master/system/invocation.html "QEMU system invocation documentation"
[6]: https://www.raspberrypi.com/documentation/computers/configuration.html "Raspberry Pi configuration documentation"
