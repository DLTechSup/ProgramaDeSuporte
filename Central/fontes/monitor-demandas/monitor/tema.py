"""Visual do programa (tema claro): cores, fontes e pecas reutilizaveis."""
from __future__ import annotations

import sys
from pathlib import Path

import customtkinter as ctk

from .config import RAIZ

VERSAO = "1.0.0"
FUNDO = "#F3F5F7"
BRANCO = "#FFFFFF"
BORDA = "#E1E6EB"
TEXTO = "#1F2933"
SUAVE = "#6B7785"
ACENTO = "#0E7C66"
ACENTO_HOVER = "#0B6553"
SEC = "#E8ECF0"
SEC_HOVER = "#DCE2E8"
AVISO_FUNDO, AVISO_BORDA, AVISO_TEXTO = "#FFF4DB", "#F1D08A", "#8A5A00"
OK_FUNDO, OK_TEXTO = "#E6F4EC", "#2E7D4F"
ERRO_FUNDO, ERRO_TEXTO = "#FDE8E8", "#B42318"

FONTE = "Segoe UI" if sys.platform.startswith("win") else "DejaVu Sans"   # fora do Windows so para testar o visual


def fonte(tam: int = 13, negrito: bool = False) -> ctk.CTkFont:
    return ctk.CTkFont(family=FONTE, size=tam, weight="bold" if negrito else "normal")


def recurso(nome: str) -> Path:
    """Arquivo de dentro do programa (funciona no .exe e rodando pelo Python)."""
    base = Path(getattr(sys, "_MEIPASS", RAIZ))
    return base / "assets" / nome


def cartao(pai, **kw) -> ctk.CTkFrame:
    kw.setdefault("fg_color", BRANCO)
    return ctk.CTkFrame(pai, corner_radius=12, border_width=1, border_color=BORDA, **kw)


def botao(pai, texto: str, comando, tipo: str = "secundario", largura: int = 0, **kw) -> ctk.CTkButton:
    estilos = {
        "primario": dict(fg_color=ACENTO, hover_color=ACENTO_HOVER, text_color="white"),
        "secundario": dict(fg_color=SEC, hover_color=SEC_HOVER, text_color=TEXTO),
        "perigo": dict(fg_color=ERRO_FUNDO, hover_color="#F9D3D3", text_color=ERRO_TEXTO),
    }
    if largura:
        kw["width"] = largura
    kw.setdefault("height", 34)
    return ctk.CTkButton(pai, text=texto, command=comando, corner_radius=8, font=fonte(13, tipo == "primario"),
                         **estilos[tipo], **kw)


def etiqueta(pai, texto: str, fundo: str, cor: str, **kw) -> ctk.CTkLabel:
    """Selo pequeno e arredondado (ex.: 'CONFERIR')."""
    return ctk.CTkLabel(pai, text=texto, fg_color=fundo, text_color=cor, corner_radius=10, font=fonte(11, True), **kw)


def pilula_status(texto: str) -> tuple[str, str, str]:
    """(texto da pilula, cor de fundo, cor do texto) a partir da mensagem de status do servico."""
    t = texto.lower()
    if "monitorando" in t:
        return "●  " + texto, OK_FUNDO, OK_TEXTO
    if "qr" in t or "abrindo" in t or "entre no" in t:
        return "●  " + texto, AVISO_FUNDO, AVISO_TEXTO
    if "erro" in t:
        return "●  " + texto, ERRO_FUNDO, ERRO_TEXTO
    return "●  " + texto, SEC, SUAVE
