"""Extração do número de referência a partir do texto da etiqueta."""
from __future__ import annotations

import re

# Um "código": começa com dígito, tem pelo menos 4 dígitos, aceita . - / entre eles.
_CODIGO = r"\d[\d.\-/ ]{2,24}\d"
_RE_CODIGO = re.compile(_CODIGO)
_RE_APOS_ROTULO = re.compile(
    r"(?:REF(?:ER[EÊ]NCIA)?|REFER|ARTIGO|ART|MOD(?:ELO)?)\s*[.:;#°ºN\-]*\s*(" + _CODIGO + r")",
    re.IGNORECASE,
)
_RE_ROTULO_COM_LETRAS = re.compile(
    r"(?:REF(?:ER[EÊ]NCIA)?)\s*[.:;#°º\-]*\s*([A-Z]{0,3}\s?\d[\w.\-/]{2,24})", re.IGNORECASE
)


def _limpar(cod: str) -> str:
    cod = re.sub(r"\s+", "", cod)
    return cod.strip(".-/")


def _digitos(cod: str) -> int:
    return sum(c.isdigit() for c in cod)


def _parece_codigo_de_barras(cod: str) -> bool:
    # EAN/UPC (8, 12, 13, 14 dígitos corridos) não é referência.
    puro = re.sub(r"\D", "", cod)
    return puro == cod and len(puro) in (8, 12, 13, 14)


def extrair_referencia(texto: str) -> str | None:
    """Devolve a referência (como lida, ex.: '4235.101') ou None."""
    if not texto:
        return None
    linhas = texto.replace("\r", "\n")

    # 1) Número logo depois de "REF", "REFERÊNCIA", "ARTIGO", "MODELO".
    for padrao in (_RE_APOS_ROTULO, _RE_ROTULO_COM_LETRAS):
        for m in padrao.finditer(linhas):
            cod = _limpar(m.group(1))
            if _digitos(cod) >= 4 and not _parece_codigo_de_barras(cod):
                return cod.upper()

    # 2) Rótulo numa linha e número na linha seguinte.
    partes = [p.strip() for p in linhas.split("\n") if p.strip()]
    for i, p in enumerate(partes[:-1]):
        if re.fullmatch(r"(REF\w*|ARTIGO|MODELO)[\s.:]*", p, re.IGNORECASE):
            m = _RE_CODIGO.search(partes[i + 1])
            if m:
                cod = _limpar(m.group(0))
                if _digitos(cod) >= 4 and not _parece_codigo_de_barras(cod):
                    return cod.upper()

    # 3) Sem rótulo: o código com ponto/hífen mais "forte" do texto.
    candidatos = []
    for m in _RE_CODIGO.finditer(linhas):
        cod = _limpar(m.group(0))
        if _digitos(cod) < 4 or _parece_codigo_de_barras(cod):
            continue
        if re.fullmatch(r"\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4}", cod):  # data
            continue
        peso = _digitos(cod) + (3 if re.search(r"[.\-]", cod) else 0)
        candidatos.append((peso, cod))
    if candidatos:
        return max(candidatos, key=lambda t: t[0])[1].upper()
    return None


def chave_referencia(ref: str) -> str:
    """Chave de agrupamento: ignora pontuação ('123.456' == '123-456')."""
    return re.sub(r"[^A-Z0-9]", "", ref.upper())


def nome_seguro(texto: str) -> str:
    """Remove caracteres proibidos em nomes de pasta (Windows/Mac/Linux)."""
    texto = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", texto).strip().rstrip(". ")
    return texto or "SEM_NOME"
