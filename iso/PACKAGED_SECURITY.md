# Packaged Datya Security Components

The `config/hooks/normal/0900-install-datya-security.hook.chroot` hook builds the C++17 control daemon inside the target chroot, installs it under `/usr/lib/datya/datya-control`, stages the Guardian module under `/lib/modules/<kernel>/extra/`, and runs `depmod`. It also creates the restricted `datya-guardian` service account and installs the Datya policy marker.

The build script copies `cpp-control/`, `kernel/`, and `systemd/datya-control.service` into the chroot before the hook runs. The image package list includes the compiler, CMake, OpenSSL development headers, kernel headers, and `kmod` required for the build.

## Signed release requirement

The hook intentionally does not embed private signing keys. A release pipeline must sign `datya_guardian.ko` with an owner-controlled key using the target kernel's `scripts/sign-file`, verify the signature, and reject the image if Secure Boot policy requires a signature and the module is unsigned. The current hook stages an unsigned module only for development or a later signing step; it must not be treated as a production release artifact.

## Enablement

The C++ daemon service is installed but should be enabled only after the image maintainer has reviewed the policy, log path, account permissions, and tool adapter configuration:

```bash
sudo systemctl enable --now datya-control.service
sudo journalctl -u datya-control.service
```

The daemon remains dry-run by design in the current reference implementation. The Guardian kernel module is not automatically loaded by this hook; loading should be a deliberate signed-profile choice after hardware and kernel testing.
