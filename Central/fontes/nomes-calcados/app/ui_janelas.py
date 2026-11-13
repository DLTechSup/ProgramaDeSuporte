"""Janelas auxiliares: checar nome, banco de nomes, banco de pecas e 'Analisar o dia'."""
from __future__ import annotations

import threading
from tkinter import filedialog, messagebox

import customtkinter as ctk

from . import analise_dia
from .offline import CARACTERISTICAS, TIPOS
from .validador import Regras, validar


def checar_nome(app) -> None:
    ctl = app.ctl
    p = app.ler_produto_painel()
    if not (p.marca and p.referencia and p.categoria):
        messagebox.showwarning("Atenção", "Preencha marca, referência e categoria no painel do produto antes de checar.")
        return
    win = ctk.CTkToplevel(app)
    win.title("Checar nome")
    win.geometry("780x540")
    win.after(150, win.focus)
    ctk.CTkLabel(win, text="Cole o nome que você quer conferir:", anchor="w").pack(fill="x", padx=10, pady=(10, 2))
    entrada = ctk.CTkEntry(win)
    entrada.pack(fill="x", padx=10)
    saida = ctk.CTkTextbox(win, font=("Consolas", 12))
    saida.pack(fill="both", expand=True, padx=10, pady=10)
    regras = Regras.carregar()

    def checar(_e=None):
        from .validador import Contexto
        ctx = Contexto(p.marca, p.referencia, p.categoria_completa, p.genero, p.publico,
                       aprovados=ctl.banco.listar_nomes(limite=10**9))
        res = validar(entrada.get(), ctx, regras)
        linhas = [f"{len(res.nome)} caracteres\n"]
        for i in res.itens:
            linhas.append(("[OK]    " if i.ok else "[ERRO]  ") + i.regra + ("" if i.ok else f" - {i.mensagem}"))
            if i.ajuste:
                linhas.append(f"          Como ajustar: {i.ajuste}")
        linhas.append("\n" + ("Nome no padrão." if res.aprovado else "Nome fora do padrão: corrija os itens com [ERRO]."))
        saida.delete("1.0", "end")
        saida.insert("1.0", "\n".join(linhas))

    ctk.CTkButton(win, text="Checar", command=checar).pack(pady=(0, 8))
    entrada.bind("<Return>", checar)


def banco_de_nomes(app) -> None:
    banco = app.ctl.banco
    win = ctk.CTkToplevel(app)
    win.title("Banco de nomes")
    win.geometry("780x540")
    win.after(150, win.focus)
    busca = ctk.CTkEntry(win, placeholder_text="Buscar...")
    busca.pack(fill="x", padx=10, pady=(10, 4))
    caixa = ctk.CTkTextbox(win)
    caixa.pack(fill="both", expand=True, padx=10, pady=4)
    rodape = ctk.CTkLabel(win, text="", anchor="w")
    rodape.pack(fill="x", padx=12)

    def atualizar(_e=None):
        nomes = banco.listar_nomes(busca.get())
        caixa.configure(state="normal")
        caixa.delete("1.0", "end")
        caixa.insert("1.0", "\n".join(f"{len(n):>2}  {n}" for n in nomes))
        caixa.configure(state="disabled")
        rodape.configure(text=f"{len(nomes)} exibido(s) de {banco.total_nomes()}")

    def exportar():
        destino = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Texto", "*.txt")])
        if destino:
            messagebox.showinfo("Exportado", f"{banco.exportar_nomes(destino)} nomes salvos.")

    busca.bind("<KeyRelease>", atualizar)
    ctk.CTkButton(win, text="Exportar para .txt", command=exportar).pack(pady=8)
    atualizar()


