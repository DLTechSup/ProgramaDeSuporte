"""Gera assets/icone.ico e icone.png: cartoes numerados (01, 02) sobre fundo azul. uso: python tools/gerar_icone.py"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

T = 1024
SAIDA = Path(__file__).resolve().parent.parent / "assets"


def gradiente(topo=(63, 128, 245), base=(32, 80, 200)) -> Image.Image:
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
    # cartao de tras (meio transparente) e cartao da frente
    d.rounded_rectangle((int(T * .26), int(T * .17), int(T * .86), int(T * .62)), radius=int(T * .07), fill=(255, 255, 255, 120))
    d.rounded_rectangle((int(T * .14), int(T * .33), int(T * .74), int(T * .83)), radius=int(T * .08), fill="white")
    fonte = ImageFont.load_default(size=int(T * .30))
    d.text((int(T * .44), int(T * .58)), "01", font=fonte, fill=(37, 89, 196), anchor="mm")
    # tracinhos de "nome" no cartao
    d.rounded_rectangle((int(T * .22), int(T * .70), int(T * .58), int(T * .73)), radius=12, fill=(190, 205, 240))
    d.rounded_rectangle((int(T * .22), int(T * .75), int(T * .46), int(T * .78)), radius=12, fill=(215, 225, 247))
    return base


if __name__ == "__main__":
    SAIDA.mkdir(exist_ok=True)
    img = desenhar()
    img.resize((256, 256), Image.LANCZOS).save(SAIDA / "icone.png")
    img.save(SAIDA / "icone.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("icone gerado")
