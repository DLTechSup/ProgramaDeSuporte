"""Janela de configuracoes: pasta de destino, copiar para a area de transferencia, som, iniciar com o Windows."""
from __future__ import annotations

from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Callable

import customtkinter as ctk

from . import tema
from .nucleo import Config
from .tema import ACENTO, BORDA, BRANCO, FUNDO, SUAVE, TEXTO, botao, cartao, fonte


def iniciar_com_windows(ligar: bool, nome: str = "CapturaDeTela") -> bool:
    import sys
    if not sys.platform.startswith("win"):
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0,
                            winreg.KEY_SET_VALUE) as k:
            if ligar:
                winreg.SetValueEx(k, nome, 0, winreg.REG_SZ, f'"{sys.executable}"')
            else:
                try:
                    winreg.DeleteValue(k, nome)
                except FileNotFoundError:
                    pass
        return True
    except Exception:  # noqa: BLE001
        return False


def inicia_com_windows(nome: str = "CapturaDeTela") -> bool:
    import sys
    if not sys.platform.startswith("win"):
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as k:
            winreg.QueryValueEx(k, nome)
            return True
    except Exception:  # noqa: BLE001
        return False


class Configuracoes(ctk.CTkToplevel):
    def __init__(self, raiz, cfg: Config, ao_salvar: Callable[[], None]) -> None:
        super().__init__(raiz)
        self.cfg, self.ao_salvar = cfg, ao_salvar
        self.title("Configurações")
        self.configure(fg_color=FUNDO)
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.geometry("520x430")

        c1 = cartao(self)
        c1.pack(fill="x", padx=16, pady=(16, 8))
        ctk.CTkLabel(c1, text="Pasta onde as capturas são salvas", font=fonte(15, True), text_color=TEXTO).pack(anchor="w", padx=16, pady=(14, 4))
        linha = ctk.CTkFrame(c1, fg_color="transparent")
        linha.pack(fill="x", padx=16, pady=(0, 14))
        self.e_pasta = ctk.CTkEntry(linha, height=36, font=fonte(13), border_color=BORDA, fg_color=BRANCO, text_color=TEXTO)
        self.e_pasta.pack(side="left", fill="x", expand=True)
        self.e_pasta.insert(0, cfg.pasta_destino)
        botao(linha, "Escolher...", self._escolher_pasta, "secundario", 100).pack(side="left", padx=(8, 0))

        c2 = cartao(self)
        c2.pack(fill="x", padx=16, pady=8)
        ctk.CTkLabel(c2, text="Opções", font=fonte(15, True), text_color=TEXTO).pack(anchor="w", padx=16, pady=(14, 4))
        self.v_copiar = ctk.BooleanVar(value=cfg.copiar_para_area_transferencia)
        self.v_som = ctk.BooleanVar(value=cfg.som)
        self.v_ativo = ctk.BooleanVar(value=cfg.ativo)
        self.v_inicio = ctk.BooleanVar(value=inicia_com_windows())
        for var, txt in ((self.v_ativo, "Captura ligada (clique com os dois botões do mouse ao mesmo tempo)"),
                         (self.v_copiar, "Copiar a imagem para a área de transferência"),
                         (self.v_som, "Tocar um som ao capturar"),
                         (self.v_inicio, "Iniciar junto com o Windows (fica na bandeja)")):
            ctk.CTkCheckBox(c2, text=txt, variable=var, font=fonte(13), text_color=TEXTO, fg_color=ACENTO,
                            hover_color=tema.ACENTO_HOVER, corner_radius=6).pack(anchor="w", padx=16, pady=5)
        ctk.CTkLabel(c2, text="", height=6).pack()

        rod = ctk.CTkFrame(self, fg_color="transparent")
        rod.pack(side="bottom", fill="x", padx=16, pady=10)
        botao(rod, "Cancelar", self.destroy, "secundario", 110).pack(side="left")
        botao(rod, "Salvar", self._salvar, "primario", 130).pack(side="right")
        ctk.CTkLabel(self, text=f"Captura de Tela v{tema.VERSAO}", font=fonte(11), text_color=SUAVE).pack(side="bottom", pady=(0, 6))

    def _escolher_pasta(self) -> None:
        p = filedialog.askdirectory(title="Pasta das capturas", initialdir=self.e_pasta.get() or None)
        if p:
            self.e_pasta.delete(0, "end")
            self.e_pasta.insert(0, p)

    def _salvar(self) -> None:
        pasta = self.e_pasta.get().strip()
        if not pasta:
            messagebox.showwarning("Atenção", "Escolha uma pasta.", parent=self)
            return
        self.cfg.pasta_destino = pasta
        self.cfg.copiar_para_area_transferencia = bool(self.v_copiar.get())
        self.cfg.som = bool(self.v_som.get())
        self.cfg.ativo = bool(self.v_ativo.get())
        iniciar_com_windows(bool(self.v_inicio.get()))
        try:
            Path(pasta).mkdir(parents=True, exist_ok=True)
            self.cfg.salvar(self._arquivo_config())
        except OSError as e:
            messagebox.showerror("Não consegui salvar", str(e), parent=self)
            return
        self.destroy()
        self.ao_salvar()

    def _arquivo_config(self) -> Path:
        from .config import pasta_dados
        return pasta_dados() / "config.json"