def banco_de_pecas(app) -> None:
    banco = app.ctl.banco
    win = ctk.CTkToplevel(app)
    win.title("Banco de peças (modo offline)")
    win.geometry("860x600")
    win.after(150, win.focus)
    ctk.CTkLabel(win, anchor="w", justify="left", wraplength=800,
                 text="Peças são pedaços de frase que o modo offline combina. Etiquetas = características que precisam estar marcadas "
                      "(" + ", ".join(CARACTERISTICAS) + "). Use \"-masculino\" ou \"-feminino\" para excluir.").pack(fill="x", padx=10, pady=8)
    caixa = ctk.CTkTextbox(win, font=("Consolas", 11))
    caixa.pack(fill="both", expand=True, padx=10)
    form = ctk.CTkFrame(win)
    form.pack(fill="x", padx=10, pady=8)
    e_txt = ctk.CTkEntry(form, placeholder_text="Texto da peça (ex.: AMORTECE O IMPACTO)", width=330)
    e_txt.grid(row=0, column=0, padx=4, pady=4)
    c_tipo = ctk.CTkComboBox(form, values=TIPOS, width=140)
    c_tipo.set("acao")
    c_tipo.grid(row=0, column=1, padx=4)
    e_tags = ctk.CTkEntry(form, placeholder_text="etiquetas, separadas por vírgula", width=220)
    e_tags.grid(row=0, column=2, padx=4)

    def atualizar():
        caixa.configure(state="normal")
        caixa.delete("1.0", "end")
        for pc in banco.listar_pecas():
            caixa.insert("end", f"{pc['tipo']:<15} {pc['texto']:<55} [{', '.join(pc['etiquetas'])}] ({pc['origem']})\n")
        caixa.configure(state="disabled")

    def add():
        if e_txt.get().strip():
            tags = [t.strip() for t in e_tags.get().split(",") if t.strip()]
            banco.adicionar_peca(e_txt.get(), c_tipo.get(), tags)
            e_txt.delete(0, "end")
            atualizar()

    def remover():
        if e_txt.get().strip():
            banco.remover_peca(e_txt.get().strip().upper())
            e_txt.delete(0, "end")
            atualizar()

    ctk.CTkButton(form, text="Adicionar", width=90, command=add).grid(row=0, column=3, padx=4)
    ctk.CTkButton(form, text="Remover pelo texto", width=130, fg_color="gray50", command=remover).grid(row=0, column=4, padx=4)
    atualizar()


def analisar_dia(app) -> None:
    ctl = app.ctl
    win = ctk.CTkToplevel(app)
    win.title("Analisar o dia")
    win.geometry("820x560")
    win.after(150, win.focus)
    info = ctk.CTkLabel(win, text="Analisando o que aconteceu hoje...", wraplength=760, justify="left")
    info.pack(padx=10, pady=10, anchor="w")
    lista = ctk.CTkScrollableFrame(win)
    lista.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def trabalho():
        ia = ctl.ia if (ctl.ia and ctl.ia.tem_alguma) else None
        try:
            r = analise_dia.analisar(ctl.banco, ia)
        except Exception as e:  # noqa: BLE001
            r = ([], f"Erro na análise: {e}")
        win.after(0, lambda: mostrar(*r))

    def mostrar(propostas, origem):
        info.configure(text=f"{origem} Nada muda sem a sua aprovação; antes de aplicar o programa guarda uma cópia das regras.")
        if not propostas:
            ctk.CTkLabel(lista, text="Nenhuma proposta por enquanto.").pack(pady=20)
        for prop in propostas:
            linha = ctk.CTkFrame(lista)
            linha.pack(fill="x", pady=3, padx=2)
            ctk.CTkLabel(linha, text=prop.descricao(), wraplength=540, justify="left", anchor="w").pack(side="left", padx=8, pady=6, expand=True, fill="x")

            def aceitar(pr=prop, ln=linha):
                backup = analise_dia.aplicar(pr, ctl.banco)
                ctl.regras = Regras.carregar()
                for w in ln.winfo_children():
                    w.destroy()
                ctk.CTkLabel(ln, text=f"✅ Aplicado: {pr.valor} (backup em {backup})", wraplength=700, justify="left").pack(padx=8, pady=6)

            def recusar(ln=linha):
                ln.destroy()

            ctk.CTkButton(linha, text="Recusar", width=80, fg_color="gray50", command=recusar).pack(side="right", padx=4)
            ctk.CTkButton(linha, text="Aceitar", width=80, command=aceitar).pack(side="right", padx=4)

    threading.Thread(target=trabalho, daemon=True).start()
