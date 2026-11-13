"""Janela transparente que cobre a tela toda: primeiro so avisando que esta pronta (armada),
depois mostrando o retangulo enquanto o usuario arrasta com o botao esquerdo."""
from __future__ import annotations

from typing import Callable

import customtkinter as ctk


class Overlay(ctk.CTkToplevel):
    def __init__(self, raiz, area_tela: tuple[int, int, int, int], ao_cancelar: Callable[[], None]) -> None:
        super().__init__(raiz)
        esq, topo, dire, baixo = area_tela
        self.overrideredirect(True)
        self.geometry(f"{dire - esq}x{baixo - topo}+{esq}+{topo}")
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.22)
        self.configure(fg_color="#101418", cursor="crosshair")
        self._offset_x, self._offset_y = esq, topo
        self.ao_cancelar = ao_cancelar
        self.canvas = ctk.CTkCanvas(self, highlightthickness=0, bg="#101418")
        self.canvas.pack(fill="both", expand=True)
        self._dica = self.canvas.create_text((dire - esq) / 2, 36, text="Clique e arraste para selecionar a área  •  clique direito ou Esc para cancelar",
                                             fill="white", font=("Segoe UI", 14, "bold"))
        self._x0 = self._y0 = 0
        self._retangulo = None
        self._medida = None
        self.bind("<Escape>", lambda _e: self.ao_cancelar())
        self.lift()
        self.focus_force()

    def iniciar_arraste(self, x_abs: int, y_abs: int) -> None:
        self.canvas.delete(self._dica)
        self._x0, self._y0 = x_abs - self._offset_x, y_abs - self._offset_y
        self._retangulo = self.canvas.create_rectangle(self._x0, self._y0, self._x0, self._y0, outline="#E0472C", width=2)
        self._medida = self.canvas.create_text(self._x0 + 14, max(4, self._y0 - 22), text="", fill="white",
                                                font=("Segoe UI", 13, "bold"), anchor="nw")

    def atualizar(self, x_abs: int, y_abs: int) -> None:
        if self._retangulo is None:
            return
        x, y = x_abs - self._offset_x, y_abs - self._offset_y
        self.canvas.coords(self._retangulo, self._x0, self._y0, x, y)
        self.canvas.itemconfigure(self._medida, text=f"{abs(x - self._x0)} x {abs(y - self._y0)}")
        self.canvas.coords(self._medida, min(self._x0, x) + 4, max(4, min(self._y0, y) - 22))

    def bbox_absoluto(self, x_abs: int, y_abs: int) -> tuple[int, int, int, int]:
        return (self._x0 + self._offset_x, self._y0 + self._offset_y, x_abs, y_abs)
