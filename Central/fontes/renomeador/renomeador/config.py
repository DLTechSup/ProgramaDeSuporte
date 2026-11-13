"""Configuracao e dados do programa (em %APPDATA%\\RenomeadorEmMassa)."""
from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path


def pasta_dados() -> Path:
    if os.environ.get("RENOMEADOR_DADOS"):
        base = Path(os.environ["RENOMEADOR_DADOS"])
    elif sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", Path.home())) / "RenomeadorEmMassa"
    else:
        base = Path.home() / ".renomeador-em-massa"
    base.mkdir(parents=True, exist_ok=True)
    return base


@dataclass
class Config:
    atalho: str = "Ctrl+Alt+R"
    zeros: bool = True
    separador: str = "espaco"
    ordem: str = "data"
    continuar: bool = True
    extensao_minuscula: bool = True
    ultimos_nomes: list[str] = field(default_factory=list)
    som: bool = True
    ultima_pasta: str = ""

    def lembrar_nome(self, nome: str) -> None:
        nome = nome.strip()
        if nome:
            self.ultimos_nomes = [nome] + [n for n in self.ultimos_nomes if n.lower() != nome.lower()]
            self.ultimos_nomes = self.ultimos_nomes[:10]

    def salvar(self, arquivo: Path | None = None) -> None:
        (arquivo or pasta_dados() / "config.json").write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def carregar(cls, arquivo: Path | None = None) -> "Config":
        arquivo = arquivo or pasta_dados() / "config.json"
        try:
            d = json.loads(arquivo.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return cls()
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
