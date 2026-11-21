# License and third-party notices

This repository is a collection of build instructions and selected inputs, not a relicensing of upstream code. Each component retains its own terms. Do not infer permission to redistribute stock Unraid files, NVIDIA proprietary components, or source modifications beyond their applicable licenses.

- **Linux kernel**: GPL-2.0-only with syscall exception and other per-file notices. See kernel source `COPYING` and individual file headers.
- **NVIDIA open GPU kernel modules 580.196.07**: upstream states individual files are MIT unless noted; linked Linux kernel modules are dual MIT/GPLv2. See the upstream [`COPYING`](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/580.196.07/COPYING) and retain it with any redistributed NVIDIA module bundle.
- **OpenZFS/SPL 2.4.4**: CDDL-1.0; consult the source distribution's `LICENSE` and copyright notices. ZFS is a locally built module dependency, not a separately published artifact in this release.
- **Unraid-specific md sources and modifications**: retain embedded copyright and license notices in `build/*/src/unraid-drivers/md/`. Their presence here is for the stated kernel build; no claim of endorsement by Lime Technology.
- **Unraid stock system files**: not included in the repository or release. The locally assembled `bzroot` necessarily contains stock files and must not be redistributed here.
- **NVIDIA proprietary userspace libraries and firmware**: not included. Obtain through NVIDIA's applicable distribution channels and license terms.

The kernel and NVIDIA module assets are provided without warranty. Refer to each upstream license for the precise rights, obligations, disclaimers, and limitations.
