"""Programa de Nomes e Descricoes de Calcados - janela principal (etapa 1: base)."""
from __future__ import annotations

import json
import os
from tkinter import filedialog, messagebox

import customtkinter as ctk

from .banco import Banco
from .caminhos import CONFIG, LOGS

CATEGORIAS = ["Sandália", "Rasteira", "Chinelo", "Tênis", "Sapatilha", "Scarpin", "Bota", "Sapato", "Mocassim", "Tamanco", "Anabela"]
GENEROS = ["Feminino", "Masculino", "Unissex"]
PUBLICOS = ["Adulto", "Infantil", "Bebê", "Teen"]
PUBLICO_BD = {"Adulto": "adulto", "Infantil": "infantil", "Bebê": "bebe", "Teen": "teen"}


def ler_configuracoes() -> dict:
    return json.loads((CONFIG / "configuracoes.json").read_text(encoding="utf-8"))


class Janela(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Nomes e Descrições de Calçados")
        self.geometry("980x680")
        self.minsize(860, 600)
        ctk.set_appearance_mode("light")
        self.config_geral = ler_configuracoes()
        self.banco = Banco()
        novos = self.banco.importar_semente()
        self.produto_id: int | None = None
        self.protocol("WM_DELETE_WINDOW", self._fechar)
        self._montar_topo()
        self._montar_produto()
        self._montar_abas()
        self._montar_barra()
        self._mensagem_barra(f"Pronto. {self.banco.total_nomes()} nomes no banco" + (f" ({novos} importados agora)." if novos else "."))

    # ---- topo ------------------------------------------------------------
    def _montar_topo(self) -> None:
        topo = ctk.CTkFrame(self)
        topo.pack(fill="x", padx=10, pady=(10, 4))
        ctk.CTkLabel(topo, text="Modo:").pack(side="left", padx=(10, 4))
        self.modo = ctk.CTkSegmentedButton(topo, values=["Online", "Offline"])
        self.modo.set("Online" if self.config_geral.get("modo_padrao") == "online" else "Offline")
        self.modo.pack(side="left")
        self.lbl_provedores = ctk.CTkLabel(topo, text="IA: nenhum provedor configurado ainda (etapa 4)")
        self.lbl_provedores.pack(side="left", padx=16)
        ctk.CTkButton(topo, text="Banco de nomes", width=130, command=self._abrir_banco_nomes).pack(side="right", padx=8)

    # ---- painel do produto ------------------------------------------------
    def _montar_produto(self) -> None:
        p = ctk.CTkFrame(self)
        p.pack(fill="x", padx=10, pady=4)
        self.e_marca = self._campo(p, "Marca", 0, 0)
        self.e_ref = self._campo(p, "Referência", 0, 1)
        self.c_cat = self._lista(p, "Categoria", CATEGORIAS, 0, 2)
        self.c_gen = self._lista(p, "Gênero", GENEROS, 0, 3)
        self.c_pub = self._lista(p, "Público", PUBLICOS, 0, 4)
        ctk.CTkButton(p, text="Anexar fotos", width=120, command=self._em_breve).grid(row=2, column=0, padx=8, pady=8, sticky="w")
        ctk.CTkButton(p, text="Pesquisar", width=120, command=self._em_breve).grid(row=2, column=1, padx=8, pady=8, sticky="w")
        ctk.CTkButton(p, text="Salvar produto", width=120, command=self._salvar_produto).grid(row=2, column=2, padx=8, pady=8, sticky="w")
        for i in range(5):
            p.grid_columnconfigure(i, weight=1)

    def _campo(self, pai, rotulo, linha, col):
        ctk.CTkLabel(pai, text=rotulo).grid(row=linha, column=col, sticky="w", padx=8, pady=(6, 0))
        e = ctk.CTkEntry(pai)
        e.grid(row=linha + 1, column=col, sticky="ew", padx=8)
        return e

    def _lista(self, pai, rotulo, valores, linha, col):
        ctk.CTkLabel(pai, text=rotulo).grid(row=linha, column=col, sticky="w", padx=8, pady=(6, 0))
        c = ctk.CTkComboBox(pai, values=valores)
        c.set("")
        c.grid(row=linha + 1, column=col, sticky="ew", padx=8)
        return c

    # ---- abas -------------------------------------------------------------
    def _montar_abas(self) -> None:
        self.abas = ctk.CTkTabview(self)
        self.abas.pack(fill="both", expand=True, padx=10, pady=4)
        textos = {
            "Nomes": "Criação de nomes: etapas 3 (offline) e 5 (online).",
            "Descrição": "Descrição no padrão da versão 5: etapas 3 e 5.",
            "Verificação": "Log da pesquisa, peso e sugestão de campo de cor: etapa 6.",
            "Correções": "Correções do usuário e 'Analisar o dia': etapa 7.",
        }
        for nome, texto in textos.items():
            aba = self.abas.add(nome)
            ctk.CTkLabel(aba, text=texto, text_color="gray40").pack(pady=40)

    def _montar_barra(self) -> None:
        self.barra = ctk.CTkLabel(self, text="", anchor="w")
        self.barra.pack(fill="x", padx=14, pady=(0, 8))

    def _mensagem_barra(self, msg: str) -> None:
        self.barra.configure(text=msg)

    # ---- acoes ------------------------------------------------------------
    def _em_breve(self) -> None:
        messagebox.showinfo("Em breve", "Esta função será feita nas próximas etapas do plano.")

    def _salvar_produto(self) -> None:
        marca, ref = self.e_marca.get().strip(), self.e_ref.get().strip()
        if not marca or not ref:
            messagebox.showwarning("Atenção", "Preencha a marca e a referência.")
            return
        self.produto_id = self.banco.criar_produto(
            marca, ref, self.c_cat.get(), self.c_gen.get(), PUBLICO_BD.get(self.c_pub.get(), ""))
        self._mensagem_barra(f"Produto salvo: {marca} {ref}")

    def _abrir_banco_nomes(self) -> None:
        win = ctk.CTkToplevel(self)
        win.title("Banco de nomes")
        win.geometry("760x520")
        win.after(100, win.focus)
        busca = ctk.CTkEntry(win, placeholder_text="Buscar...")
        busca.pack(fill="x", padx=10, pady=(10, 4))
        caixa = ctk.CTkTextbox(win)
        caixa.pack(fill="both", expand=True, padx=10, pady=4)
        rodape = ctk.CTkLabel(win, text="", anchor="w")
        rodape.pack(fill="x", padx=12)

        def atualizar(*_):
            nomes = self.banco.listar_nomes(busca.get())
            caixa.configure(state="normal")
            caixa.delete("1.0", "end")
            caixa.insert("1.0", "\n".join(f"{len(n):>2}  {n}" for n in nomes))
            caixa.configure(state="disabled")
            rodape.configure(text=f"{len(nomes)} exibido(s) de {self.banco.total_nomes()}")

        def exportar():
            destino = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Texto", "*.txt")])
            if destino:
                n = self.banco.exportar_nomes(destino)
                messagebox.showinfo("Exportado", f"{n} nomes salvos.")

        busca.bind("<KeyRelease>", atualizar)
        ctk.CTkButton(win, text="Exportar para .txt", command=exportar).pack(pady=8)
        atualizar()

    def _fechar(self) -> None:
        self.banco.fechar()
        self.destroy()


def main() -> None:
    LOGS.mkdir(exist_ok=True)
    Janela().mainloop()


if __name__ == "__main__":
    main()
