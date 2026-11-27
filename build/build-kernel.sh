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
  amd)
    KREL=6.18.60-Unraid-p2p-amd
    LOCALVERSION=-Unraid-p2p-amd
    source="$(dirname "$0")/intel"
    ;;
  intel-741)
    KREL=6.18.64-Unraid-p2p-exp-intel
    LOCALVERSION=-Unraid-p2p-exp-intel
    source="$(dirname "$0")/7.4.1"
    ;;
  nvidia-741)
    KREL=6.18.64-Unraid-p2p-exp-nvidia580.196.07
    LOCALVERSION=-Unraid-p2p-exp-nvidia580.196.07
    source="$(dirname "$0")/7.4.1"
    ;;
  amd-741)
    KREL=6.18.64-Unraid-p2p-exp-amd
    LOCALVERSION=-Unraid-p2p-exp-amd
    source="$(dirname "$0")/7.4.1"
    ;;
  *) echo "Usage: $0 {intel|nvidia|amd|intel-741|nvidia-741|amd-741}" >&2; exit 2;;
esac
: "${KERNEL_SRC:?Set KERNEL_SRC to a clean extracted Linux source tree}"
: "${OUTPUT_DIR:?Set OUTPUT_DIR to an empty output directory}"
[[ -d $KERNEL_SRC && -d $OUTPUT_DIR && -z "$(find "$OUTPUT_DIR" -mindepth 1 -print -quit)" ]] || { echo "Source missing or OUTPUT_DIR is not empty" >&2; exit 1; }
expected_version=6.18.60
if [[ $variant == *-741 ]]; then
  expected_version=6.18.64
fi
[[ $(make -s -C "$KERNEL_SRC" kernelversion) == "$expected_version" ]] || { echo "Expected Linux $expected_version source" >&2; exit 1; }
if [[ $variant == *-741 ]]; then
  for key in CONFIG_PCI_P2PDMA CONFIG_DMABUF_MOVE_NOTIFY CONFIG_DRM_AMDGPU CONFIG_HSA_AMD CONFIG_HSA_AMD_SVM; do
    if ! grep -q "^${key}=" "$source/config" && ! grep -qx "# ${key} is not set" "$source/config"; then
      echo "Missing expected 7.4.1 config key: ${key}" >&2
      exit 1
    fi
  done
  cp "$source/config" "$KERNEL_SRC/.config"
else
  cp "$source"/config "$KERNEL_SRC/.config"
fi
if [[ $variant == *-741 ]]; then
  "$KERNEL_SRC/scripts/config" --file "$KERNEL_SRC/.config" --module DRM_AMDGPU
  "$KERNEL_SRC/scripts/config" --file "$KERNEL_SRC/.config" --enable HSA_AMD --enable HSA_AMD_SVM
fi
if [[ $variant != *-741 ]]; then
  cp "$source"/src/unraid-drivers/md/*.c "$source"/src/unraid-drivers/md/*.h "$KERNEL_SRC/drivers/md/"
fi
for patch in "$source"/src/*.patch; do patch -d "$KERNEL_SRC" -p1 --forward < "$patch"; done
"$KERNEL_SRC/scripts/config" --file "$KERNEL_SRC/.config" --set-str LOCALVERSION "$LOCALVERSION" --enable PCI_P2PDMA --enable DMABUF_MOVE_NOTIFY
if [[ $variant == amd || $variant == amd-741 ]]; then
  "$KERNEL_SRC/scripts/config" --file "$KERNEL_SRC/.config" --enable HSA_AMD_P2P
fi
make -C "$KERNEL_SRC" olddefconfig
make -C "$KERNEL_SRC" -s include/config/kernel.release
actual=$(<"$KERNEL_SRC/include/config/kernel.release")
[[ $actual == "$KREL" ]] || { echo "Expected $KREL, got $actual" >&2; exit 1; }
grep -qx 'CONFIG_PCI_P2PDMA=y' "$KERNEL_SRC/.config"
grep -qx 'CONFIG_DMABUF_MOVE_NOTIFY=y' "$KERNEL_SRC/.config"
if [[ $variant == amd || $variant == amd-741 ]]; then
  grep -qx 'CONFIG_DRM_AMDGPU=m' "$KERNEL_SRC/.config"
  grep -qx 'CONFIG_HSA_AMD=y' "$KERNEL_SRC/.config"
  grep -qx 'CONFIG_HSA_AMD_P2P=y' "$KERNEL_SRC/.config"
fi
make -C "$KERNEL_SRC" -j"$(nproc)" bzImage modules
make -C "$KERNEL_SRC" INSTALL_MOD_PATH="$OUTPUT_DIR/modules" INSTALL_MOD_STRIP=1 modules_install
cp "$KERNEL_SRC/arch/x86/boot/bzImage" "$OUTPUT_DIR/bzImage"
echo "Built kernel image and modules for $KREL in $OUTPUT_DIR"
