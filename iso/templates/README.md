# ISO Build Templates

This directory contains the persistent source templates copied into the clean live-build tree by `iso/build-datya-iso.sh`.

The Calamares files define the Datya branding, installer settings, and manual-partitioning safety defaults. The normal hooks install Datya security policy and configure the XFCE live desktop. Keeping these files outside the generated `iso/config` tree prevents a clean build from deleting the source configuration.

Generated live-build trees, downloaded package caches, bootloader binaries, and ISO artifacts are intentionally ignored by Git. Only these portable templates and the build scripts belong in the source release.
