#!/usr/bin/env bash
# Grava o DL OS num pendrive e cria uma partição persistente (arquivos, programas e
# configurações ficam salvos entre os boots). ATENÇÃO: APAGA TODO O PENDRIVE.
#   sudo ./tools/make-usb.sh DL-OS.iso /dev/sdX
set -euo pipefail
ISO="${1:?ISO}"; DEV="${2:?dispositivo, ex.: /dev/sdb}"
[ "$(id -u)" = 0 ] || { echo "Use sudo."; exit 1; }
[ -b "$DEV" ] || { echo "$DEV não é um dispositivo."; exit 1; }
[ "$(lsblk -dno RM "$DEV")" = 1 ] || { echo "$DEV não parece removível. Abortando por segurança."; exit 1; }
lsblk "$DEV"; read -rp "Isto APAGA $DEV. Digite o nome do dispositivo para confirmar: " c
[ "$c" = "$DEV" ] || { echo cancelado; exit 1; }
umount "$DEV"* 2>/dev/null || true
dd if="$ISO" of="$DEV" bs=4M status=progress conv=fsync
SIZE=$(stat -c %s "$ISO"); START=$(( (SIZE / 1048576) + 8 ))
parted -s "$DEV" mkpart primary ext4 "${START}MiB" 100%
sleep 2; P=$(lsblk -lnpo NAME "$DEV" | tail -1)
mkfs.ext4 -F -L dlos-data "$P"
M=$(mktemp -d); mount "$P" "$M"; echo "/ union" > "$M/persistence.conf"; umount "$M"
echo "Pronto! Boote pelo pendrive: seus dados ficam salvos."
