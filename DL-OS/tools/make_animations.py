#!/usr/bin/env python3
"""Renderiza as animações do DL OS (mesma matemática do tema Plymouth):
   design/boot-animado.mp4 (prévia) e branding/wallpaper-animado.mp4 (papel de parede em loop)."""
import math, pathlib, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFont
ROOT = pathlib.Path(__file__).resolve().parent.parent
P = ROOT / "rootfs/usr/share/plymouth/themes/dlos"
BG = Image.open(ROOT / "branding/art/boot-logo.png").convert("RGB")
GLOW, SWEEP, SPARK = [Image.open(P / n).convert("RGBA") for n in ("glow.png", "sweep.png", "spark.png")]
fr = lambda x: x - math.floor(x)
LINES = ["KERNEL CORE", "LOGIC PATHWAYS", "REGISTERS", "FILE SYSTEM", "HARDWARE", "GRAPHICS..."]

def alpha(img, a):
    img = img.copy(); img.putalpha(img.getchannel("A").point(lambda v: int(v * max(0, min(1, a))))); return img

def frame(t, W, H, boot=True, loop=False):
    # loop=True: todas as frequências são múltiplos de 2π/10s => vídeo de 10 s emenda perfeitamente
    w = 2 * math.pi / 10
    dx, dy, gl, sw_ = (w, w, w * 4, 2) if loop else (.35, .27, 2.2, 1)
    r = max(W / BG.width, H / BG.height) * 1.04
    bw0, bh0 = int(BG.width * r), int(BG.height * r)
    ox, oy = (W - bw0) / 2, (H - bh0) / 2
    img = Image.new("RGBA", (W, H), (4, 10, 23, 255))
    big = BG.resize((bw0, bh0), Image.LANCZOS).convert("RGBA")
    img.paste(big, (int(ox + math.sin(t * dx) * (bw0 - W) / 2), int(oy + math.cos(t * dy) * (bh0 - H) / 2)))
    gs = int(min(W, H) * .55); lx, ly = ox + bw0 * .503, oy + bh0 * .34
    g = alpha(GLOW.resize((gs, gs)), .30 + .25 * math.sin(t * gl)); img.alpha_composite(g, (int(lx - gs / 2), int(ly - gs / 2)))
    ph = fr(t / 5); sw = alpha(SWEEP.resize((int(W * .12), int(H * 1.1))), .7 * math.sin(ph * math.pi))
    img.alpha_composite(sw, (int(-W * .2 + ph * W * 1.4), int(-H * .05)))
    for i in range(22):
        seed = fr(math.sin(i * 12.9898) * 43758.5453); st = fr(t * ((1 + i % 3) / 10 if loop else (.05 + seed * .06)) + seed); s = 8 + (i % 3) * 4
        sp = alpha(SPARK.resize((s, s)), math.sin(st * math.pi) * .9)
        img.alpha_composite(sp, (int(W * (.05 + .9 * fr(seed * 7.3)) + math.sin((t * w * 2 if loop else t) + i) * 12), int(H * (1 - st * 1.05))))
    if boot:
        d = ImageDraw.Draw(img); bw, bx, by = W * .36, W * .32, H * .955
        p = max(.02, t / (t + 8))
        d.rounded_rectangle((bx, by, bx + bw, by + 8), 4, fill=(28, 48, 80, 255))
        d.rounded_rectangle((bx, by, bx + bw * p, by + 8), 4, fill=(34, 200, 255, 255))
        try: f = ImageFont.truetype("DejaVuSansMono.ttf", max(10, int(H * .028)))
        except OSError: f = ImageFont.load_default()
        n = min(6, int(t / 1.3) + 1)
        for i in range(n):
            busy = i == n - 1 and n == 6
            d.text((W * .04, H * .70 + i * H * .04), ("[ BUSY ] " if busy else "[  OK  ] ") + LINES[i],
                   font=f, fill=(255, 242, 77) if busy else (115, 255, 166))
    return img.convert("RGB")

def main():
    out = ROOT
    # 1) prévia do boot (10 s) em MP4
    tmp0 = pathlib.Path(tempfile.mkdtemp())
    for i in range(300):
        frame(i / 30, 960, 540).save(tmp0 / f"f{i:04d}.jpg", quality=90)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "30", "-i", str(tmp0 / "f%04d.jpg"),
        "-c:v", "libx264", "-crf", "24", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out / "design/boot-animado.mp4")], check=True)
    # 2) papel de parede em loop (sem barra/log): 10 s, período do feixe = 5 s
    tmp = pathlib.Path(tempfile.mkdtemp())
    for i in range(240):
        frame(i / 24, 1280, 720, boot=False, loop=True).save(tmp / f"f{i:04d}.jpg", quality=92)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "24", "-i", str(tmp / "f%04d.jpg"),
        "-c:v", "libx264", "-crf", "26", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out / "branding/wallpaper-animado.mp4")], check=True)
    print("ok")

if __name__ == "__main__":
    main()
