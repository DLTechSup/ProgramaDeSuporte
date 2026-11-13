"""Programa que fica na bandeja e abre a janela de renomear com o atalho global."""
from __future__ import annotations

import queue
import sys
import threading
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from . import nucleo, tema
from .bandeja import Bandeja
from .config import Config, pasta_dados
from .configuracoes import Configuracoes
from .dialogo import Dialogo
from .toast import Aviso
from .windows import Atalho, arquivos_selecionados


class Aplicativo(ctk.CTk):
    def __init__(self, atalho_teste: str | None = None) -> None:
        super().__init__()
        ctk.set_appearance_mode("light")
        self.withdraw()
        self.title("Renomeador em Massa")
        self.cfg = Config.carregar()
        if atalho_teste:
            self.cfg.atalho = atalho_teste
        self.historico = nucleo.Historico(pasta_dados() / "historico.json")
        self.eventos: queue.Queue = queue.Queue()
        self.aviso = Aviso(self)
        self.dialogo: Dialogo | None = None
        self.janela_config: Configuracoes | None = None
        self.atalho: Atalho | None = None
        self.bandeja: Bandeja | None = None
        self.tem_bandeja = False
        self._registrar_atalho()
        self._iniciar_bandeja()
        self.after(150, self._ler_eventos)

    # ------------------------------------------------------------ atalho e bandeja
    def _registrar_atalho(self) -> None:
        if self.atalho:
            self.atalho.parar()
        try:
            self.atalho = Atalho(self.cfg.atalho, self._atalho_apertado)
        except ValueError:
            self.cfg.atalho = Config().atalho
            self.atalho = Atalho(self.cfg.atalho, self._atalho_apertado)
        self.atalho.start()
        self.atalho.pronto.wait(2)
        if sys.platform.startswith("win") and not self.atalho.registrado:
            self.after(600, lambda: self.aviso.mostrar("Atalho indisponível", f"Não consegui usar {self.cfg.atalho}: outro programa já usa. "
                                                       "Abra Configurações pela bandeja e escolha outro.", erro=True, som=False))

    def _iniciar_bandeja(self) -> None:
        try:
            from PIL import Image
            imagem = Image.open(tema.recurso("icone.png")).convert("RGBA")
        except Exception:  # noqa: BLE001
            return
        pedir = lambda nome: (lambda: self.eventos.put((nome, None)))
        if self.bandeja:
            self.bandeja.parar()
        self.bandeja = Bandeja(imagem, self.cfg.atalho, escolher=pedir("escolher"), desfazer=pedir("desfazer"),
                               config=pedir("config"), sair=pedir("sair"))
        self.tem_bandeja = self.bandeja.iniciar()

    def _atalho_apertado(self, hwnd: int) -> None:
        """Roda na thread do atalho: descobre o que esta selecionado no Explorador e avisa a janela principal."""
        def trabalho():
            self.eventos.put(("abrir", arquivos_selecionados(hwnd)))
        threading.Thread(target=trabalho, daemon=True).start()

    def pedir(self, nome: str, dado=None) -> None:
        self.eventos.put((nome, dado))

    # ------------------------------------------------------------ eventos
    def _ler_eventos(self) -> None:
        try:
            while True:
                tipo, dado = self.eventos.get_nowait()
                if tipo == "abrir":
                    self.abrir(dado or self._escolher_arquivos())
                elif tipo == "escolher":
                    self.abrir(self._escolher_arquivos())
                elif tipo == "desfazer":
                    self.desfazer_ultimo()
                elif tipo == "config":
                    self.abrir_config()
                elif tipo == "sair":
                    self.sair()
                    return
        except queue.Empty:
            pass
        self.after(150, self._ler_eventos)

    def _escolher_arquivos(self) -> list[str]:
        """Sem selecao no Explorador (ou atalho vindo da bandeja): deixa escolher os arquivos numa janela."""
        self.update()
        escolhidos = filedialog.askopenfilenames(title="Escolha os arquivos para renomear", initialdir=self.cfg.ultima_pasta or None)
        return list(escolhidos)

    def abrir(self, arquivos: list[str]) -> None:
        arquivos = [a for a in arquivos if Path(a).is_file()]
        if not arquivos:
            return
        if self.dialogo is not None:
            try:
                self.dialogo.destroy()
            except Exception:  # noqa: BLE001
                pass
        self.dialogo = Dialogo(self, arquivos, self.cfg, self._concluido)

    def _concluido(self, feitos: list[tuple[str, str]], nome: str) -> None:
        self.historico.registrar(feitos, nome)
        primeiro, ultimo = Path(feitos[0][0]).name, Path(feitos[-1][0]).name
        self.aviso.mostrar("✔ Renomeado", f"{len(feitos)} arquivo(s): {primeiro} … {ultimo}", ao_desfazer=self.desfazer_ultimo, som=self.cfg.som)

    def desfazer_ultimo(self) -> None:
        item = self.historico.ultimo()
        if not item:
            self.aviso.mostrar("Desfazer", "Não há nada para desfazer.", som=False)
            return
        try:
            n = nucleo.desfazer([tuple(x) for x in item["feitos"]])
        except Exception as e:  # noqa: BLE001
            self.aviso.mostrar("Não consegui desfazer", str(e), erro=True, som=False)
            return
        self.historico.remover_ultimo()
        self.aviso.mostrar("↩ Desfeito", f"{n} arquivo(s) voltaram ao nome original.", som=False)

    def abrir_config(self) -> None:
        if self.janela_config is not None:
            try:
                self.janela_config.destroy()
            except Exception:  # noqa: BLE001
                pass
        self.janela_config = Configuracoes(self, self.cfg, self._config_salva)

    def _config_salva(self) -> None:
        self._registrar_atalho()
        self._iniciar_bandeja()
        self.aviso.mostrar("Configurações salvas", f"Atalho: {self.cfg.atalho}", som=False)

    def destroy(self) -> None:
        for parte in (self.atalho, self.bandeja):
            try:
                parte.parar() if parte else None
            except Exception:  # noqa: BLE001
                pass
        super().destroy()

    def sair(self) -> None:
        self.destroy()
