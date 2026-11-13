"""Log dos eventos do dia: um arquivo .txt, um evento por linha, na pasta principal (_Log)."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path


class RegistroDoDia:
    def __init__(self, pasta_base: str | Path, agora=datetime.now) -> None:
        self.agora = agora
        self.pasta = Path(pasta_base) / "_Log"

    @property
    def arquivo(self) -> Path:
        return self.pasta / f"log_{self.agora().strftime('%d-%m-%Y')}.txt"

    def escrever(self, texto: str) -> None:
        """Acrescenta '[HH:MM:SS] texto'. Se o texto tiver varias linhas, cada uma vira uma linha do log."""
        self.pasta.mkdir(parents=True, exist_ok=True)
        hora = self.agora().strftime("%H:%M:%S")
        with open(self.arquivo, "a", encoding="utf-8", newline="") as f:
            for i, linha in enumerate(str(texto).splitlines() or [""]):
                f.write((f"[{hora}] " if i == 0 else "           ") + linha + "\r\n")

    def ler(self) -> str:
        return self.arquivo.read_bytes().decode("utf-8").replace("\r\n", "\n") if self.arquivo.exists() else ""
