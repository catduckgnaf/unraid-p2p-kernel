# Upstream update alerts

The workflow supports schedule and manual dispatch (default dry run), and validates pull requests with read-only dry-run scans. The `scan` job runs the fixtures and fetches live feeds without issue permissions, saving its report as an artifact. A separate `publish` job is limited to scheduled `main` runs or manual `main` runs with dry-run explicitly disabled; it checks out trusted `main` and alone has `issues: write`. On first run, baseline comparison includes known newer items; the known Unraid 7.4.1 / Linux 6.18.64 update remains visible against the 7.4.0 / 6.18.60 baseline.

## Sources and routing

`watch-config.json` is the source registry and records the current build compatibility baseline: Unraid 7.4.0 / Linux 6.18.60, NVIDIA open modules 580.196.07. It tracks kernel.org release metadata, Torvalds Linux commits in PCI P2PDMA, DRM xe/i915/AMDGPU, and DMA-BUF, NVIDIA open GPU kernel module releases, Intel GPU release notes, and separate Unraid stable and preview lanes from the official release-note index. Unraid detail pages are inspected for their shipped `x.y.z-Unraid` kernel version.

Each item becomes an actionable issue; a SHA-256 key derived from source ID and immutable upstream ID is embedded in an HTML comment. Existing issues are searched before issue creation, so reruns do not duplicate alerts. Upstream titles and summaries are HTML escaped, limited in length, and treated as untrusted data. Issues ask a maintainer to check compatibility; no updates are applied automatically.

The filter is intentionally scoped: kernel change feeds retain matching P2PDMA, GPU/DRM, and DMA-BUF changes; release feeds report newer release identifiers. Linux release metadata is checked against 6.18.60. The initial Unraid stable baseline is 7.4.0, so 7.4.1 (Linux 6.18.64-Unraid) is surfaced rather than silently treated as already seen. Preview links are distinct from stable and labeled `preview`.

Commits from Linus's mainline path and Greg Kroah-Hartman's stable tree have separate source IDs. Mainline or maintainer-queue changes, including the supplied Intel Xeon P2PDMA candidate `803285675d466fdfcb023e0d9f73609c679d15de`, are labeled as candidates, not claimed released/backported. Stable tree commits and kernel.org releases are distinct evidence of downstream status.

## Failure and permissions

The workflow grants only `contents: read` and job-level `issues: write`; checkout does not persist credentials. It does not run code from upstream sources. Every source is attempted independently. Failures appear in the JSON report and cause a nonzero exit after successful-source alerts are processed, making partial coverage explicit without discarding available findings. An issue API failure also stops the run.

## Local verification

Run `python3 -m unittest discover -s tests -v`. To inspect current source results without writing issues, run `python3 scripts/upstream_watch.py --dry-run`. For deterministic fixture scans, pass `--fixtures <json>` where keys are source IDs and values are raw JSON or HTML strings. In GitHub Actions, use **Upstream update watch → Run workflow**; dry run is selected by default. First run compares against the committed compatibility baselines, so it can open issues for already-known newer upstream items; review the resulting set before using a non-dry-run manual dispatch.
