"""Regras de referencia por marca (ex.: cortar o codigo da cor no final). Arquivo editavel: regras_referencia.txt."""
from __future__ import annotations

import re
from pathlib import Path

from .config import RAIZ
from .marcas import compactar

ARQUIVO = RAIZ / "regras_referencia.txt"

MODELO = """# REGRAS DE REFERENCIA POR MARCA
# Serve para cortar do FINAL da referencia o que e so a cor (voce nao usa).
# Formato, uma por linha:   MARCA | padrao do que cortar no final
#   N = um numero    L = uma letra    qualquer outro sinal vale como esta
# Exemplos:
#   PEGADA | -NN      corta '-01' no final:   133 161-01  ->  133 161
#   MODARE | .NNN     corta '.106' no final:  7226.106   ->  7226
# A referencia completa que veio na etiqueta continua aparecendo na lista (como observacao).
# Linhas que comecam com # sao ignoradas. Sem regra para a marca = a referencia fica completa.

PEGADA | -NN
"""


def padrao_para_regex(padrao: str) -> str:
    """Converte o padrao em regex: N = numero, L = letra, o resto vale literal (ex.: -NN)."""
    partes = []
    for c in padrao.strip():
        partes.append(r"\d" if c == "N" else (r"[A-Za-z]" if c == "L" else re.escape(c)))
    return "".join(partes) + r"\s*$"


class RegrasReferencia:
    def __init__(self, regras: dict[str, str] | None = None) -> None:
        self.regras = regras or {}          # marca (compactada) -> regex

    @classmethod
    def carregar(cls, arquivo: Path = ARQUIVO) -> "RegrasReferencia":
        if not arquivo.exists():
            try:
                arquivo.write_text(MODELO, encoding="utf-8")
            except OSError:
                pass
        texto = arquivo.read_text(encoding="utf-8") if arquivo.exists() else MODELO
        regras = {}
        for linha in texto.splitlines():
            linha = linha.strip()
            if not linha or linha.startswith("#") or "|" not in linha:
                continue
            marca, padrao = (x.strip() for x in linha.split("|", 1))
            if marca and padrao:
                regras[compactar(marca)] = padrao_para_regex(padrao)
        return cls(regras)

    def aplicar(self, marca: str | None, referencia: str) -> tuple[str, str]:
        """(referencia para usar, referencia completa se foi cortada senao '')."""
        rx = self.regras.get(compactar(marca or ""))
        if not rx:
            return referencia, ""
        cortada = re.sub(rx, "", referencia).strip(" .-/")
        if cortada and cortada != referencia:
            return cortada, referencia
        return referencia, ""
