#!/usr/bin/env bash
# welcome.sh "Nome" saida.mp4 : cena de boas-vindas (3 s) com o nome do usuário, escrito e narrado.
set -euo pipefail
NAME="${1:?nome}"; OUT="${2:?saida}"; D=/usr/share/dlos/branding/intro
[ -d "$D" ] || D="$(dirname "$0")/../../../../branding/intro"
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
FONT=$(fc-match -f '%{file}' 'Inter:bold' 2>/dev/null || fc-match -f '%{file}' sans:bold)
# --- narração (offline). Piper (voz neural) se instalado; senão espeak-ng.
SAY="Bem-vindo, $NAME. O sistema está pronto."
if command -v piper >/dev/null && [ -f /usr/share/dlos/voice/pt_BR.onnx ]; then
  echo "$SAY" | piper -m /usr/share/dlos/voice/pt_BR.onnx -f "$T/voz.wav" >/dev/null 2>&1
else
  espeak-ng -v pt-br -s 160 -p 45 -w "$T/voz.wav" "$SAY"
fi
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$T/voz.wav")
LEN=$(python3 -c "print(max(3.0, float('$DUR') + 0.9))")
printf '%s' "Bem-vindo," > "$T/l1.txt"; printf '%s' "$NAME" > "$T/l2.txt"
# --- cena: fundo do vídeo + cartão de vidro + texto com fade
ffmpeg -loglevel error -y -loop 1 -framerate 24 -t "$LEN" -i "$D/bg.png" -i "$T/voz.wav" -filter_complex "
[0:v]crop=1190:670:45:25,scale=1344:756,zoompan=z='1+0.0004*on':d=1:s=1280x720:fps=24,eq=brightness=-0.08,
drawbox=x=300:y=150:w=680:h=250:color=0x061426@0.72:t=fill,
drawbox=x=300:y=150:w=680:h=250:color=0x22b8ff@0.9:t=2,
drawtext=fontfile=$FONT:textfile=$T/l1.txt:fontsize=34:fontcolor=0xbfe9ff:x=(w-text_w)/2:y=205:alpha='min(1,t/0.5)',
drawtext=fontfile=$FONT:textfile=$T/l2.txt:fontsize=64:fontcolor=white:x=(w-text_w)/2:y=255:alpha='min(1,max(0,(t-0.3)/0.5))',
drawtext=fontfile=$FONT:text='DLOS 1.0 Boole':fontsize=22:fontcolor=0x2de2e6:x=(w-text_w)/2:y=345:alpha='min(1,max(0,(t-0.6)/0.5))',
fade=t=in:d=0.4,fade=t=out:st=$(python3 -c "print($LEN-0.4)"):d=0.4[v];
[1:a]apad,atrim=0:$LEN,afade=t=out:st=$(python3 -c "print($LEN-0.4)"):d=0.4,volume=1.6[a]" \
  -map "[v]" -map "[a]" -c:v libx264 -crf 24 -pix_fmt yuv420p -r 24 -ar 44100 -ac 2 -c:a aac -b:a 128k "$OUT"
