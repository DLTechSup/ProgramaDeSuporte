"""Dados do produto em andamento."""
from __future__ import annotations

from dataclasses import dataclass, field

FEMININAS = ("SANDALIA", "RASTEIRA", "SAPATILHA", "BOTA", "BOTINA", "PAPETE", "ANABELA", "PLATAFORMA")


@dataclass
class Produto:
    id: int | None = None
    marca: str = ""
    referencia: str = ""
    categoria: str = ""
    genero: str = ""
    publico: str = ""          # adulto | infantil | bebe | teen
    caracteristicas: list[str] = field(default_factory=list)   # etiquetas marcadas (modo offline)

    @property
    def masculino(self) -> bool:
        return self.genero.lower().startswith("masc")

    @property
    def categoria_completa(self) -> str:
        """Categoria + MASCULINO/A logo depois dela (Parte 4 do arquivo v5)."""
        cat = self.categoria.strip().upper()
        if self.masculino and "MASCULIN" not in cat and cat:
            primeira = cat.split()[0].replace("Á", "A").replace("Ê", "E")
            cat += " MASCULINA" if primeira in FEMININAS else " MASCULINO"
        return cat
