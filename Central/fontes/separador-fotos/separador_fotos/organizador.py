"""Fluxo principal: analisa as fotos de uma pasta e copia para pastas Marca - Referência."""
from __future__ import annotations

import csv
import shutil
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable

from .marcas import carregar_marcas, detectar_marca
from .ocr import criar_motor, ler_foto
from .referencia import chave_referencia, extrair_referencia, nome_seguro

EXTENSOES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
PASTA_NAO_IDENTIFICADAS = "_Nao_identificadas"


@dataclass
class Leitura:
    arquivo: Path
    marca: str | None = None
    referencia: str | None = None
    texto: str = ""
    erro: str | None = None


@dataclass
class Resultado:
    leituras: list[Leitura] = field(default_factory=list)
    pastas: dict[str, list[Path]] = field(default_factory=dict)


def listar_fotos(pasta: Path) -> list[Path]:
    """Só as fotos soltas na pasta (ignora as subpastas criadas por execuções anteriores)."""
    return sorted(p for p in pasta.iterdir() if p.is_file() and p.suffix.lower() in EXTENSOES)


def analisar_texto(texto: str, marcas) -> tuple[str | None, str | None]:
    return detectar_marca(texto, marcas), extrair_referencia(texto)


def analisar_foto(ler, caminho: Path, marcas) -> Leitura:
    leitura = Leitura(caminho)
    textos: list[str] = []
    try:
        for t in ler_foto(ler, caminho):
            textos.append(t)
            junto = "\n".join(textos)
            marca, ref = analisar_texto(junto, marcas)
            if marca and ref:
                break
        leitura.texto = "\n".join(textos)
        leitura.marca, leitura.referencia = analisar_texto(leitura.texto, marcas)
    except Exception as e:  # noqa: BLE001
        leitura.erro = str(e)
    return leitura


def agrupar(leituras: Iterable[Leitura]) -> dict[str, list[Path]]:
    """Nome da pasta -> fotos. Mesma marca + mesma referência (ignorando pontuação) = mesma pasta."""
    grupos: dict[tuple[str, str], list[Leitura]] = defaultdict(list)
    sem_id: list[Path] = []
    for l in leituras:
        if l.referencia and l.marca:
            grupos[(l.marca, chave_referencia(l.referencia))].append(l)
        else:
            sem_id.append(l.arquivo)
    pastas: dict[str, list[Path]] = {}
    for (marca, _), itens in sorted(grupos.items()):
        # grafia mais comum entre as fotos do grupo (corrige um erro isolado de OCR)
        ref = Counter(i.referencia for i in itens).most_common(1)[0][0]
        pastas[nome_seguro(f"{marca} - {ref}")] = [i.arquivo for i in itens]
    if sem_id:
        pastas[PASTA_NAO_IDENTIFICADAS] = sem_id
    return pastas


def copiar_para_pastas(base: Path, pastas: dict[str, list[Path]]) -> None:
    for nome, arquivos in pastas.items():
        destino_dir = base / nome
        destino_dir.mkdir(exist_ok=True)
        for arq in arquivos:
            destino = destino_dir / arq.name
            n = 1
            while destino.exists():
                destino = destino_dir / f"{arq.stem}_{n}{arq.suffix}"
                n += 1
            shutil.copy2(arq, destino)  # cópia: o original permanece na pasta


def salvar_relatorio(base: Path, leituras: list[Leitura], pastas: dict[str, list[Path]]) -> Path:
    destino_por_arquivo = {a: n for n, arqs in pastas.items() for a in arqs}
    caminho = base / "relatorio_separacao.csv"
    with open(caminho, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["foto", "marca", "referencia", "pasta", "erro"])
        for l in leituras:
            w.writerow([l.arquivo.name, l.marca or "", l.referencia or "",
                        destino_por_arquivo.get(l.arquivo, ""), l.erro or ""])
    return caminho


def processar_pasta(
    base: Path,
    progresso: Callable[[int, int, Leitura], None] | None = None,
    parar: Callable[[], bool] | None = None,
    ler=None,
) -> Resultado:
    base = Path(base)
    fotos = listar_fotos(base)
    if not fotos:
        raise ValueError("Nenhuma foto (jpg, png, webp...) encontrada nessa pasta.")
    if getattr(sys, "frozen", False):  # executável: marcas.txt fica ao lado do .exe
        pasta_app = Path(sys.executable).resolve().parent
    else:
        pasta_app = Path(__file__).resolve().parent.parent
    marcas = carregar_marcas(pasta_app / "marcas.txt")
    ler = ler or criar_motor()
    leituras: list[Leitura] = []
    for i, foto in enumerate(fotos, 1):
        if parar and parar():
            break
        l = analisar_foto(ler, foto, marcas)
        leituras.append(l)
        if progresso:
            progresso(i, len(fotos), l)
    pastas = agrupar(leituras)
    copiar_para_pastas(base, pastas)
    salvar_relatorio(base, leituras, pastas)
    return Resultado(leituras, pastas)
