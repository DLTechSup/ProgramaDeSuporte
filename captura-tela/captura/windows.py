"""Partes que so existem no Windows: ouvir o mouse do sistema inteiro, a janela de selecao na tela
inteira e colocar a imagem na area de transferencia."""
from __future__ import annotations

import io
import sys
import time
from typing import Callable

EH_WINDOWS = sys.platform.startswith("win")


class GatilhoCaptura:
    """Fluxo em duas etapas:
    1) Os dois botoes do mouse pressionados ao mesmo tempo (um toque rapido, sem precisar segurar)
       ARMAM a captura -- a tela fica pronta esperando.
    2) Um clique normal com o botao ESQUERDO: pressionar comeca a selecao, arrastar mostra a area,
       soltar conclui a captura.
    Um clique com o botao direito (ou Esc, tratado fora daqui) cancela a qualquer momento depois de armado.
    Logica pura (sem pynput), para poder ser testada."""

    IDLE, ARMADO, SELECIONANDO = "idle", "armado", "selecionando"

    def __init__(self, ao_armar: Callable[[int, int], None], ao_iniciar_selecao: Callable[[int, int], None],
                ao_mover: Callable[[int, int], None], ao_finalizar: Callable[[int, int], None],
                ao_cancelar: Callable[[], None], janela_ms: int = 350) -> None:
        self.ao_armar, self.ao_iniciar_selecao = ao_armar, ao_iniciar_selecao
        self.ao_mover, self.ao_finalizar, self.ao_cancelar = ao_mover, ao_finalizar, ao_cancelar
        self.janela_ms = janela_ms
        self._listener = None
        self.estado = self.IDLE
        self._esquerdo_apertado = False
        self._direito_apertado = False
        self._esquerdo_desde = 0.0
        self._direito_desde = 0.0

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

    def cancelar(self) -> None:
        """Chamado de fora (ex.: tecla Esc) para desistir, de qualquer estado."""
        if self.estado != self.IDLE:
            self.estado = self.IDLE
            self.ao_cancelar()

    def clique(self, x: int, y: int, lado: str, pressionado: bool) -> None:
        agora = time.monotonic()
        if lado == "esquerdo":
            self._esquerdo_apertado = pressionado
            if pressionado:
                self._esquerdo_desde = agora
        else:
            self._direito_apertado = pressionado
            if pressionado:
                self._direito_desde = agora

        if self.estado == self.IDLE:
            if pressionado and self._esquerdo_apertado and self._direito_apertado and \
               abs(self._esquerdo_desde - self._direito_desde) * 1000 <= self.janela_ms:
                self.estado = self.ARMADO
                self.ao_armar(x, y)
        elif self.estado == self.ARMADO:
            if lado == "esquerdo" and pressionado:
                self.estado = self.SELECIONANDO
                self.ao_iniciar_selecao(x, y)
            elif lado == "direito" and pressionado:
                self.estado = self.IDLE
                self.ao_cancelar()
        elif self.estado == self.SELECIONANDO:
            if lado == "esquerdo" and not pressionado:
                self.estado = self.IDLE
                self.ao_finalizar(x, y)
            elif lado == "direito" and pressionado:
                self.estado = self.IDLE
                self.ao_cancelar()

    def _mover(self, x: int, y: int) -> None:
        if self.estado == self.SELECIONANDO:
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
