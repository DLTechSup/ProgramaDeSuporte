"""Legenda do Grupo A (foto + marca + referencia): separa a marca da referencia."""
from __future__ import annotations

import re
from dataclasses import dataclass

from .marcas import compactar, detectar_marca
from .referencia import nome_seguro


@dataclass
class Demanda:
    marca: str | None       # None = nao reconhecida
    referencia: str | None  # None = nao achei
    original: str = ""

    @property
    def completa(self) -> bool:
        return bool(self.marca and self.referencia)

    @property
    def nome_pasta(self) -> str:
        return nome_seguro(f"{self.marca} {self.referencia}")


def dividir_legenda(legenda: str, marcas: dict[str, list[str]]) -> Demanda:
    """'BEIRA RIO 8513.115' -> (BEIRA RIO, 8513.115). Referencia = tudo que nao e a marca, do jeito que veio."""
    texto = re.sub(r"\s+", " ", (legenda or "").replace("\n", " ")).strip()
    if not texto:
        return Demanda(None, None, "")
    marca = detectar_marca(texto, marcas)
    if marca:
        resto = _tirar_marca(texto, marcas[marca] + [marca])
        return Demanda(marca.upper(), resto or None, texto)
    # marca desconhecida: se ha um codigo com numero, o que vem antes dele e a marca
    m = re.search(r"(?<!\S)(\S*\d\S*(?:\s\S*\d\S*)?)\s*$", texto)
    if m and m.start() > 0:
        return Demanda(texto[:m.start()].strip().upper() or None, m.group(1).strip(), texto)
    return Demanda(None, texto, texto)


def _tirar_marca(texto: str, apelidos: list[str]) -> str:
    """Remove da legenda as palavras que formam a marca (tolera acentos, caixa e espacos)."""
    palavras = texto.split()
    for ap in sorted(apelidos, key=len, reverse=True):
        alvo = compactar(ap)
        for i in range(len(palavras)):
            acumulado = ""
            for j in range(i, len(palavras)):
                acumulado += compactar(palavras[j])
                if acumulado == alvo:
                    return " ".join(palavras[:i] + palavras[j + 1:]).strip(" -:.")
                if len(acumulado) >= len(alvo):
                    break
    # marca achada por aproximacao (erro de digitacao): remove as primeiras palavras equivalentes em tamanho
    n_marca = max(1, len(apelidos[0].split()))
    return " ".join(palavras[n_marca:]).strip(" -:.")
