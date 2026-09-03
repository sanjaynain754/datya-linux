# Datya Secure Boot Module Signing

This workflow signs out-of-tree Linux kernel modules with a key controlled by the machine owner or Datya release team. It does not disable Secure Boot and does not bypass signature enforcement.

## 1. Install prerequisites

On Debian/Ubuntu, install the tools and exact headers for the target kernel:

```bash
sudo apt-get update
sudo apt-get install --yes openssl mokutil kmod linux-headers-$(uname -r)
```

The target machine must boot in UEFI mode for MOK enrollment. Check the current state before changing anything:

```bash
mokutil --sb-state
uname -r
```

## 2. Generate a key pair

Run the script on an administrator-controlled machine. It creates a 3072-bit RSA key and a DER certificate with strict permissions:

```bash
sudo ./generate-mok.sh /root/datya-signing "Datya Linux Module Signing"
sudo sha256sum /root/datya-signing/datya-mok.priv /root/datya-signing/datya-mok.der
```

Store `datya-mok.priv` offline or in an approved hardware-backed signing service. Never commit it to Git, include it in an ISO, upload it to a ticket, or send it to a workstation that does not perform signing. Keep the public `.der` certificate available for enrollment and verification.

## 3. Build the module for the exact kernel

Build against the exact target headers, not merely a similar kernel:

```bash
make -C ../../kernel KDIR=/lib/modules/$(uname -r)/build
```

## Disposable v0.1.1 test bundle

For VM and disposable-hardware validation, the combined workflow can generate a test certificate, build the Guardian module against one exact kernel, sign it, and write hash evidence:

```bash
sudo ./create-test-signing-bundle.sh --build-module \
  --kernel "$(uname -r)" \
  --key-dir /root/datya-v0.1.1-test-signing
```

To generate and inspect test keys without building a module:

```bash
sudo ./create-test-signing-bundle.sh --generate-only \
  --key-dir /root/datya-v0.1.1-test-signing
```

The combined script refuses to overwrite an existing key directory or unsigned backup, requires matching kernel headers and `sign-file`, keeps the private key at mode `0600`, and records the certificate fingerprint and module hash. It deliberately does not enroll the certificate, alter firmware settings, disable Secure Boot, or copy private material into the ISO. Enrollment must remain a separate, manually reviewed test step using `enroll-mok.sh` on hardware the administrator controls.

## 4. Sign the module

```bash
sudo DATYA_SIGNING_DIR=/root/datya-signing \
  ./sign-module.sh ../../kernel/datya_guardian.ko "$(uname -r)"
```

The script keeps an unsigned backup next to the module, uses the target kernel's `sign-file`, and prints the signer/hash fields:

```bash
modinfo ../../kernel/datya_guardian.ko | grep -E '^(signer|sig_key|sig_hashalgo):'
```

## 5. Stage certificate enrollment

Enrollment changes the machine's trusted MOK database and requires a firmware approval after reboot. Review the displayed fingerprint carefully before proceeding:

```bash
sudo ./enroll-mok.sh /root/datya-signing/datya-mok.der
sudo reboot
```

At the firmware MOK Manager screen, select **Enroll MOK**, inspect the certificate, enter the one-time password created by `mokutil`, and confirm. This step is an important system trust change; do it only on hardware you administer.

## 6. Verify after reboot

```bash
mokutil --sb-state
mokutil --list-enrolled | grep -A2 -B2 'Datya'
modinfo ../../kernel/datya_guardian.ko | grep -E '^(signer|sig_key|sig_hashalgo):'
sudo modprobe --dry-run datya_guardian
```

Load the module only after reviewing the module source, policy, and kernel compatibility. Confirm the load/unload events in the local audit stream.

## 7. Rotation and revocation

Set an expiry policy, generate a new key before the old certificate expires, sign and test all modules with the new key, and enroll the new public certificate. Keep the old key offline until every supported image has migrated. If a key is compromised, stop signing immediately, revoke it through the platform's MOK management workflow on affected devices, publish a new certificate fingerprint, rebuild/re-sign modules, and document the incident. Do not delete the only copy of old evidence or keys needed for incident response.

## Operational limits

MOK enrollment trusts modules for a particular owner-controlled machine; it is not a replacement for reproducible builds, source review, package signing, or measured boot. A compromised root account or firmware can still alter a running system. Secure Boot verifies what is signed, not whether the signed code is bug-free.
