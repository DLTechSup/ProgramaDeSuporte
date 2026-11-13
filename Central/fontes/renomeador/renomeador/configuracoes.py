"""Janela de configuracoes: atalho e iniciar com o Windows."""
from __future__ import annotations

from tkinter import messagebox
from typing import Callable

import customtkinter as ctk

from . import tema
from .config import Config
from .tema import ACENTO, BORDA, BRANCO, FUNDO, SUAVE, TEXTO, botao, cartao, fonte
from .windows import formatar_atalho, iniciar_com_windows, inicia_com_windows, interpretar_atalho

TECLAS = [chr(c) for c in range(ord("A"), ord("Z") + 1)] + [str(n) for n in range(10)] + [f"F{n}" for n in range(1, 13)]


class Configuracoes(ctk.CTkToplevel):
    def __init__(self, raiz, cfg: Config, ao_salvar: Callable[[], None]) -> None:
        super().__init__(raiz)
        self.cfg, self.ao_salvar = cfg, ao_salvar
        self.title("Configurações")
        self.configure(fg_color=FUNDO)
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.geometry("480x470")
        mods = [p.lower() for p in cfg.atalho.replace(" ", "").split("+")]
        c = cartao(self)
        c.pack(fill="x", padx=16, pady=(16, 8))
        ctk.CTkLabel(c, text="Atalho para abrir o renomeador", font=fonte(15, True), text_color=TEXTO).pack(anchor="w", padx=16, pady=(14, 0))
        ctk.CTkLabel(c, text="Selecione os arquivos no Explorador e aperte o atalho.", font=fonte(12), text_color=SUAVE).pack(anchor="w", padx=16)
        linha = ctk.CTkFrame(c, fg_color="transparent")
        linha.pack(anchor="w", padx=16, pady=10)
        self.vars = {}
        for nome, rot in (("ctrl", "Ctrl"), ("alt", "Alt"), ("shift", "Shift"), ("win", "Win")):
            v = ctk.BooleanVar(value=nome in mods)
            self.vars[nome] = v
            ctk.CTkCheckBox(linha, text=rot, variable=v, width=70, font=fonte(13), text_color=TEXTO, fg_color=ACENTO,
                            hover_color=tema.ACENTO_HOVER, corner_radius=6).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(linha, text="+", font=fonte(15, True), text_color=SUAVE).pack(side="left", padx=4)
        tecla = [p for p in cfg.atalho.replace(" ", "").split("+") if p.lower() not in ("ctrl", "alt", "shift", "win", "control")]
        self.c_tecla = ctk.CTkComboBox(linha, values=TECLAS, width=80, state="readonly", border_color=BORDA, fg_color=BRANCO, text_color=TEXTO)
        self.c_tecla.set((tecla[-1] if tecla else "R").upper())
        self.c_tecla.pack(side="left", padx=4)
        self.lbl_erro = ctk.CTkLabel(c, text="", font=fonte(12), text_color="#B42318", wraplength=420, justify="left")
        self.lbl_erro.pack(anchor="w", padx=16, pady=(0, 10))

        c2 = cartao(self)
        c2.pack(fill="x", padx=16, pady=8)
        ctk.CTkLabel(c2, text="Geral", font=fonte(15, True), text_color=TEXTO).pack(anchor="w", padx=16, pady=(14, 4))
        self.v_inicio = ctk.BooleanVar(value=inicia_com_windows())
        self.v_som = ctk.BooleanVar(value=cfg.som)
        for var, txt in ((self.v_inicio, "Iniciar junto com o Windows (fica na bandeja)"), (self.v_som, "Tocar um som no aviso de pronto")):
            ctk.CTkCheckBox(c2, text=txt, variable=var, font=fonte(13), text_color=TEXTO, fg_color=ACENTO, hover_color=tema.ACENTO_HOVER,
                            corner_radius=6).pack(anchor="w", padx=16, pady=4)
        ctk.CTkLabel(c2, text="", height=6).pack()
        rod = ctk.CTkFrame(self, fg_color="transparent")
        rod.pack(fill="x", padx=16, pady=10)
        botao(rod, "Cancelar", self.destroy, "secundario", 110).pack(side="left")
        botao(rod, "Salvar", self._salvar, "primario", 130).pack(side="right")
        ctk.CTkLabel(self, text=f"Renomeador em Massa v{tema.VERSAO}", font=fonte(11), text_color=SUAVE).pack(pady=(0, 6))

    def _salvar(self) -> None:
        partes = [rot for nome, rot in (("ctrl", "Ctrl"), ("alt", "Alt"), ("shift", "Shift"), ("win", "Win")) if self.vars[nome].get()]
        texto = "+".join(partes + [self.c_tecla.get()])
        try:
            interpretar_atalho(texto)
        except ValueError as e:
            self.lbl_erro.configure(text=str(e))
            return
        self.cfg.atalho = formatar_atalho(texto)
        self.cfg.som = bool(self.v_som.get())
        iniciar_com_windows(bool(self.v_inicio.get()))
        try:
            self.cfg.salvar()
        except OSError as e:
            messagebox.showerror("Não consegui salvar", str(e), parent=self)
            return
        self.destroy()
        self.ao_salvar()
