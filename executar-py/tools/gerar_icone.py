"""Gera assets/icone.ico e icone.png: uma seta 'play' sobre o logo do Python simplificado. uso: python tools/gerar_icone.py"""
from pathlib import Path
from PIL import Image, ImageDraw

T = 1024
SAIDA = Path(__file__).resolve().parent.parent / "assets"


def gradiente(topo=(53, 114, 165), base=(27, 64, 99)):
    img = Image.new("RGB", (T, T))
    px = img.load()
    for y in range(T):
        t = y / (T - 1)
        cor = tuple(int(topo[i] + (base[i] - topo[i]) * t) for i in range(3))
        for x in range(T):
            px[x, y] = cor
    return img


def desenhar() -> Image.Image:
    mascara = Image.new("L", (T, T), 0)
    ImageDraw.Draw(mascara).rounded_rectangle((0, 0, T - 1, T - 1), radius=int(T * .22), fill=255)
    base = Image.new("RGBA", (T, T), (0, 0, 0, 0))
    base.paste(gradiente().convert("RGBA"), mask=mascara)
    d = ImageDraw.Draw(base)
    d.ellipse((int(T * .14), int(T * .14), int(T * .86), int(T * .86)), fill="white")
    cx, cy, r = T * .5, T * .5, T * .22
    d.polygon([(cx - r * .55, cy - r), (cx - r * .55, cy + r), (cx + r * 1.1, cy)], fill=(27, 64, 99))
    return base


if __name__ == "__main__":
    SAIDA.mkdir(exist_ok=True)
    img = desenhar()
    img.resize((256, 256), Image.LANCZOS).save(SAIDA / "icone.png")
    img.save(SAIDA / "icone.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("icone gerado")
