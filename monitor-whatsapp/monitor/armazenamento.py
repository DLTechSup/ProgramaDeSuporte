"""Pasta do dia e gravacao das fotos (sem duplicar: compara o conteudo)."""
from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import date
from pathlib import Path

from .referencia import nome_seguro


def nome_pasta_grupo(nome: str) -> str:
    """Nome do grupo como pasta: tira emojis e caracteres proibidos no Windows (ex.: 'PROGRAMAÇÃO ✨📷💰' -> 'PROGRAMAÇÃO')."""
    limpo = "".join(c for c in nome if ord(c) < 0x2000 or 0x2190 > ord(c) > 0x1FFF).strip()
    limpo = "".join(c for c in limpo if c.isprintable() and unicodedata.category(c) not in ("So", "Sk", "Cs", "Cn"))
    return nome_seguro(re.sub(r"\s+", " ", limpo)) if limpo else "Grupo"


def pasta_do_dia(base: Path, grupo: str, dia: date | None = None) -> Path:
    """<pasta principal>/<grupo>/<dd-mm-aaaa>: cada grupo tem a sua pasta e nada se mistura."""
    dia = dia or date.today()
    p = Path(base) / nome_pasta_grupo(grupo) / dia.strftime("%d-%m-%Y")
    p.mkdir(parents=True, exist_ok=True)
    return p


def extensao(dados: bytes) -> str:
    if dados[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if dados[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if dados[:4] == b"RIFF" and dados[8:12] == b"WEBP":
        return ".webp"
    return ".jpg"


def salvar_fotos(pasta_dia: Path, nome_pasta: str, fotos: list[bytes], prefixo: str = "") -> tuple[Path, int]:
    """Salva em <dia>/<nome_pasta>/<prefixo>foto_01.jpg... Pula foto que ja esta na pasta. Devolve (pasta, quantas novas)."""
    destino = Path(pasta_dia) / nome_seguro(nome_pasta)
    destino.mkdir(parents=True, exist_ok=True)
    existentes = {hashlib.sha1(f.read_bytes()).hexdigest() for f in destino.iterdir() if f.is_file()}
    numero = sum(1 for f in destino.iterdir() if f.is_file() and f.name.startswith(prefixo + "foto_"))
    novas = 0
    for dados in fotos:
        h = hashlib.sha1(dados).hexdigest()
        if len(dados) < 3000 or h in existentes:   # menor que 3 KB = miniatura/icone, nao e foto
            continue
        numero += 1
        (destino / f"{prefixo}foto_{numero:02d}{extensao(dados)}").write_bytes(dados)
        existentes.add(h)
        novas += 1
    return destino, novas


def anexar_mensagens(pasta_dia: Path, linhas: list[str], nome_arquivo: str = "mensagens.txt") -> Path:
    """Acrescenta linhas ao .txt do dia (UTF-8, abre em qualquer editor). Nunca apaga nem reescreve o que ja foi salvo."""
    arq = Path(pasta_dia) / nome_arquivo
    with open(arq, "a", encoding="utf-8") as f:
        for linha in linhas:
            f.write(linha.rstrip("\n") + "\n")
    return arq
