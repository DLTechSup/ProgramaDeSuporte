"""Leitura de texto das fotos (OCR) com RapidOCR ou, se faltar, Tesseract."""
from __future__ import annotations

from typing import Callable

from PIL import Image, ImageOps

LimiteLado = 2000


def _preparar(img: Image.Image) -> Image.Image:
    img = ImageOps.exif_transpose(img).convert("RGB")
    w, h = img.size
    maior = max(w, h)
    if maior > LimiteLado:
        f = LimiteLado / maior
        img = img.resize((int(w * f), int(h * f)), Image.LANCZOS)
    return img


def criar_motor() -> Callable[[Image.Image], str]:
    """Devolve uma função imagem -> texto. Levanta RuntimeError se não houver OCR."""
    erros = []
    try:
        import numpy as np
        from rapidocr_onnxruntime import RapidOCR

        motor = RapidOCR()

        def ler(img: Image.Image) -> str:
            resultado, _ = motor(np.array(img))
            return "\n".join(item[1] for item in (resultado or []))

        return ler
    except Exception as e:  # noqa: BLE001
        erros.append(f"RapidOCR: {e}")
    try:
        import pytesseract

        pytesseract.get_tesseract_version()
        try:
            langs = pytesseract.get_languages()
        except Exception:  # noqa: BLE001
            langs = []
        lang = "por+eng" if "por" in langs else "eng"
        return lambda img: pytesseract.image_to_string(img, lang=lang, config="--psm 11")
    except Exception as e:  # noqa: BLE001
        erros.append(f"Tesseract: {e}")
    raise RuntimeError(
        "Nenhum motor de OCR disponível. Rode: pip install -r requirements.txt\n" + "\n".join(erros)
    )


def ler_foto(ler: Callable[[Image.Image], str], caminho, *, tentar_girar: bool = True):
    """Gera variações da foto (original, contraste, girada) e devolve o texto lido de cada uma,
    em ordem de custo. É um gerador: quem consome para quando já achou marca e referência."""
    with Image.open(caminho) as bruta:
        img = _preparar(bruta)
    yield ler(img)
    yield ler(ImageOps.autocontrast(ImageOps.grayscale(img)).convert("RGB"))
    if tentar_girar:
        for ang in (90, 270):
            yield ler(img.rotate(ang, expand=True))


def ler_bytes(ler, dados: bytes, *, tentar_girar: bool = True):
    """Como ler_foto, mas a partir dos bytes da imagem (foto que veio do WhatsApp)."""
    import io
    return ler_foto(ler, io.BytesIO(dados), tentar_girar=tentar_girar)
