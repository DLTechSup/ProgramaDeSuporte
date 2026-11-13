"""Partes que so existem no Windows: ouvir os dois botoes do mouse ao mesmo tempo, a janela de
selecao na tela inteira e colocar a imagem na area de transferencia."""
from __future__ import annotations

import io
import sys
import time
from typing import Callable

EH_WINDOWS = sys.platform.startswith("win")


class GatilhoDoisBotoes:
    """Dispara quando o botao esquerdo e o direito do mouse ficam pressionados ao mesmo tempo
    (ouve o mouse inteiro do sistema; nao precisa o programa estar em primeiro plano)."""

    def __init__(self, ao_iniciar: Callable[[int, int], None], ao_mover: Callable[[int, int], None],
                 ao_soltar: Callable[[int, int], None], janela_ms: int = 350) -> None:
        self.ao_iniciar, self.ao_mover, self.ao_soltar = ao_iniciar, ao_mover, ao_soltar
        self.janela_ms = janela_ms
        self._listener = None
        self._esquerdo_em = 0.0
        self._direito_em = 0.0
        self._selecionando = False

    def iniciar(self) -> bool:
        if not EH_WINDOWS:
            return False
        try:
            from pynput import mouse
        except Exception:  # noqa: BLE001
            return False

        def ao_clicar(x, y, button, pressionado):
            lado = "esquerdo" if button == mouse.Button.left else ("direito" if button == mouse.Button.right else None)
            if lado:
                self.clique(x, y, lado, pressionado)

        self._listener = mouse.Listener(on_click=ao_clicar, on_move=self._mover)
        self._listener.start()
        return True

    def parar(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None

    def clique(self, x: int, y: int, lado: str, pressionado: bool) -> None:
        """lado = 'esquerdo' ou 'direito'. Logica pura, sem depender do pynput (por isso e' testavel)."""
        agora = time.monotonic()
        if lado == "esquerdo":
            if pressionado:
                self._esquerdo_em = agora
            elif self._selecionando:
                self._selecionando = False
                self._esquerdo_em = self._direito_em = 0.0   # evita que um horario antigo "combine" com um clique futuro
                self.ao_soltar(x, y)
        else:
            if pressionado:
                self._direito_em = agora
            elif self._selecionando:
                self._selecionando = False
                self._esquerdo_em = self._direito_em = 0.0
                self.ao_soltar(x, y)
        if pressionado and not self._selecionando:
            outro = self._direito_em if lado == "esquerdo" else self._esquerdo_em
            if outro and abs(agora - outro) * 1000 <= self.janela_ms:
                self._selecionando = True
                self.ao_iniciar(x, y)

    def _mover(self, x: int, y: int) -> None:
        if self._selecionando:
            self.ao_mover(x, y)


def capturar_regiao(esquerda: int, topo: int, direita: int, baixo: int):
    """Foto da tela dentro dessa area (PIL.Image), somando todos os monitores se precisar."""
    from PIL import ImageGrab
    return ImageGrab.grab(bbox=(esquerda, topo, direita, baixo), all_screens=True)


def area_da_tela_toda() -> tuple[int, int, int, int]:
    """Retangulo que cobre todos os monitores (para a janela de selecao cobrir tudo)."""
    if EH_WINDOWS:
        try:
            import ctypes
            u32 = ctypes.windll.user32
            u32.SetProcessDPIAware()
            SM_XVIRTUALSCREEN, SM_YVIRTUALSCREEN, SM_CXVIRTUALSCREEN, SM_CYVIRTUALSCREEN = 76, 77, 78, 79
            x, y = u32.GetSystemMetrics(SM_XVIRTUALSCREEN), u32.GetSystemMetrics(SM_YVIRTUALSCREEN)
            w, h = u32.GetSystemMetrics(SM_CXVIRTUALSCREEN), u32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
            return x, y, x + w, y + h
        except Exception:  # noqa: BLE001
            pass
    from PIL import ImageGrab
    im = ImageGrab.grab(all_screens=True)
    return 0, 0, im.width, im.height


def copiar_imagem(imagem) -> bool:
    """Coloca a imagem na area de transferencia (DIB, compativel com WhatsApp, Word, navegadores...)."""
    if not EH_WINDOWS:
        return False
    try:
        import win32clipboard
        buf = io.BytesIO()
        imagem.convert("RGB").save(buf, "BMP")
        dados = buf.getvalue()[14:]        # BMP sem o cabecalho de arquivo = formato DIB
        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32clipboard.CF_DIB, dados)
        finally:
            win32clipboard.CloseClipboard()
        return True
    except Exception:  # noqa: BLE001
        return False


def tocar_som_de_obturador() -> None:
    if EH_WINDOWS:
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception:  # noqa: BLE001
            pass


def abrir_pasta(caminho) -> None:
    if EH_WINDOWS:
        try:
            import os
            os.startfile(str(caminho))  # type: ignore[attr-defined]
        except OSError:
            pass
