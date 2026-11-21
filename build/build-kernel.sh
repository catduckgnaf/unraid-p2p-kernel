#!/usr/bin/env bash
set -euo pipefail
variant=${1:-}
case "$variant" in
  intel)
    KREL=6.18.60-Unraid-p2p
    LOCALVERSION=-Unraid-p2p
    source="$(dirname "$0")/intel"
    ;;
  nvidia)
    KREL=6.18.60-Unraid-p2p-nvidia580.196.07
    LOCALVERSION=-Unraid-p2p-nvidia580.196.07
    source="$(dirname "$0")/nvidia"
    ;;
  *) echo "Usage: $0 {intel|nvidia}" >&2; exit 2;;
esac
: "${KERNEL_SRC:?Set KERNEL_SRC to a clean extracted Linux 6.18.60 source tree}"
: "${OUTPUT_DIR:?Set OUTPUT_DIR to an empty output directory}"
[[ -d $KERNEL_SRC && -d $OUTPUT_DIR && -z "$(find "$OUTPUT_DIR" -mindepth 1 -print -quit)" ]] || { echo "Source missing or OUTPUT_DIR is not empty" >&2; exit 1; }
[[ $(make -s -C "$KERNEL_SRC" kernelversion) == 6.18.60 ]] || { echo "Expected Linux 6.18.60 source" >&2; exit 1; }
for patch in "$source"/src/*.patch; do patch -d "$KERNEL_SRC" -p1 --forward < "$patch"; done
cp "$source"/src/unraid-drivers/md/*.c "$source"/src/unraid-drivers/md/*.h "$KERNEL_SRC/drivers/md/"
cp "$source/config" "$KERNEL_SRC/.config"
"$KERNEL_SRC/scripts/config" --file "$KERNEL_SRC/.config" --set-str LOCALVERSION "$LOCALVERSION" --enable PCI_P2PDMA --enable DMABUF_MOVE_NOTIFY
make -C "$KERNEL_SRC" olddefconfig
make -C "$KERNEL_SRC" -s include/config/kernel.release
actual=$(<"$KERNEL_SRC/include/config/kernel.release")
[[ $actual == "$KREL" ]] || { echo "Expected $KREL, got $actual" >&2; exit 1; }
grep -qx 'CONFIG_PCI_P2PDMA=y' "$KERNEL_SRC/.config"
grep -qx 'CONFIG_DMABUF_MOVE_NOTIFY=y' "$KERNEL_SRC/.config"
make -C "$KERNEL_SRC" -j"$(nproc)" bzImage modules
make -C "$KERNEL_SRC" INSTALL_MOD_PATH="$OUTPUT_DIR/modules" INSTALL_MOD_STRIP=1 modules_install
cp "$KERNEL_SRC/arch/x86/boot/bzImage" "$OUTPUT_DIR/bzImage"
echo "Built kernel image and modules for $KREL in $OUTPUT_DIR"
