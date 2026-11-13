"""Gera assets/icone.ico e icone.png (balao de conversa com 'visto' sobre fundo verde-azulado). uso: python tools/gerar_icone.py"""
from pathlib import Path
from PIL import Image, ImageDraw

T = 1024
SAIDA = Path(__file__).resolve().parent.parent / "assets"


def gradiente(tam: int, topo=(20, 150, 125), base=(10, 98, 82)) -> Image.Image:
    img = Image.new("RGB", (tam, tam))
    px = img.load()
    for y in range(tam):
        t = y / (tam - 1)
        cor = tuple(int(topo[i] + (base[i] - topo[i]) * t) for i in range(3))
        for x in range(tam):
            px[x, y] = cor
    return img


def desenhar() -> Image.Image:
    fundo = gradiente(T).convert("RGBA")
    mascara = Image.new("L", (T, T), 0)
    ImageDraw.Draw(mascara).rounded_rectangle((0, 0, T - 1, T - 1), radius=int(T * 0.22), fill=255)
    base = Image.new("RGBA", (T, T), (0, 0, 0, 0))
    base.paste(fundo, mask=mascara)
    d = ImageDraw.Draw(base)
    # balao branco
    bx0, by0, bx1, by1 = int(T * .18), int(T * .22), int(T * .82), int(T * .68)
    d.rounded_rectangle((bx0, by0, bx1, by1), radius=int(T * .12), fill="white")
    d.polygon([(int(T * .30), by1 - 10), (int(T * .30), int(T * .82)), (int(T * .46), by1 - 10)], fill="white")
    # "visto" verde dentro do balao
    cor = (12, 112, 92)
    w = int(T * .06)
    d.line([(int(T * .32), int(T * .46)), (int(T * .45), int(T * .58)), (int(T * .68), int(T * .33))], fill=cor, width=w, joint="curve")
    for p in ((.32, .46), (.45, .58), (.68, .33)):
        d.ellipse((p[0] * T - w / 2, p[1] * T - w / 2, p[0] * T + w / 2, p[1] * T + w / 2), fill=cor)
    # pequeno cartao de foto no canto (indica fotos salvas)
    d.rounded_rectangle((int(T * .60), int(T * .60), int(T * .86), int(T * .84)), radius=int(T * .04), fill=(255, 255, 255), outline=(10, 98, 82), width=int(T * .018))
    d.polygon([(int(T * .63), int(T * .80)), (int(T * .71), int(T * .68)), (int(T * .76), int(T * .75)), (int(T * .80), int(T * .70)), (int(T * .83), int(T * .80))], fill=(20, 150, 125))
    d.ellipse((int(T * .665), int(T * .625), int(T * .705), int(T * .665)), fill=(20, 150, 125))
    return base


if __name__ == "__main__":
    SAIDA.mkdir(exist_ok=True)
    img = desenhar()
    img.resize((256, 256), Image.LANCZOS).save(SAIDA / "icone.png")
    img.save(SAIDA / "icone.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("icone gerado")
