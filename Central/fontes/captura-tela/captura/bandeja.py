"""Icone na bandeja do Windows."""
from __future__ import annotations

from typing import Callable


class Bandeja:
    def __init__(self, imagem, **acoes: Callable) -> None:
        self.imagem, self.acoes, self.icone = imagem, acoes, None

    def iniciar(self) -> bool:
        try:
            import pystray
            from pystray import Menu, MenuItem as Item
            menu = Menu(
                Item("Ligado (dois botões do mouse)", lambda *_: self.acoes["alternar"](), checked=lambda _i: self.acoes["esta_ligado"](), default=True),
                Item("Abrir pasta das capturas", lambda *_: self.acoes["pasta"]()),
                Menu.SEPARATOR,
                Item("Configurações", lambda *_: self.acoes["config"]()),
                Item("Sair", lambda *_: self.acoes["sair"]()),
            )
            self.icone = pystray.Icon("captura_tela", self.imagem, "Captura de Tela", menu)
            self.icone.run_detached()
            return True
        except Exception:  # noqa: BLE001
            self.icone = None
            return False

    def atualizar_menu(self) -> None:
        if self.icone is not None:
            try:
                self.icone.update_menu()
            except Exception:  # noqa: BLE001
                pass

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
