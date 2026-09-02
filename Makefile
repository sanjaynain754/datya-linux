.DEFAULT_GOAL := help
SHELL := /bin/bash
.SHELLFLAGS := -euo pipefail -c

PYTHON ?= python3
CMAKE ?= cmake
CARGO ?= cargo
MAKE_CMD ?= make
ARCH ?= amd64
SUITE ?= trixie
BUILD_DIR ?= build

.PHONY: help check test build build-all device-lab build-python build-shell build-rust build-cpp build-kernel manifest install-plan iso clean

help:
	@printf '%s\n' 'Datya Linux unified build targets:'
	@printf '%s\n' '  make check         syntax, policy, manifest, and catalog checks'
	@printf '%s\n' '  make test          all Python regression tests'
	@printf '%s\n' '  make build         check + Python + Rust + C/C++ builds'
	@printf '%s\n' '  make build-all     build + target-kernel module'
	@printf '%s\n' '  make device-lab    inventory hardware and build-lab readiness'
	@printf '%s\n' '  make build-rust    cargo fmt/check/test/clippy'
	@printf '%s\n' '  make build-cpp     CMake configure and build'
	@printf '%s\n' '  make build-kernel  out-of-tree kernel module build'
	@printf '%s\n' '  make iso            privileged Debian live-build ISO build'
	@printf '%s\n' '  make install-plan  verified pack installer dry-run'

check: build-python build-shell manifest
	@$(PYTHON) tools/datya-tool-catalog.py --list >/dev/null
	@$(PYTHON) tools/datya-install-pack.py --pack observe >/tmp/datya-install-plan.json || test $$? -eq 1
	@printf '%s\n' 'All language-independent checks passed.'

test:
	@$(PYTHON) -m unittest discover -s tests -p 'test_*.py' -v

build-python:
	@$(PYTHON) -m py_compile tools/*.py tests/*.py
	@$(PYTHON) -m unittest discover -s tests -p 'test_*.py' -q

build-shell:
	@for file in $$(find iso security tools -type f -name '*.sh' -print); do bash -n "$$file"; done
	@if command -v shellcheck >/dev/null 2>&1; then shellcheck --severity=error $$(find iso security tools -type f -name '*.sh' -print); else printf '%s\n' 'shellcheck not installed; bash -n completed (CI installs shellcheck).'; fi

manifest:
	@$(PYTHON) tools/verify-package-manifest.py packages/manifest.json
	@$(PYTHON) -c 'import tomllib; tomllib.load(open("profiles/tool-packs.toml", "rb"))'

build-rust:
	@command -v $(CARGO) >/dev/null 2>&1 || { echo 'cargo is required; install Rust stable toolchain.' >&2; exit 127; }
	@$(CARGO) fmt --all -- --check
	@$(CARGO) test --workspace --locked
	@$(CARGO) check --workspace --locked
	@$(CARGO) clippy --workspace --all-targets --all-features -- -D warnings

build-cpp:
	@command -v $(CMAKE) >/dev/null 2>&1 || { echo 'cmake is required; install CMake and a C++17 compiler.' >&2; exit 127; }
	@$(CMAKE) -S cpp-control -B $(BUILD_DIR)/cpp -DCMAKE_BUILD_TYPE=Release
	@$(CMAKE) --build $(BUILD_DIR)/cpp --parallel

build-kernel:
	@KDIR="/lib/modules/$$(uname -r)/build"; \
	if [[ ! -d "$$KDIR" ]]; then \
		echo "kernel headers are required at $$KDIR; install linux-headers-$$(uname -r) or build on the target kernel" >&2; exit 127; \
	fi; \
	$(MAKE_CMD) -C kernel KDIR="$$KDIR"

build-python: ## Python is interpreted; compilation and tests are its build gate

build: check build-rust build-cpp
	@printf '%s\n' 'Datya user-space language components built successfully.'

build-all: build build-kernel
	@printf '%s\n' 'Datya source components, including the kernel module, built successfully.'

device-lab:
	@$(PYTHON) tools/datya-device-lab.py --json --output $(BUILD_DIR)/device-lab.json

install-plan:
	@$(PYTHON) tools/datya-install-pack.py --all

iso:
	@command -v lb >/dev/null 2>&1 || { echo 'live-build is required; install live-build before running make iso.' >&2; exit 127; }
	@sudo ./iso/build-datya-iso.sh $(ARCH) $(SUITE)

clean:
	@rm -rf $(BUILD_DIR) .pytest_cache tests/__pycache__ tools/__pycache__
