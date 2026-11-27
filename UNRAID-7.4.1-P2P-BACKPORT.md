# Unraid 7.4.1 P2P kernel backport qualification

Status: experimental candidate, not a stable release. All 7.4.1 builds are **experimental and unverified against stock Unraid 7.4.1**. The Intel Xeon P2PDMA backport is adapted from upstream and has not been tested on hardware. Green build jobs do not establish bootability, stock Unraid compatibility, ZFS integration, or runtime P2P behavior.

## Source baseline

- Unraid release: 7.4.1
- Kernel source: ich777/unraid_kernel release `6.18.64-Unraid`
- Archive: `https://github.com/ich777/unraid_kernel/releases/download/6.18.64-Unraid/linux-6.18.64-Unraid.tar.xz`
- SHA-256: `177852d0a1abafdf56074262ada1cec1daba55144ef2182b5455df6db15fa7d7` (verified before build)
- Kernel release string: `6.18.64-Unraid`; source `.config` included in archive.

## Included changes

- `24bc5d64ddc289dae0a05b22e2966c55a2005716`, PCI/P2PDMA prerequisite: move the `CONFIG_X86` conditional outside `cpu_supports_p2pdma()`. Applies as an upstream patch.
- `803285675d466fdfcb023e0d9f73609c679d15de`, PCI/P2PDMA: add explicit Intel Xeon server CPU family matches. The 6.18.64 source has the required x86 CPU matching APIs, structure, and Intel family IDs. The mismatch is surrounding-code drift: after applying the prerequisite, `cpu_supports_p2pdma()` begins at line 447 versus upstream's line 546, and `seq_buf_print_bus_devfn()` is at line 421 rather than the cited upstream line 521. The separate `0002-pci-p2pdma-intel-xeon-adapted.patch` places the match table before the helper and checks it in the helper, preserving existing AMD handling.
- `6a68105dac4f93dfb431c77c3d5b5f46d0707a5f`, DRM: expand 64-bit `drm_vma_manager` mmap range to 8 TiB. Applies cleanly and is relevant to large multi-GPU dma-buf workloads.

PCI and DRM patches were applied and checked against a fresh extraction of the hash-verified archive. The Xe FLR series is excluded. The Intel adaptation remains untested on hardware.

## Limits

- ZFS `2.4.4_6.18.64_Unraid-1_LT` is not qualified. These CI jobs only build kernel and module artifacts, not a validated ZFS or complete Unraid boot image.
- NVIDIA open modules `580.196.07` source digest for 6.18.64 is recorded as `sha256:83cd2faece3e64cb882d057090dd34548212ebca8f8e25ec7e0d7a3056a08103`; CI verifies the download, version, and vermagic.
- AMD is an experimental config variant only. KFD P2P build configuration does not establish GPU, firmware, ROCm, or peer-transfer support.
- Do not install on Uranium. Disposable VM testing remains tracked in issue #2.
- Existing 7.4.0 artifacts and release remain unchanged. No stable 7.4.1 release is authorized.

Every CI artifact manifest identifies the build as experimental, unverified against stock Unraid 7.4.1, and not hardware tested.
