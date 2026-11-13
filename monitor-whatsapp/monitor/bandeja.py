"""Icone na bandeja do Windows (perto do relogio): o programa fica ali, bonito e discreto, enquanto monitora."""
from __future__ import annotations

from typing import Callable


class Bandeja:
    def __init__(self, ao_abrir: Callable, ao_alternar: Callable, ao_pasta: Callable, ao_sair: Callable, imagem) -> None:
        self.ao_abrir, self.ao_alternar, self.ao_pasta, self.ao_sair = ao_abrir, ao_alternar, ao_pasta, ao_sair
        self.imagem = imagem
        self.texto_alternar = "Iniciar monitor"
        self.icone = None

    def iniciar(self) -> bool:
        """False se a bandeja nao estiver disponivel (o programa entao so minimiza a janela)."""
        try:
            import pystray
            from pystray import Menu, MenuItem as Item
            menu = Menu(
                Item("Abrir Monitor de Demandas", lambda *_: self.ao_abrir(), default=True),
                Item(lambda _item: self.texto_alternar, lambda *_: self.ao_alternar()),
                Item("Abrir pasta das demandas", lambda *_: self.ao_pasta()),
                Menu.SEPARATOR,
                Item("Sair de vez", lambda *_: self.ao_sair()),
            )
            self.icone = pystray.Icon("monitor_demandas", self.imagem, "Monitor de Demandas", menu)
            self.icone.run_detached()
            return True
        except Exception:  # noqa: BLE001
            self.icone = None
            return False

    def atualizar(self, status: str, monitorando: bool) -> None:
        self.texto_alternar = "Pausar monitor" if monitorando else "Iniciar monitor"
        if self.icone is not None:
            try:
                self.icone.title = f"Monitor de Demandas — {status}"[:120]
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
