# Build and provenance

## Supported baseline

Only Unraid 7.4.0, Linux 6.18.60, x86_64. The released `bzImage` files and `modules-*.tar.gz` bundles correspond to configs and source modifications under `build/intel/` and `build/nvidia/`. Both set `CONFIG_PCI_P2PDMA=y` and `CONFIG_DMABUF_MOVE_NOTIFY=y`; NVIDIA modules use `LOCALVERSION=-Unraid-p2p-nvidia580.196.07` and NVIDIA open kernel modules 580.196.07.

## Inputs

- Linux kernel source: `https://cdn.kernel.org/pub/linux/kernel/v6.x/linux-6.18.60.tar.xz` (SHA-256 `3c2f44ef6acc021a7ad444d9a2e6ec1ef488ff09368793d0004a6080f69d621e`). Apply the patches and Unraid md driver sources in the relevant variant's `build/<variant>/src/` to this pristine source.
- ZFS/SPL source: OpenZFS `zfs-2.4.4`, `https://github.com/openzfs/zfs/releases/download/zfs-2.4.4/zfs-2.4.4.tar.gz`. Build against the exact kernel tree and release string. ZFS is CDDL-1.0; the upstream license text used for the build is included at `build/<variant>/licenses/ZFS-LICENSE`.
- NVIDIA variant only: NVIDIA open kernel modules 580.196.07, `https://github.com/NVIDIA/open-gpu-kernel-modules/archive/refs/tags/580.196.07.tar.gz` (published build input SHA-256 `3342cfc0e91c7e9c63c1ba24bcb850881068f5cfaf4c7ec45ad954b49c5a14f2`). Use only its open kernel module sources and preserve `build/nvidia/NVIDIA-COPYING`. These are dual MIT/GPLv2. No NVIDIA proprietary user-space libraries or firmware are included.
- Unraid-specific kernel config, patch files, and modified md sources are included in each variant's `build/<variant>/src/`. Their embedded copyright and license notices are retained. The base stock `bzroot` and its contents are not included; obtain them from a licensed Unraid 7.4.0 installation.

## Reproduction outline

1. Use a clean Linux x86_64 build host with kernel build dependencies (`build-essential`, `bc`, `bison`, `flex`, `libssl-dev`, `libelf-dev`, `dwarves`, `python3`, `cpio`, `xz-utils`, `zstd`, `kmod`, `rsync`, `autoconf`, `automake`, `libtool`, `pkg-config`, `uuid-dev`, `libblkid-dev`, `libudev-dev`, `libaio-dev`, `libattr1-dev`, `libtirpc-dev`, `zlib1g-dev`, `gawk`, `initramfs-tools-core`, `squashfs-tools`).
2. Verify source archive hashes, extract Linux 6.18.60, apply the patches in lexical order with `patch -p1`, copy `unraid-drivers/md/*` into `drivers/md/`, and start from the variant's config.
3. Run `build/build-kernel.sh intel` or `build/build-kernel.sh nvidia` with `KERNEL_SRC` set to a clean extracted Linux 6.18.60 tree and `OUTPUT_DIR` set to an empty directory. The script checks the exact kernel release, `CONFIG_PCI_P2PDMA=y`, and `CONFIG_DMABUF_MOVE_NOTIFY=y`, then builds `bzImage` and modules. Complete the module build with OpenZFS 2.4.4 against the same kernel tree. For NVIDIA, build the 580.196.07 open modules against the same kernel source and `Module.symvers`; verify all included NVIDIA modules have exact release vermagic and version 580.196.07. Do not include a mismatched module package.
4. Package the resulting module tree as the variant's `modules-*.tar.gz`. Produce a complete `bzroot` locally using `build/assemble-local-bzroot.sh <stock-bzroot> <modules.tar.gz> <kernel-release> <output-bzroot>`. This keeps the stock image's early cpio, unpacks its compressed main cpio, replaces only the stock kernel-release module directory with the matching custom-release module directory, and recompresses using the original main archive compression. Never distribute the assembled `bzroot`; it contains stock Unraid files. Keep it local for the install procedure.
5. Record SHA-256 hashes of the release assets and verify downloaded copies before use. The release tag and README identify the exact baseline; do not reuse these artifacts for another Unraid version.

The build was performed on the existing Unraid 7.4.0 build host. Its build commands and component checks were observed, but a second clean-room rebuild is not claimed. Reproducibility means the required inputs, patches, configs, procedures, and source hashes are identified here; it is not a claim of bit-for-bit reproducibility.

## Verification and limitations

The build handoff verified both kernel release strings, P2P config options, and module vermagic. NVIDIA's five open modules (nvidia, nvidia-uvm, nvidia-modeset, nvidia-drm, nvidia-peermem) were version 580.196.07; matching ZFS/SPL 2.4.4 and md-mod were present in the package. No boot smoke test, NVIDIA GPU initialization, CUDA, or NVIDIA P2P runtime test was performed. Uranium had no NVIDIA GPU installed. The currently installed Unraid NVIDIA plugin's package path is keyed to stock `6.18.60-Unraid`; custom-release plugin package integration is not included or implied.
