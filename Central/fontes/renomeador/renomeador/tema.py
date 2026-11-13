"""Visual (tema claro)."""
from __future__ import annotations

import sys
from pathlib import Path

import customtkinter as ctk

VERSAO = "1.0.0"
FUNDO, BRANCO, BORDA = "#F3F5F9", "#FFFFFF", "#E1E6EE"
TEXTO, SUAVE = "#1F2933", "#6B7785"
ACENTO, ACENTO_HOVER = "#2F6FED", "#2559C4"
SEC, SEC_HOVER = "#E8ECF3", "#DCE2EC"
OK_FUNDO, OK_TEXTO = "#E6F4EC", "#2E7D4F"
AVISO_FUNDO, AVISO_TEXTO = "#FFF4DB", "#8A5A00"
ERRO_FUNDO, ERRO_TEXTO = "#FDE8E8", "#B42318"
FONTE = "Segoe UI" if sys.platform.startswith("win") else "DejaVu Sans"


def fonte(tam: int = 13, negrito: bool = False) -> ctk.CTkFont:
    return ctk.CTkFont(family=FONTE, size=tam, weight="bold" if negrito else "normal")


def recurso(nome: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / "assets" / nome


def cartao(pai, **kw) -> ctk.CTkFrame:
    kw.setdefault("fg_color", BRANCO)
    return ctk.CTkFrame(pai, corner_radius=12, border_width=1, border_color=BORDA, **kw)


def botao(pai, texto: str, comando, tipo: str = "secundario", largura: int = 0, **kw) -> ctk.CTkButton:
    estilos = {"primario": dict(fg_color=ACENTO, hover_color=ACENTO_HOVER, text_color="white"),
               "secundario": dict(fg_color=SEC, hover_color=SEC_HOVER, text_color=TEXTO),
               "perigo": dict(fg_color=ERRO_FUNDO, hover_color="#F9D3D3", text_color=ERRO_TEXTO)}
    if largura:
        kw["width"] = largura
    kw.setdefault("height", 36)
    return ctk.CTkButton(pai, text=texto, command=comando, corner_radius=8, font=fonte(13, tipo == "primario"), **estilos[tipo], **kw)


def etiqueta(pai, texto: str, fundo: str, cor: str, **kw) -> ctk.CTkLabel:
    return ctk.CTkLabel(pai, text=texto, fg_color=fundo, text_color=cor, corner_radius=10, font=fonte(11, True), **kw)
