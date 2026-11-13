"""Programa que fica na bandeja: os dois botoes do mouse abrem a selecao; ao soltar, salva e copia."""
from __future__ import annotations

import queue
import sys
from datetime import datetime
from pathlib import Path

import customtkinter as ctk

from . import tema
from .bandeja import Bandeja
from .config import pasta_dados, pasta_destino_padrao
from .configuracoes import Configuracoes
from .nucleo import Config, area_valida, caminho_sem_sobrescrever, nome_arquivo, normalizar_area
from .overlay import Overlay
from .toast import Aviso
from .windows import (GatilhoDoisBotoes, abrir_pasta, area_da_tela_toda, capturar_regiao, copiar_imagem,
                      tocar_som_de_obturador)


class Aplicativo(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("light")
        self.withdraw()
        self.title("Captura de Tela")
        self.arquivo_config = pasta_dados() / "config.json"
        self.cfg = Config.carregar(self.arquivo_config)
        if not self.cfg.pasta_destino:
            self.cfg.pasta_destino = str(pasta_destino_padrao())
            self.cfg.salvar(self.arquivo_config)
        self.eventos: queue.Queue = queue.Queue()
        self.aviso = Aviso(self)
        self.overlay: Overlay | None = None
        self.janela_config: Configuracoes | None = None
        self.bandeja: Bandeja | None = None
        self.tem_bandeja = False
        self.gatilho = GatilhoDoisBotoes(self._ao_iniciar_fora_da_thread, self._ao_mover_fora_da_thread,
                                         self._ao_soltar_fora_da_thread)
        self.gatilho_ativo = self.gatilho.iniciar()
        self._iniciar_bandeja()
        self.after(150, self._ler_eventos)

    def _iniciar_bandeja(self) -> None:
        try:
            from PIL import Image
            imagem = Image.open(tema.recurso("icone.png")).convert("RGBA")
        except Exception:  # noqa: BLE001
            return
        pedir = lambda nome: (lambda: self.eventos.put((nome, None)))
        self.bandeja = Bandeja(imagem, alternar=pedir("alternar"), esta_ligado=lambda: self.cfg.ativo,
                               pasta=pedir("pasta"), config=pedir("config"), sair=pedir("sair"))
        self.tem_bandeja = self.bandeja.iniciar()
        if not self.gatilho_ativo:
            self.after(500, lambda: self.aviso.mostrar("Captura de Tela", "Não consegui ouvir o mouse do sistema. "
                                                       "Alguns antivírus bloqueiam isso. Veja o LEIA-ME.", erro=True))

    # ---- chamadas da thread do mouse (pynput): so colocam na fila, nada de Tk por la ----------
    def _ao_iniciar_fora_da_thread(self, x: int, y: int) -> None:
        if self.cfg.ativo:
            self.eventos.put(("iniciar_selecao", (x, y)))

    def _ao_mover_fora_da_thread(self, x: int, y: int) -> None:
        self.eventos.put(("mover_selecao", (x, y)))

    def _ao_soltar_fora_da_thread(self, x: int, y: int) -> None:
        self.eventos.put(("soltar_selecao", (x, y)))

    # ---- selecao (na thread da interface) -----------------------------------------------------
    def _iniciar_selecao(self, x: int, y: int) -> None:
        if self.overlay is not None:
            return
        self.overlay = Overlay(self, area_da_tela_toda(), x, y, self._finalizar_selecao, self._cancelar_selecao)

    def _cancelar_selecao(self) -> None:
        self.overlay = None

    def _finalizar_selecao(self, x1: int, y1: int, x2: int, y2: int) -> None:
        self.overlay = None
        area = normalizar_area(x1, y1, x2, y2)
        if not area_valida(area):
            return
        self.capturar(area)

    def capturar(self, area: tuple[int, int, int, int]) -> None:
        try:
            imagem = capturar_regiao(*area)
        except Exception as e:  # noqa: BLE001
            self.aviso.mostrar("Não consegui capturar", str(e), erro=True)
            return
        pasta = Path(self.cfg.pasta_destino)
        try:
            pasta.mkdir(parents=True, exist_ok=True)
            destino = caminho_sem_sobrescrever(pasta, nome_arquivo(datetime.now(), self.cfg.prefixo_arquivo))
            imagem.save(destino, "PNG")
        except OSError as e:
            self.aviso.mostrar("Não consegui salvar", str(e), erro=True)
            return
        copiou = self.cfg.copiar_para_area_transferencia and copiar_imagem(imagem)
        if self.cfg.som:
            tocar_som_de_obturador()
        self._avisar_pronto(imagem, destino, copiou)

    def _avisar_pronto(self, imagem, destino: Path, copiou: bool) -> None:
        miniatura = None
        try:
            from PIL import Image, ImageOps
            mini = ImageOps.contain(imagem.convert("RGB"), (64, 64))
            import io
            from PIL import ImageTk
            buf = io.BytesIO()
            mini.save(buf, "PNG")
            miniatura = ImageTk.PhotoImage(data=buf.getvalue())
        except Exception:  # noqa: BLE001
            pass
        texto = f"{imagem.width} x {imagem.height} px — {destino.name}" + ("" if copiou else "\n(não copiado p/ a área de transferência)")
        self.aviso.mostrar("✔ Captura salva", texto, miniatura=miniatura, ao_abrir_pasta=lambda: abrir_pasta(destino.parent))
        if self.tem_bandeja:
            self.bandeja.avisar("Captura de Tela", f"Salvo: {destino.name}")

    # ---- eventos (menu da bandeja + fila do mouse) --------------------------------------------
    def _ler_eventos(self) -> None:
        try:
            while True:
                tipo, dado = self.eventos.get_nowait()
                if tipo == "iniciar_selecao":
                    self._iniciar_selecao(*dado)
                elif tipo == "mover_selecao" and self.overlay is not None:
                    self.overlay.atualizar(*dado)
                elif tipo == "soltar_selecao" and self.overlay is not None:
                    self.overlay.finalizar(*dado)
                elif tipo == "alternar":
                    self.cfg.ativo = not self.cfg.ativo
                    self.cfg.salvar(self.arquivo_config)
                    if self.tem_bandeja:
                        self.bandeja.atualizar_menu()
                elif tipo == "pasta":
                    abrir_pasta(self.cfg.pasta_destino)
                elif tipo == "config":
                    self.abrir_config()
                elif tipo == "sair":
                    self.sair()
                    return
        except queue.Empty:
            pass
        self.after(150, self._ler_eventos)

    def abrir_config(self) -> None:
        if self.janela_config is not None:
            try:
                self.janela_config.destroy()
            except Exception:  # noqa: BLE001
                pass
        self.janela_config = Configuracoes(self, self.cfg, lambda: None)

    def destroy(self) -> None:
        self.gatilho.parar()
        if getattr(self, "tem_bandeja", False) and self.bandeja:
            self.bandeja.parar()
            self.tem_bandeja = False
        super().destroy()

    def sair(self) -> None:
        self.destroy()
