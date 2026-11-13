"""Icone na bandeja do Windows."""
from __future__ import annotations

from typing import Callable


class Bandeja:
    def __init__(self, imagem, atalho_texto: str, **acoes: Callable) -> None:
        self.imagem, self.atalho_texto, self.acoes, self.icone = imagem, atalho_texto, acoes, None

    def iniciar(self) -> bool:
        try:
            import pystray
            from pystray import Menu, MenuItem as Item
            menu = Menu(
                Item(f"Renomear arquivos selecionados  ({self.atalho_texto})", lambda *_: self.acoes["escolher"](), default=True),
                Item("Desfazer a última renomeação", lambda *_: self.acoes["desfazer"]()),
                Menu.SEPARATOR,
                Item("Configurações", lambda *_: self.acoes["config"]()),
                Item("Sair", lambda *_: self.acoes["sair"]()),
            )
            self.icone = pystray.Icon("renomeador", self.imagem, f"Renomeador em Massa — {self.atalho_texto}", menu)
            self.icone.run_detached()
            return True
        except Exception:  # noqa: BLE001
            self.icone = None
            return False

    def avisar(self, titulo: str, texto: str) -> None:
        if self.icone is not None:
            try:
                self.icone.notify(texto, titulo)
            except Exception:  # noqa: BLE001
                pass

    def parar(self) -> None:
        if self.icone is not None:
            try:
                self.icone.stop()
            except Exception:  # noqa: BLE001
                pass
            self.icone = None
