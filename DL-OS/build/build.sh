#!/usr/bin/env bash
# Gera a ISO do DL OS. Requer Debian/Ubuntu com root: sudo ./build/build.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; ROOT="$(dirname "$HERE")"
WORK="${WORK:-/tmp/dlos-build}"; OUT="${OUT:-$ROOT/out}"
[ "$(id -u)" = 0 ] || { echo "Execute como root (sudo)."; exit 1; }
apt-get update && apt-get install -y live-build debootstrap xorriso squashfs-tools python3

python3 "$ROOT/tools/gen_theme.py" --out "$ROOT/rootfs/usr/share/dlos"

rm -rf "$WORK"; mkdir -p "$WORK" "$OUT"; cd "$WORK"
lb config --distribution trixie --architectures amd64 \
  --archive-areas "main contrib non-free non-free-firmware" \
  --binary-images iso-hybrid --bootloaders "grub-efi syslinux" --bootappend-live "boot=live components quiet splash persistence persistence-label=dlos-data" \
  --iso-application "DL OS" --iso-publisher "Danilo Lira" --iso-volume "DLOS" \
  --image-name dlos --debian-installer none --apt-recommends false \
  --firmware-chroot true --win32-loader false --memtest none
cp -r "$HERE/config/package-lists/." config/package-lists/
mkdir -p config/hooks/live config/includes.chroot
cp "$HERE"/config/hooks/live/* config/hooks/live/
cp -r "$ROOT/rootfs/." config/includes.chroot/
lb build
mv -v ./*.iso "$OUT/DL-OS-$(date +%Y%m%d).iso"
