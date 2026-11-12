"""Escolha das fotos (botao ou arrastar e soltar)."""
from __future__ import annotations

from pathlib import Path

EXTENSOES = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def filtrar_fotos(caminhos) -> list[Path]:
    """Aceita arquivos e pastas (pega as fotos de dentro); ignora o que nao for imagem. Sem repetir, em ordem."""
    out: list[Path] = []
    for c in caminhos:
        p = Path(str(c).strip().strip("{}"))
        itens = sorted(p.iterdir()) if p.is_dir() else [p]
        for it in itens:
            if it.is_file() and it.suffix.lower() in EXTENSOES and it not in out:
                out.append(it)
    return out
