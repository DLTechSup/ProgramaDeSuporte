"""Gera assets/icone.ico e icone.png: uma camera/mira de selecao. uso: python tools/gerar_icone.py"""
from pathlib import Path
from PIL import Image, ImageDraw

T = 1024
SAIDA = Path(__file__).resolve().parent.parent / "assets"


def gradiente(topo=(235, 85, 60), base=(190, 45, 25)):
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
    # cantos de selecao (como uma mira de captura de tela)
    w, m, l = 14, 150, 230
    for x, y, dx, dy in ((m, m, 1, 1), (T - m, m, -1, 1), (m, T - m, 1, -1), (T - m, T - m, -1, -1)):
        x0, x1 = sorted((x, x + dx * l)); y0, y1 = sorted((y, y + dy * w))
        d.rectangle((x0, y0, x1, y1), fill="white")
        x0, x1 = sorted((x, x + dx * w)); y0, y1 = sorted((y, y + dy * l))
        d.rectangle((x0, y0, x1, y1), fill="white")
    d.ellipse((T * .5 - 70, T * .5 - 70, T * .5 + 70, T * .5 + 70), outline="white", width=22)
    return base


if __name__ == "__main__":
    SAIDA.mkdir(exist_ok=True)
    img = desenhar()
    img.resize((256, 256), Image.LANCZOS).save(SAIDA / "icone.png")
    img.save(SAIDA / "icone.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("icone gerado")
