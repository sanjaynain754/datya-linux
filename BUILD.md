# Datya Linux Build Contract

The repository uses the root `Makefile` as the single build entrypoint. It does not silently pretend that an unavailable compiler, kernel headers package, ISO builder, or static checker succeeded. Each target either performs its checks or exits with an actionable dependency message.

## Quick validation

```bash
make check
make test
```

`make check` validates Python syntax and tests, all shell syntax, the package manifest, the TOML tool catalog, and the fail-closed installer plan. `make test` runs the complete Python regression suite.

## Full source build

```bash
make build
make build-all   # also requires headers for the currently running kernel
```

The full build performs checks, then runs Rust formatting/tests/check/clippy and the C/C++ CMake build. `build-all` additionally compiles the out-of-tree kernel module against the currently running kernel. Rust requires a stable Cargo toolchain. C/C++ requires CMake and a C++17 compiler. Python is interpreted, so bytecode compilation plus the test suite is its build gate.

Individual targets are available when diagnosing one component:

```bash
make build-python
make build-shell
make build-rust
make build-cpp
make build-kernel
```

The kernel target requires matching Linux kernel headers and normally must be run on the target kernel. If `/lib/modules/$(uname -r)/build` is absent, the target fails with the exact headers requirement instead of producing a misleading success. The ISO target is intentionally separate and privileged:

```bash
sudo make iso ARCH=amd64 SUITE=trixie
```

It requires Debian `live-build` and a root-capable build environment. ISO builds are not run by the default `make build` target because they are destructive to the ISO build directory, slow, privileged, and architecture-specific.

## Device-lab readiness

```bash
make device-lab
python3 tools/datya-device-lab.py --strict --json
```

The device-lab command only inventories the host; it does not load modules, attach USB devices, start VMs, change firewall rules, or install packages. It records architecture, kernel version, matching kernel-header availability, compilers, ISO tooling, virtualization commands, KVM/TUN/USB device nodes, network interfaces, and block devices in `build/device-lab.json`. Strict mode fails unless user-space build tools, ShellCheck, matching kernel headers, `live-build`, and a QEMU/KVM lab are all ready. A normal report is still useful on a constrained sandbox because it distinguishes `READY` from `BLOCKED` without claiming a hardware test occurred.

## Package and tool-pack checks

```bash
make install-plan
python3 tools/datya-install-pack.py --pack observe
```

The installer remains fail-closed until each package has a complete verified record, including license review and installation evidence. A metadata checksum alone is not promoted to release verification.

## CI contract

The same categories are enforced in GitHub Actions: Rust format/test/clippy, CMake build, shell syntax/ShellCheck, Python compilation/tests, TOML/JSON validation, package policy markers, and private signing-material checks. A local machine without Cargo or CMake can still run `make check`, but `make build` will stop with a clear missing-toolchain error.
