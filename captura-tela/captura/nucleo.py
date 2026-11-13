"""Logica da captura de tela: nomes de arquivo, normalizacao da area selecionada, config. Sem nada de Windows aqui."""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

TAMANHO_MINIMO = 4   # arrastou menos que isso (clique sem querer) = nao conta como selecao


def normalizar_area(x1: float, y1: float, x2: float, y2: float) -> tuple[int, int, int, int]:
    """Deixa (esquerda, topo, direita, baixo) na ordem certa, nao importa de que canto o usuario arrastou."""
    esq, dire = sorted((round(x1), round(x2)))
    topo, baixo = sorted((round(y1), round(y2)))
    return esq, topo, dire, baixo


def area_valida(area: tuple[int, int, int, int], minimo: int = TAMANHO_MINIMO) -> bool:
    esq, topo, dire, baixo = area
    return (dire - esq) >= minimo and (baixo - topo) >= minimo


def nome_arquivo(quando: datetime, prefixo: str = "Captura") -> str:
    """'Captura 2026-11-13 15-30-07.png' (sem : no nome, o Windows nao aceita)."""
    base = re.sub(r'[<>:"/\\|?*]', "-", prefixo).strip() or "Captura"
    return f"{base} {quando.strftime('%Y-%m-%d %H-%M-%S')}.png"


def caminho_sem_sobrescrever(pasta: Path, nome: str) -> Path:
    """Se 'Captura ...png' ja existir (duas no mesmo segundo), acrescenta (2), (3)..."""
    destino = Path(pasta) / nome
    if not destino.exists():
        return destino
    tronco, ext = destino.stem, destino.suffix
    n = 2
    while (Path(pasta) / f"{tronco} ({n}){ext}").exists():
        n += 1
    return Path(pasta) / f"{tronco} ({n}){ext}"


@dataclass
class Config:
    pasta_destino: str = ""            # vazio = Imagens\Capturas de Tela (definido na 1a abertura)
    copiar_para_area_transferencia: bool = True
    som: bool = True
    abrir_pasta_no_aviso: bool = True
    ativo: bool = True                 # desliga/liga a captura sem fechar o programa
    prefixo_arquivo: str = "Captura"

    def salvar(self, arquivo: Path) -> None:
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        arquivo.write_text(__import__("json").dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def carregar(cls, arquivo: Path) -> "Config":
        import json
        try:
            d = json.loads(Path(arquivo).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return cls()
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
