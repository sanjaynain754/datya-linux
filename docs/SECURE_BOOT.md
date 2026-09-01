# Secure Boot and Kernel Module Trust

## Trust model

Secure Boot verifies the first-stage bootloader and each signed stage before execution. It does not make a running system invulnerable and it does not prove that every user-space application is trustworthy. Datya should use a signed boot chain, signed kernel, signed initramfs, signed repository metadata, and signed out-of-tree modules.

The `kernel/datya_guardian.c` file is an experimental, read-only evidence sensor. It observes process execution and IPv4 socket state transitions through kernel tracepoints and emits rate-limited local kernel log events. It does not inspect payloads, collect source code, block traffic, evade monitoring, or send information remotely. A userspace collector must correlate these records with procfs/sysfs and apply policy.

## Build and sign

Build against the exact target kernel headers and do not copy a module between kernel versions:

```bash
make -C kernel KDIR=/lib/modules/$(uname -r)/build
```

For a Secure Boot machine, sign the module with a key held by the system owner or release infrastructure. Keep the private key offline or in a hardware-backed signing service:

```bash
openssl req -new -x509 -newkey rsa:3072 \
  -keyout datya-mok.priv -outform DER -out datya-mok.der \
  -nodes -days 3650 -subj "/CN=Datya Linux Module Signing/"

/usr/src/linux-headers-$(uname -r)/scripts/sign-file sha256 \
  datya-mok.priv datya-mok.der kernel/datya_guardian.ko
```

Enroll the public certificate using the platform's documented MOK/firmware enrollment flow. On production images, prefer an organization-controlled release key and reproducible build verification rather than asking every user to trust an unknown key.

## Installation policy

The module should be shipped disabled unless the user chooses the Guardian kernel sensor profile. Loading must be auditable, and unloading must restore a clean state. The system should reject unsigned modules when Secure Boot policy requires it. Package upgrades must verify the module signature and exact kernel ABI.

## Important limitations

A kernel module cannot guarantee that a user is untraceable. Firmware, bootloader, kernel, privileged malware, hardware, network observers, and remote services can observe or alter activity outside this module's visibility. The module is therefore a **local evidence sensor**, not an anonymity mechanism or complete tracking detector. Datya must communicate that limitation in the UI and documentation.
