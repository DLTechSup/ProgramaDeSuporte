"""Aviso no canto da tela depois da captura, com botoes 'Abrir pasta' e 'Copiar de novo'."""
from __future__ import annotations

import tkinter as tk
from typing import Callable

DURACAO_MS = 7000


class Aviso:
    def __init__(self, raiz: tk.Misc) -> None:
        self.raiz = raiz
        self.atual: tk.Toplevel | None = None

    def mostrar(self, titulo: str, texto: str, miniatura=None, ao_abrir_pasta: Callable | None = None,
               erro: bool = False) -> None:
        self.fechar()
        faixa, fundo = ("#D14343", "#FFF5F5") if erro else ("#E0472C", "#FFFFFF")
        w = tk.Toplevel(self.raiz)
        w.overrideredirect(True)
        w.attributes("-topmost", True)
        w.configure(bg="#C9D1DC")
        corpo = tk.Frame(w, bg=fundo)
        corpo.pack(fill="both", expand=True, padx=1, pady=1)
        tk.Frame(corpo, bg=faixa, width=6).pack(side="left", fill="y")
        if miniatura is not None:
            tk.Label(corpo, image=miniatura, bg=fundo).pack(side="left", padx=(8, 4), pady=8)
            w._miniatura = miniatura  # evita o garbage collector apagar a imagem
        t = tk.Frame(corpo, bg=fundo)
        t.pack(side="left", fill="both", expand=True, padx=10, pady=8)
        tk.Label(t, text=titulo, bg=fundo, fg=faixa, font=("Segoe UI", 10, "bold"), anchor="w").pack(fill="x")
        tk.Label(t, text=texto, bg=fundo, fg="#1F2933", font=("Segoe UI", 10), anchor="w", justify="left", wraplength=230).pack(fill="x")
        if ao_abrir_pasta:
            b = tk.Label(t, text="📂 Abrir pasta", bg=fundo, fg=faixa, font=("Segoe UI", 10, "bold"), cursor="hand2", anchor="w")
            b.pack(fill="x", pady=(4, 0))
            b.bind("<Button-1>", lambda _e: (self.fechar(), ao_abrir_pasta()))
        w.bind("<Button-1>", lambda _e: self.fechar())
        sw, sh = self.raiz.winfo_screenwidth(), self.raiz.winfo_screenheight()
        w.update_idletasks()
        largura, altura = 360, max(w.winfo_reqheight(), 90)
        w.geometry(f"{largura}x{altura}+{sw - largura - 12}+{max(0, sh - 60 - altura - 12)}")
        self.atual = w
        w.after(DURACAO_MS, lambda x=w: self.fechar(x))

    def fechar(self, so_este: tk.Toplevel | None = None) -> None:
        if self.atual is not None and (so_este is None or so_este is self.atual):
            try:
                self.atual.destroy()
            except tk.TclError:
                pass
            self.atual = None
