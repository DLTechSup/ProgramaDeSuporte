"""Aviso no canto da tela depois de renomear, com botao 'Desfazer'."""
from __future__ import annotations

import sys
import tkinter as tk
from typing import Callable

DURACAO_MS = 9000


class Aviso:
    def __init__(self, raiz: tk.Misc) -> None:
        self.raiz = raiz
        self.atual: tk.Toplevel | None = None

    def mostrar(self, titulo: str, texto: str, ao_desfazer: Callable | None = None, erro: bool = False, som: bool = True) -> None:
        self.fechar()
        faixa, fundo = ("#D14343", "#FFF5F5") if erro else ("#2F6FED", "#FFFFFF")
        w = tk.Toplevel(self.raiz)
        w.overrideredirect(True)
        w.attributes("-topmost", True)
        w.configure(bg="#C9D1DC")
        corpo = tk.Frame(w, bg=fundo)
        corpo.pack(fill="both", expand=True, padx=1, pady=1)
        tk.Frame(corpo, bg=faixa, width=6).pack(side="left", fill="y")
        t = tk.Frame(corpo, bg=fundo)
        t.pack(side="left", fill="both", expand=True, padx=12, pady=8)
        tk.Label(t, text=titulo, bg=fundo, fg=faixa, font=("Segoe UI", 10, "bold"), anchor="w").pack(fill="x")
        tk.Label(t, text=texto, bg=fundo, fg="#1F2933", font=("Segoe UI", 11), anchor="w", justify="left", wraplength=290).pack(fill="x")
        if ao_desfazer:
            b = tk.Label(t, text="↩ Desfazer", bg=fundo, fg=faixa, font=("Segoe UI", 10, "bold"), cursor="hand2", anchor="w")
            b.pack(fill="x", pady=(4, 0))
            b.bind("<Button-1>", lambda _e: (self.fechar(), ao_desfazer()))
        w.bind("<Button-1>", lambda _e: self.fechar())
        sw, sh = self.raiz.winfo_screenwidth(), self.raiz.winfo_screenheight()
        w.update_idletasks()
        alt = max(w.winfo_reqheight(), 84)
        w.geometry(f"360x{alt}+{sw - 360 - 12}+{max(0, sh - 60 - alt - 12)}")
        self.atual = w
        if som and sys.platform.startswith("win"):
            try:
                import winsound
                winsound.MessageBeep()
            except Exception:  # noqa: BLE001
                pass
        w.after(DURACAO_MS, lambda x=w: self.fechar(x))

    def fechar(self, so_este: tk.Toplevel | None = None) -> None:
        if self.atual is not None and (so_este is None or so_este is self.atual):
            try:
                self.atual.destroy()
            except tk.TclError:
                pass
            self.atual = None
