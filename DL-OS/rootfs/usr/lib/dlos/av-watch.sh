#!/usr/bin/env bash
# Vigia pastas de download e mídias externas. Arquivos novos são escaneados (clamscan) em lote; infectados vão para quarentena.
Q=/var/lib/dlos/quarentena; LOG=/var/log/dlos-av.log; mkdir -p "$Q"; chmod 700 "$Q"
notify() { for u in $(loginctl list-sessions --no-legend | awk '{print $3}' | sort -u); do id=$(id -u "$u" 2>/dev/null) || continue
  runuser -u "$u" -- env DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$id/bus" notify-send -u critical "DL OS: ameaça bloqueada" "$1" 2>/dev/null; done; }
watch_dirs() { ls -d /home/*/Downloads /media /run/media /mnt /tmp 2>/dev/null; }
inotifywait -m -r -q -e close_write -e moved_to --format '%w%f' --exclude '(\.part|\.crdownload|\.tmp|/\.cache/)' $(watch_dirs) 2>/dev/null |
while read -r first; do
  batch=("$first")
  while read -r -t 8 more; do batch+=("$more"); [ ${#batch[@]} -ge 200 ] && break; done
  [ -d /var/lib/clamav ] && ls /var/lib/clamav/*.c[vl]d >/dev/null 2>&1 || { echo "$(date) banco de vírus ausente; conecte à internet (freshclam)" >> "$LOG"; continue; }
  files=(); for f in "${batch[@]}"; do [ -f "$f" ] && files+=("$f"); done; [ ${#files[@]} -gt 0 ] || continue
  out=$(nice -n 15 ionice -c3 clamscan --no-summary -i "${files[@]}" 2>/dev/null)
  while IFS= read -r l; do [ -n "$l" ] || continue; f=${l%%:*}; sig=${l#*: }
    dest="$Q/$(date +%s)-$(basename "$f")"; mv "$f" "$dest" 2>/dev/null && chmod 000 "$dest"
    echo "$(date) INFECTADO $f ($sig) -> $dest" >> "$LOG"; notify "$(basename "$f"): $sig (movido para a quarentena)"
  done <<< "$out"
done
