# Release SHA-256 manifest

The versioned GitHub Release includes a `SHA256SUMS` asset listing SHA-256 hashes for all downloadable kernel image and module archive assets. Download `SHA256SUMS` and the selected assets into the same directory, then run:

```sh
sha256sum -c SHA256SUMS
```

The manifest verifies integrity against the published release values; it does not establish that a download is trustworthy if the release itself is compromised. Compare file names exactly, and stop on any mismatch.
