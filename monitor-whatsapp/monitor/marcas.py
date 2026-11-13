"""Lista de marcas conhecidas e seus apelidos (como aparecem nas etiquetas).

Para adicionar uma marca sem mexer no código, crie um arquivo `marcas.txt`
ao lado de `separador.py`, uma marca por linha, apelidos separados por `|`:

    Beira Rio | BEIRA RIO | BEIRARIO
    Minha Marca Nova
"""
from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

MARCAS_PADRAO: dict[str, list[str]] = {
    "Beira Rio": ["Beira Rio", "BeiraRio"],
    "Dakota": ["Dakota"],
    "Via Jupiter": ["Via Jupiter", "ViaJupiter"],
    "BR Sport": ["BR Sport", "BRSport"],
    "Via Marte": ["Via Marte"],
    "Via Uno": ["Via Uno"],
    "Vizzano": ["Vizzano"],
    "Molekinha": ["Molekinha"],
    "Moleca": ["Moleca"],
    "Modare": ["Modare"],
    "Ramarim": ["Ramarim"],
    "Bottero": ["Bottero"],
    "Piccadilly": ["Piccadilly"],
    "Usaflex": ["Usaflex"],
    "Comfortflex": ["Comfortflex"],
    "Campesi": ["Campesi"],
    "Azaleia": ["Azaleia"],
    "Olympikus": ["Olympikus"],
    "Grendha": ["Grendha"],
    "Ipanema": ["Ipanema"],
    "Rider": ["Rider"],
    "Kidy": ["Kidy"],
    "Pegada": ["Pegada"],
    "Democrata": ["Democrata"],
    "Cravo e Canela": ["Cravo e Canela"],
    "Arezzo": ["Arezzo"],
    "Schutz": ["Schutz"],
    "Actvitta": ["Actvitta", "Actvita"],
    "Bebecê": ["Bebecê", "Bebece"],
    "Maria's Shoes": ["Maria's Shoes", "Marias Shoes", "Maria Shoes"],
    "Santinelli": ["Santinelli"],
    "Renata Mello": ["Renata Mello"],
    "Di Valentini": ["Di Valentini", "Divalentini"],
    "Três Marias": ["Três Marias", "Tres Marias"],
    "Kolosh": ["Kolosh"],
    "Mizuno": ["Mizuno"],
    "Stir": ["Stir"],
    "Sport Fire": ["Sport Fire"],
    "Improviso": ["Improviso"],
    "Adrun": ["Adrun"],
    "Molekinho": ["Molekinho"],
}


def compactar(texto: str) -> str:
    """MAIÚSCULO, sem acento e só letras/números."""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z0-9]", "", sem_acento.upper())


def carregar_marcas(arquivo: Path | None = None) -> dict[str, list[str]]:
    marcas = {k: list(v) for k, v in MARCAS_PADRAO.items()}
    if arquivo and arquivo.is_file():
        for linha in arquivo.read_text(encoding="utf-8").splitlines():
            linha = linha.strip()
            if not linha or linha.startswith("#"):
                continue
            nomes = [p.strip() for p in linha.split("|") if p.strip()]
            marcas.setdefault(nomes[0], [])
            marcas[nomes[0]].extend(nomes)
    return marcas


def detectar_marca(texto: str, marcas: dict[str, list[str]]) -> str | None:
    """Acha a marca no texto do OCR (tolera pequenos erros de leitura)."""
    alvo = compactar(texto)
    if not alvo:
        return None
    melhor, melhor_nota = None, 0.0
    for marca, apelidos in marcas.items():
        for apelido in apelidos:
            a = compactar(apelido)
            if not a:
                continue
            if a in alvo:
                nota = 1.0 + len(a) / 100  # acerto exato; apelido maior desempata
            elif len(a) >= 6:
                nota = _melhor_janela(a, alvo)
                if nota < 0.85:
                    continue
            else:
                continue
            if nota > melhor_nota:
                melhor, melhor_nota = marca, nota
    return melhor


def _melhor_janela(a: str, alvo: str) -> float:
    n = len(a)
    melhor = 0.0
    for tam in (n - 1, n, n + 1):
        for i in range(0, max(1, len(alvo) - tam + 1)):
            r = SequenceMatcher(None, a, alvo[i:i + tam]).ratio()
            if r > melhor:
                melhor = r
    return melhor
