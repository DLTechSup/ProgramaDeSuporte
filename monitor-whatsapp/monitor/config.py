"""Configuracao (config.json ao lado do programa)."""
from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

RAIZ = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent
ARQUIVO = RAIZ / "config.json"
TIPOS = {"A": "Grupo A: foto + marca + referência (legenda)", "B": "Grupo B: só foto da caixa (ler a etiqueta)"}


@dataclass
class Grupo:
    nome: str
    tipo: str = "A"   # "A" ou "B"


@dataclass
class Config:
    pasta_base: str = ""
    grupos: list[Grupo] = field(default_factory=list)
    espera_legenda_seg: int = 120      # foto sem legenda espera o texto por este tempo
    incluir_hoje: bool = True          # pegar tambem o que ja chegou hoje
    tentar_escondidas: bool = True     # album com "+N": tentar abrir e baixar as fotos escondidas
    navegador: str = "msedge"
    notificar: bool = True             # aviso na tela a cada item salvo
    som: bool = True                   # toca um som junto com o aviso

    def salvar(self, arquivo: Path = ARQUIVO) -> None:
        arquivo.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def carregar(cls, arquivo: Path = ARQUIVO) -> "Config":
        if not arquivo.is_file():
            return cls()
        d = json.loads(arquivo.read_text(encoding="utf-8"))
        grupos = [Grupo(**g) for g in d.pop("grupos", [])]
        validos = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(grupos=grupos, **validos)
