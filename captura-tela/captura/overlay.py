"""Janela transparente que cobre a tela toda enquanto o usuario arrasta a selecao."""
from __future__ import annotations

from typing import Callable

import customtkinter as ctk


class Overlay(ctk.CTkToplevel):
    def __init__(self, raiz, area_tela: tuple[int, int, int, int], x_inicial: int, y_inicial: int,
                ao_finalizar: Callable[[int, int, int, int], None], ao_cancelar: Callable[[], None]) -> None:
        super().__init__(raiz)
        esq, topo, dire, baixo = area_tela
        self.overrideredirect(True)
        self.geometry(f"{dire - esq}x{baixo - topo}+{esq}+{topo}")
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.28)
        self.configure(fg_color="#101418", cursor="crosshair")
        self._offset_x, self._offset_y = esq, topo
        self._x0, self._y0 = x_inicial - esq, y_inicial - topo
        self.ao_finalizar, self.ao_cancelar = ao_finalizar, ao_cancelar
        self.canvas = ctk.CTkCanvas(self, highlightthickness=0, bg="#101418")
        self.canvas.pack(fill="both", expand=True)
        self.lbl = self.canvas.create_text(self._x0 + 14, max(4, self._y0 - 22), text="", fill="white",
                                           font=("Segoe UI", 13, "bold"), anchor="nw")
        self.retangulo = self.canvas.create_rectangle(self._x0, self._y0, self._x0, self._y0, outline="#E0472C", width=2)
        self.bind("<Escape>", lambda _e: self._cancelar())
        self.lift()
        self.focus_force()

    def atualizar(self, x_abs: int, y_abs: int) -> None:
        x, y = x_abs - self._offset_x, y_abs - self._offset_y
        self.canvas.coords(self.retangulo, self._x0, self._y0, x, y)
        self.canvas.itemconfigure(self.lbl, text=f"{abs(x - self._x0)} x {abs(y - self._y0)}")
        self.canvas.coords(self.lbl, min(self._x0, x) + 4, max(4, min(self._y0, y) - 22))

    def finalizar(self, x_abs: int, y_abs: int) -> None:
        esq, topo, dire, baixo = self._bbox_absoluto(x_abs, y_abs)
        self.destroy()
        self.ao_finalizar(esq, topo, dire, baixo)

    def _bbox_absoluto(self, x_abs: int, y_abs: int) -> tuple[int, int, int, int]:
        return (self._x0 + self._offset_x, self._y0 + self._offset_y, x_abs, y_abs)

    def _cancelar(self) -> None:
        self.destroy()
        self.ao_cancelar()
