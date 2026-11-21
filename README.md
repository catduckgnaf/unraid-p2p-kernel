# Unraid 7.4.0 P2P kernel builds

Experimental custom kernels for the **exact Unraid 7.4.0 baseline, Linux 6.18.60**. These are optional boot entries, not CA templates and not automatic installers. They are community builds, not supported or endorsed by Lime Technology.

## Variants

| Variant | Kernel release | NVIDIA kernel modules | Hardware status |
|---|---|---|---|
| Intel Arc PCI P2P | `6.18.60-Unraid-p2p` | No | Build and static package checks verified; no boot test claimed |
| Intel Arc PCI P2P + NVIDIA open modules 580.196.07 | `6.18.60-Unraid-p2p-nvidia580.196.07` | NVIDIA open kernel modules 580.196.07 | Build and static package checks verified; no NVIDIA GPU or boot test available |

Both builds enable `CONFIG_PCI_P2PDMA=y` and `CONFIG_DMABUF_MOVE_NOTIFY=y`. NVIDIA open modules support Turing and newer GPUs. NVIDIA userspace libraries and firmware are **not** included; use only matching NVIDIA 580.196.07 userspace, and note that the Unraid NVIDIA plugin's current package lookup targets stock `6.18.60-Unraid`, not this custom release. Plugin integration for the custom release is not provided here. Do not assume the stock plugin module package works with this kernel.

## Downloads

See [Releases](https://github.com/catduckgnaf/unraid-p2p-kernel/releases) for the versioned `bzImage` files, corresponding Linux kernel module trees as `modules-*.tar.gz` (including md-mod, ZFS/SPL, and NVIDIA open modules where applicable), and SHA-256 manifest. **No stock `bzroot` or complete Unraid boot image is distributed.** Create each matching `bzroot` locally from the stock `bzroot` on your own Unraid 7.4.0 installation using the published [`build/assemble-local-bzroot.sh`](build/assemble-local-bzroot.sh) procedure and matching module bundle. Never mix one variant's `bzImage` and modules with another's.

## Installation and recovery

Read [INSTALL.md](INSTALL.md) before use. It explains how to retain the stock entry, create a separate boot entry, assemble the matching local `bzroot`, validate hashes, select the alternate entry, and roll back. No live host changes have been made as part of building or publishing these artifacts. Test on a non-critical system and preserve a verified stock recovery path.

## Build inputs and provenance

The repository's [`build/`](build/) directory contains the exact config, source modifications, build scripts, upstream source URLs and hashes, and license/provenance notices. Start with [BUILD.md](BUILD.md). The release includes the redistributable Linux kernel images and open-source module bundles, not stock Unraid input, NVIDIA proprietary userspace, or a preassembled `bzroot` containing Unraid's stock files.

## Scope and warnings

- Only Unraid 7.4.0 / Linux 6.18.60 is covered. Do not use on another baseline.
- No boot smoke test, NVIDIA GPU runtime test, CUDA test, or NVIDIA P2P test has been performed.
- Kernel replacement can make a system unbootable. Keep the original boot option and backups.
- P2P capability does not guarantee that a particular GPU, driver, topology, or application supports peer transfers.
- This is provided without warranty. See [LICENSES.md](LICENSES.md) and upstream notices for license terms.
