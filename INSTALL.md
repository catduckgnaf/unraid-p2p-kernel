# Manual install and rollback

**Experimental and unsupported.** This guide is for Unraid 7.4.0 / Linux 6.18.60 only. Do not proceed without physical or out-of-band access and a verified way to restore the stock boot files. No install or boot test has been performed by this project.

## Before starting

1. Confirm the running stock system is exactly Unraid 7.4.0 with `uname -r` equal to `6.18.60-Unraid`. Stop if it differs.
2. Download one versioned release's matching `bzImage` and `modules-*.tar.gz`, plus `SHA256SUMS`. Verify downloaded files with `sha256sum -c SHA256SUMS` from the directory containing them.
3. For NVIDIA variant only, confirm the GPU supports NVIDIA's open kernel modules (Turing or newer) and arrange matching NVIDIA 580.196.07 user-space libraries using NVIDIA's supported channel. The standard Unraid NVIDIA plugin's current package lookup uses exact `uname -r` and is built for stock `6.18.60-Unraid`; this project does not provide a plugin package or integration for the custom release. Do not assume the plugin will load the supplied modules. If you cannot validate the required userspace and module-loading path before reboot, stop and use the Intel-only variant or stock kernel.
4. Keep the server console or remote management available. Do not change the existing stock boot entry or make the experimental entry the default until it has been tested.

## Prepare the selected flavor locally

On the Unraid host, keep the downloaded files outside `/boot` while preparing. Identify the correct release's module bundle and extract it to a temporary directory. Inspect the archive before extraction and ensure it contains paths rooted at `lib/modules/<exact-custom-kernel-release>/`; do not extract an unexpected archive. The custom release strings are listed in the README.

The published module archive is a module tree, **not** a complete Unraid root filesystem and must not be renamed to `bzroot`. Assemble it locally with [`build/assemble-local-bzroot.sh`](build/assemble-local-bzroot.sh) using your stock `/boot/bzroot`, the matching module archive, the exact custom kernel release, and a new output path outside `/boot`. This version-sensitive operation preserves the stock early cpio and replaces only the matching kernel module directory. Review the script and confirm its prerequisites and inputs before running; it never writes to `/boot`.

Before changing boot configuration, make byte-for-byte backups of the current `/boot/bzImage`, `/boot/bzroot`, and boot configuration files to storage outside `/boot`, and record their SHA-256 hashes. Also verify the original stock boot entry and recovery path still work.

## Add an alternate boot entry

1. Preserve the original stock entry untouched. Use Unraid's boot configuration mechanism to add a separate experimental entry that points at the new uniquely named `bzImage` and locally assembled matching `bzroot`.
2. Do not overwrite the existing `bzImage` or `bzroot`, do not replace the default entry, and do not mix files from different variants.
3. Inspect the resulting configuration and confirm every referenced file exists and the original stock entry is unchanged. Keep a copy of the original boot configuration outside `/boot`.
4. Select the experimental entry for one manual boot only. If the alternate entry cannot isolate the two new filenames while retaining stock recovery, stop.

After boot, verify `uname -r` matches the selected variant, check system logs and Unraid array health, and confirm expected devices/services before any further use. For NVIDIA, also verify the exact open module version and user-space version match; no GPU runtime or P2P success is implied by a successful boot.

## Rollback

Select the original stock boot entry at the console. If the experimental entry fails, do not change the stock entry. If files or boot configuration were inadvertently replaced, restore both stock image files and the original boot configuration from verified backups, check their recorded SHA-256 hashes, then select the stock entry. Keep the experimental files and logs aside for diagnosis. Never restore only one member of an image pair.

Before any Unraid upgrade, remove the experimental entry and its files after returning to stock, or wait for a separately verified build for the new exact baseline. Do not carry these 6.18.60 modules forward to another kernel release.