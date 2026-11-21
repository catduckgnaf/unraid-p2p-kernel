#!/usr/bin/env bash
# Assemble local Unraid 7.4.0 bzroot using the stock image and a matching
# published module tree. This script never writes to /boot.
set -euo pipefail

usage() {
  echo "Usage: $0 <stock-bzroot> <modules.tar.gz> <kernel-release> <output-bzroot>" >&2
  exit 2
}
[[ $# == 4 ]] || usage
stock=$(realpath "$1")
modules=$(realpath "$2")
krel=$3
output=$4
[[ -r $stock && -r $modules && -n $krel && ! -e $output ]] || { echo "Input unreadable or output already exists" >&2; exit 1; }
[[ $krel == 6.18.60-Unraid-p2p || $krel == 6.18.60-Unraid-p2p-nvidia580.196.07 ]] || { echo "Unsupported kernel release: $krel" >&2; exit 1; }
command -v cpio >/dev/null
command -v python3 >/dev/null
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

# Parse early newc cpio and detect its compression boundary. Refuse unsafe
# early symlink/hardlink entries rather than repacking paths that may escape.
python3 - "$stock" "$work/early.cpio" "$work/main.offset" "$work/compression" <<'PY'
import pathlib, stat, sys
source = pathlib.Path(sys.argv[1]).read_bytes()
pos = 0
records = []
while True:
    if source[pos:pos+6] != b"070701":
        raise SystemExit("invalid early newc cpio header")
    h = source[pos+6:pos+110]
    if len(h) != 104:
        raise SystemExit("truncated early cpio header")
    vals = [int(h[i:i+8], 16) for i in range(0, 104, 8)]
    ino, mode, uid, gid, nlink, mtime, size, devmajor, devminor, rdevmajor, rdevminor, namesize, check = vals
    pos += 110
    name = source[pos:pos+namesize]
    if len(name) != namesize or not name.endswith(b"\0"):
        raise SystemExit("invalid early cpio filename")
    pos = (pos + namesize + 3) & ~3
    pos += size
    pos = (pos + 3) & ~3
    path = name[:-1].decode("utf-8", "replace")
    records.append((path, mode, nlink))
    if path == "TRAILER!!!":
        break
if any(stat.S_ISLNK(mode) or (stat.S_ISREG(mode) and nlink > 1) for path, mode, nlink in records):
    raise SystemExit("early cpio contains symlinks or hardlinks; refusing to repack")
while pos < len(source) and source[pos] == 0:
    pos += 1
magic = source[pos:pos+6]
if magic.startswith(b"\xfd7zXZ\x00"):
    kind = "xz"
elif magic.startswith(b"\x28\xb5\x2f\xfd"):
    kind = "zstd"
elif magic.startswith(b"\x1f\x8b"):
    kind = "gzip"
else:
    raise SystemExit(f"unsupported main archive compression magic: {magic.hex()}")
pathlib.Path(sys.argv[2]).write_bytes(source[:pos])
pathlib.Path(sys.argv[3]).write_text(str(pos))
pathlib.Path(sys.argv[4]).write_text(kind)
PY
kind=$(<"$work/compression")
offset=$(<"$work/main.offset")
mkdir "$work/root"
case $kind in
  xz) dd if="$stock" bs=1 iflag=skip_bytes,count_bytes skip="$offset" status=none | xz -dc | (cd "$work/root" && cpio -idm --quiet --no-absolute-filenames);;
  zstd) dd if="$stock" bs=1 iflag=skip_bytes,count_bytes skip="$offset" status=none | zstd -dc | (cd "$work/root" && cpio -idm --quiet --no-absolute-filenames);;
  gzip) dd if="$stock" bs=1 iflag=skip_bytes,count_bytes skip="$offset" status=none | gzip -dc | (cd "$work/root" && cpio -idm --quiet --no-absolute-filenames);;
esac
stock_krel=6.18.60-Unraid
[[ -d "$work/root/lib/modules/$stock_krel" ]] || { echo "stock bzroot lacks modules/$stock_krel" >&2; exit 1; }

# Inspect module archive paths and types before extraction. Permit only dirs,
# regular files and relative symlinks with no parent traversal.
python3 - "$modules" <<'PY'
import pathlib, sys, tarfile
with tarfile.open(sys.argv[1], "r:gz") as tf:
    for member in tf.getmembers():
        path = pathlib.PurePosixPath(member.name)
        if path.is_absolute() or ".." in path.parts:
            raise SystemExit(f"unsafe archive path: {member.name}")
        if not (member.isdir() or member.isfile() or member.issym()):
            raise SystemExit(f"unsupported archive entry: {member.name}")
        if member.issym():
            target = pathlib.PurePosixPath(member.linkname)
            if target.is_absolute() or ".." in target.parts:
                raise SystemExit(f"unsafe symlink target: {member.name} -> {member.linkname}")
PY
mkdir "$work/module-tree"
tar -xzf "$modules" -C "$work/module-tree"
[[ -d "$work/module-tree/lib/modules/$krel" ]] || { echo "module archive does not contain expected $krel tree" >&2; exit 1; }
rm -rf "$work/root/lib/modules/$stock_krel"
cp -a "$work/module-tree/lib/modules/$krel" "$work/root/lib/modules/$krel"
rm -f "$work/root/lib/modules/$krel/build" "$work/root/lib/modules/$krel/source"
ln -s /usr/src/linux-6.18.60-Unraid "$work/root/lib/modules/$krel/build"
ln -s /usr/src/linux-6.18.60-Unraid "$work/root/lib/modules/$krel/source"
(cd "$work/root" && find . -print0 | LC_ALL=C sort -z | cpio -o -0 -H newc --quiet) > "$work/main.cpio"
case $kind in
  xz) xz --check=crc32 -9 -T0 -c "$work/main.cpio" > "$work/main.compressed";;
  zstd) zstd -19 -T0 -c "$work/main.cpio" > "$work/main.compressed";;
  gzip) gzip -9 -c "$work/main.cpio" > "$work/main.compressed";;
esac
cat "$work/early.cpio" "$work/main.compressed" > "$output"
echo "Assembled local bzroot: $output"
sha256sum "$output"
echo "Do not upload or redistribute: output contains files from the stock Unraid bzroot."
