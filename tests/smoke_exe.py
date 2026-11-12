"""Gera uma foto de teste com texto e cria a pasta para o teste do .exe."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

pasta = Path(sys.argv[1]); pasta.mkdir(parents=True, exist_ok=True)
for nome, txt in (("a.jpg", "BEIRA RIO  REF: 123.456"), ("b.jpg", "BEIRA RIO  REF: 123.456")):
    img = Image.new("RGB", (900, 300), "white")
    ImageDraw.Draw(img).text((40, 100), txt, fill="black", font=ImageFont.load_default(size=56))
    img.save(pasta / nome)
