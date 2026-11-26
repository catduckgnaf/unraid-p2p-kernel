# Read-only compatibility checker

`p2p-compat-check` reports whether this repository has an exact compatibility entry for the detected Unraid version and running kernel. It performs no network access, installation, boot-file access, reboot, or system modification.

Run on Unraid:

```sh
bash /path/to/p2p-compat-check
```

For standalone checks, pass a version-file path and running-kernel string:

```sh
bash p2p-compat-check fixtures/unraid-version 6.18.60-Unraid
```

Exit statuses: `0` exact match, `1` mismatch/no exact entry, `2` unknown target, `3` unavailable version source. The current exact entry is Unraid `7.4.0` with stock running kernel `6.18.60-Unraid`, corresponding to the v1.0.0 artifacts. The 6.18.60 custom P2P kernel release strings are intentionally not treated as the running stock-kernel baseline.

Run fixture tests with `python3 -m unittest discover -s plugin -p 'test_*.py'`.

## Scope and limitations

This is not a kernel ABI or module validation, artifact downloader, installer, updater, or rollback mechanism. A match means only that an exact version/kernel tuple appears in this repository's conservative compatibility table. It does not claim boot or hardware validation; see the main README's test limitations.

Official Unraid 7.x upgrade guidance uses the native Tools → Update OS workflow and recommends updating plugins before the OS. Its public documentation does not describe a third-party ABI check or native plugin callback for gating OS upgrades. The public `unraid/webgui` 7.4.1 plugin manager implementation has TARGET-VERSION handling for plugin downloads/updates and applies plugin/file Min/Max rules to the destination OS (falling back to current version), but this is plugin version filtering, not kernel ABI validation. The built-in `pre_plugin_checks` path distinguishes individual plugin updates from OS updates. This checker does not hook either flow; any integration requires disposable-VM testing of native upgrade interactions first.

Community Applications requires a public active repository, root OSI-approved `LICENSE`, non-empty `<Profile>` in `ca_profile.xml`, and a valid plugin wrapper; its submission portal runs Validate and Scan and then review. CA version filtering/admission is separate from exact kernel compatibility and must not be represented as an ABI check. No CA submission is part of this change.

## Required before any install or public listing

Test only in a disposable Unraid VM before any install/update/rollback phase, CA listing, or live use: plugin-manager install and removal, version-matched artifacts, all checker outcomes on actual guest state, failed downloads/updates and recovery, boot-file backup/restore, and native Tools → Update OS with plugin present. Confirm there is no interference with native upgrade checks. No such VM tests have been performed for this change.
