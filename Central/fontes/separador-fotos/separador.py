#!/usr/bin/env python3
"""Separador de fotos de calçados por marca e referência.

Uso:
    python separador.py              -> abre a janela para escolher a pasta
    python separador.py C:\\fotos    -> roda direto, sem janela
"""
from __future__ import annotations

import os
import sys
import threading
from pathlib import Path

from separador_fotos.organizador import PASTA_NAO_IDENTIFICADAS, processar_pasta


def rodar_terminal(pasta: str) -> int:
    def prog(i, n, l):
        status = f"{l.marca or '?'} / {l.referencia or '?'}" if not l.erro else f"ERRO: {l.erro}"
        print(f"[{i}/{n}] {l.arquivo.name} -> {status}")

    res = processar_pasta(Path(pasta), prog)
    resumo(res, print)
    return 0


def resumo(res, escrever) -> None:
    escrever("\n=== Pastas criadas ===")
    for nome, arqs in res.pastas.items():
        escrever(f"{nome}: {len(arqs)} foto(s)")
    escrever("\nRelatório salvo em relatorio_separacao.csv")


def rodar_janela() -> None:
    import tkinter as tk
    from tkinter import filedialog, messagebox, scrolledtext, ttk

    raiz = tk.Tk()
    raiz.title("Separador de fotos por marca e referência")
    raiz.geometry("760x520")

    pasta = tk.StringVar()
    topo = ttk.Frame(raiz, padding=10)
    topo.pack(fill="x")
    ttk.Entry(topo, textvariable=pasta).pack(side="left", fill="x", expand=True)

    def escolher():
        p = filedialog.askdirectory(title="Escolha a pasta com as fotos")
        if p:
            pasta.set(p)

    ttk.Button(topo, text="Escolher pasta...", command=escolher).pack(side="left", padx=6)
    botao = ttk.Button(topo, text="Separar fotos")
    botao.pack(side="left")

    barra = ttk.Progressbar(raiz, mode="determinate")
    barra.pack(fill="x", padx=10)
    log = scrolledtext.ScrolledText(raiz, state="disabled", font=("Consolas", 10))
    log.pack(fill="both", expand=True, padx=10, pady=10)

    def escrever(msg):
        def f():
            log.configure(state="normal")
            log.insert("end", msg + "\n")
            log.see("end")
            log.configure(state="disabled")
        raiz.after(0, f)

    def trabalho(p):
        try:
            escrever("Carregando leitor de texto (a primeira vez demora um pouco)...")

            def prog(i, n, l):
                raiz.after(0, lambda: barra.configure(maximum=n, value=i))
                status = f"{l.marca or '?'} / {l.referencia or '?'}" if not l.erro else f"ERRO: {l.erro}"
                escrever(f"[{i}/{n}] {l.arquivo.name} -> {status}")

            res = processar_pasta(Path(p), prog)
            resumo(res, escrever)
            n_ni = len(res.pastas.get(PASTA_NAO_IDENTIFICADAS, []))
            msg = "Pronto! As pastas foram criadas dentro da pasta escolhida."
            if n_ni:
                msg += f"\n{n_ni} foto(s) não foram identificadas e estão em '{PASTA_NAO_IDENTIFICADAS}'."
            raiz.after(0, lambda: messagebox.showinfo("Concluído", msg))
        except Exception as e:  # noqa: BLE001
            escrever(f"ERRO: {e}")
            raiz.after(0, lambda: messagebox.showerror("Erro", str(e)))
        finally:
            raiz.after(0, lambda: botao.configure(state="normal"))

    def iniciar():
        if not pasta.get() or not Path(pasta.get()).is_dir():
            messagebox.showwarning("Atenção", "Escolha primeiro a pasta com as fotos.")
            return
        botao.configure(state="disabled")
        threading.Thread(target=trabalho, args=(pasta.get(),), daemon=True).start()

    botao.configure(command=iniciar)
    raiz.mainloop()


if __name__ == "__main__":
    if sys.stdout is None:  # executável sem console: evita erro em print/log
        sys.stdout = sys.stderr = open(os.devnull, "w")
    if len(sys.argv) > 1:
        sys.exit(rodar_terminal(sys.argv[1]))
    rodar_janela()
