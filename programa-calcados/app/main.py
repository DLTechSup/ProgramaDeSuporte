"""Programa de Nomes e Descricoes de Calcados - janela principal."""
from __future__ import annotations

import io
import sys
import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from . import ui_config, ui_janelas
from .banco import Banco
from .caminhos import LOGS, RAIZ
from .controlador import Controlador, inicio_para_ajuste
from .offline import CARACTERISTICAS
from .produto import Produto
from .provedores import ErroIA, Provedores

CATEGORIAS = ["Sandália", "Sandália anabela", "Sandália papete", "Sandália slide", "Sandália rasteira", "Tamanco", "Tamanco anabela",
              "Tamanco flatform", "Tamanco rasteiro", "Rasteira", "Chinelo", "Chinelo slide", "Mule", "Mule anabela", "Scarpin",
              "Slingback", "Sapatilha", "Sapatilha boneca", "Babuche", "Sapatênis", "Tênis casual", "Tênis esportivo", "Tênis"]
GENEROS = ["Feminino", "Masculino", "Unissex"]
PUBLICOS = ["Adulto", "Infantil", "Bebê", "Teen"]
PUBLICO_BD = {"Adulto": "adulto", "Infantil": "infantil", "Bebê": "bebe", "Teen": "teen"}


class Janela(ctk.CTk):
    def __init__(self, selftest: bool = False) -> None:
        super().__init__()
        self.title("Nomes e Descrições de Calçados")
        self.geometry("1040x780")
        self.minsize(900, 680)
        ctk.set_appearance_mode("light")
        self.prov = Provedores()
        self.banco = Banco()
        self.banco.importar_semente()
        self.ctl = Controlador(self.banco, self.prov)
        self.opcoes_nomes: list[str] = []
        self.var_nome = ctk.StringVar(value="")
        self.protocol("WM_DELETE_WINDOW", self._fechar)
        self._montar_topo()
        self._montar_produto()
        self._montar_abas()
        self.barra = ctk.CTkLabel(self, text="", anchor="w")
        self.barra.pack(fill="x", padx=14, pady=(0, 8))
        self._atualizar_topo()
        self._msg(f"Pronto. {self.banco.total_nomes()} nomes no banco.")
        if selftest:
            self.after(900, self._fim_selftest)
        elif not self.prov.tem_alguma:
            self.after(600, lambda: ui_config.abrir_assistente(self, self.prov, self._atualizar_topo))

    def _fim_selftest(self) -> None:
        """Usado pelo build: confere que a janela abre e que todas as bibliotecas vieram dentro do .exe."""
        try:
            import ddgs, freelm, httpx, rapidfuzz, selectolax  # noqa: F401,E401
            from .offline import gerar_nomes_offline
            p = Produto(None, "Dakota", "Z1", "Tamanco", "Feminino", "adulto", ["salto_bloco", "strass"])
            nomes = gerar_nomes_offline(self.banco, p)
            assert len(nomes) >= 8, f"modo offline gerou so {len(nomes)} nomes"
            (RAIZ / "selftest_ok.txt").write_text(f"ok {len(nomes)} nomes", encoding="utf-8")
        except Exception as e:  # noqa: BLE001
            (RAIZ / "selftest_erro.txt").write_text(f"{type(e).__name__}: {e}", encoding="utf-8")
        self.destroy()

    # ------------------------------------------------------------ infra
    def _msg(self, texto: str) -> None:
        self.barra.configure(text=texto)

    def _rodar(self, func, ao_terminar, texto="Trabalhando...") -> None:
        self._msg(texto)

        def alvo():
            try:
                r = func()
            except Exception as e:  # noqa: BLE001
                self.after(0, lambda err=e: self._erro(err))
                return
            self.after(0, lambda: ao_terminar(r))
        threading.Thread(target=alvo, daemon=True).start()

    def _erro(self, e: Exception) -> None:
        self._msg("")
        texto = str(e) if isinstance(e, ErroIA) else f"{type(e).__name__}: {e}"
        messagebox.showerror("Não foi possível concluir", texto)

    def _atualizar_topo(self) -> None:
        self.lbl_prov.configure(text=self.prov.resumo() if self.ctl.online else "Modo offline: sem IA")

    # ------------------------------------------------------------ topo
    def _montar_topo(self) -> None:
        topo = ctk.CTkFrame(self)
        topo.pack(fill="x", padx=10, pady=(10, 4))
        ctk.CTkLabel(topo, text="Modo:").pack(side="left", padx=(10, 4))
        self.modo = ctk.CTkSegmentedButton(topo, values=["Online", "Offline"], command=self._mudou_modo)
        self.modo.set("Online")
        self.modo.pack(side="left")
        self.lbl_prov = ctk.CTkLabel(topo, text="")
        self.lbl_prov.pack(side="left", padx=14)
        for texto, cmd in (("Banco de nomes", lambda: ui_janelas.banco_de_nomes(self)),
                           ("Banco de peças", lambda: ui_janelas.banco_de_pecas(self)),
                           ("Analisar o dia", lambda: ui_janelas.analisar_dia(self)),
                           ("Checar nome", lambda: ui_janelas.checar_nome(self)),
                           ("Configurações", lambda: ui_config.abrir_assistente(self, self.prov, self._atualizar_topo))):
            ctk.CTkButton(topo, text=texto, width=110, command=cmd).pack(side="right", padx=4)

    def _mudou_modo(self, valor: str) -> None:
        self.ctl.modo = valor
        if valor == "Offline":
            self.frame_carac.grid()
        else:
            self.frame_carac.grid_remove()
        self._atualizar_topo()

    # ------------------------------------------------------------ produto
    def _montar_produto(self) -> None:
        p = ctk.CTkFrame(self)
        p.pack(fill="x", padx=10, pady=4)
        self.e_marca = self._campo(p, "Marca", 0)
        self.e_ref = self._campo(p, "Referência", 1)
        self.c_cat = self._lista(p, "Categoria", CATEGORIAS, 2)
        self.c_gen = self._lista(p, "Gênero", GENEROS, 3)
        self.c_pub = self._lista(p, "Público", PUBLICOS, 4)
        self.c_gen.set("Feminino")
        self.c_pub.set("Adulto")
        botoes = ctk.CTkFrame(p, fg_color="transparent")
        botoes.grid(row=2, column=0, columnspan=5, sticky="w", padx=6, pady=6)
        ctk.CTkButton(botoes, text="Anexar fotos", width=120, command=self._anexar_fotos).pack(side="left", padx=4)
        ctk.CTkButton(botoes, text="Pesquisar", width=120, command=self._pesquisar).pack(side="left", padx=4)
        self.lbl_fotos = ctk.CTkLabel(botoes, text="Nenhuma foto anexada", text_color="gray40")
        self.lbl_fotos.pack(side="left", padx=10)
        self.faixa_fotos = ctk.CTkFrame(p, fg_color="transparent")
        self.faixa_fotos.grid(row=3, column=0, columnspan=5, sticky="w", padx=6)
        self.frame_carac = ctk.CTkFrame(p)
        self.frame_carac.grid(row=4, column=0, columnspan=5, sticky="ew", padx=6, pady=4)
        ctk.CTkLabel(self.frame_carac, text="Características (modo offline):").grid(row=0, column=0, columnspan=6, sticky="w", padx=6)
        self.vars_carac: dict[str, ctk.BooleanVar] = {}
        for i, (tag, rotulo) in enumerate(CARACTERISTICAS.items()):
            v = ctk.BooleanVar(value=False)
            self.vars_carac[tag] = v
            ctk.CTkCheckBox(self.frame_carac, text=rotulo, variable=v, width=150).grid(row=1 + i // 5, column=i % 5, sticky="w", padx=6, pady=2)
        self.frame_carac.grid_remove()
        for i in range(5):
            p.grid_columnconfigure(i, weight=1)

    def _campo(self, pai, rotulo, col):
        ctk.CTkLabel(pai, text=rotulo).grid(row=0, column=col, sticky="w", padx=8, pady=(6, 0))
        e = ctk.CTkEntry(pai)
        e.grid(row=1, column=col, sticky="ew", padx=8)
        return e

    def _lista(self, pai, rotulo, valores, col):
        ctk.CTkLabel(pai, text=rotulo).grid(row=0, column=col, sticky="w", padx=8, pady=(6, 0))
        c = ctk.CTkComboBox(pai, values=valores)
        c.set("")
        c.grid(row=1, column=col, sticky="ew", padx=8)
        return c

    def ler_produto_painel(self) -> Produto:
        """Produto temporario com o que esta nos campos (sem gravar no banco)."""
        return Produto(None, self.e_marca.get().strip(), self.e_ref.get().strip(), self.c_cat.get().strip(),
                       self.c_gen.get().strip(), PUBLICO_BD.get(self.c_pub.get(), "adulto"),
                       [t for t, v in self.vars_carac.items() if v.get()])

    def _confirmar_produto(self) -> Produto | None:
        t = self.ler_produto_painel()
        if not (t.marca and t.referencia and t.categoria):
            messagebox.showwarning("Atenção", "Preencha marca, referência e categoria.")
            return None
        return self.ctl.definir_produto(t.marca, t.referencia, t.categoria, t.genero, t.publico, t.caracteristicas)

    def _anexar_fotos(self) -> None:
        arqs = filedialog.askopenfilenames(title="Escolha as fotos do produto", filetypes=[("Fotos", "*.jpg *.jpeg *.png *.webp *.bmp")])
        if not arqs:
            return
        self.ctl.fotos = [Path(a) for a in arqs]
        for w in self.faixa_fotos.winfo_children():
            w.destroy()
        from PIL import Image
        for caminho in self.ctl.fotos[:8]:
            try:
                im = Image.open(caminho)
                im.thumbnail((64, 64))
                img = ctk.CTkImage(light_image=im, size=im.size)
                ctk.CTkLabel(self.faixa_fotos, image=img, text="").pack(side="left", padx=3)
            except Exception:  # noqa: BLE001
                pass
        self.lbl_fotos.configure(text=f"{len(self.ctl.fotos)} foto(s) anexada(s)")

    # ------------------------------------------------------------ abas
    def _montar_abas(self) -> None:
        self.abas = ctk.CTkTabview(self)
        self.abas.pack(fill="both", expand=True, padx=10, pady=4)
        self._aba_nomes(self.abas.add("Nomes"))
        self._aba_descricao(self.abas.add("Descrição"))
        self._aba_verificacao(self.abas.add("Verificação"))
        self._aba_correcoes(self.abas.add("Correções"))

    # ---- Nomes
    def _aba_nomes(self, aba) -> None:
        linha = ctk.CTkFrame(aba, fg_color="transparent")
        linha.pack(fill="x")
        ctk.CTkButton(linha, text="Criar nomes", width=120, command=lambda: self._criar_nomes(False)).pack(side="left", padx=4)
        ctk.CTkButton(linha, text="Mais sugestões", width=130, command=lambda: self._criar_nomes(True)).pack(side="left", padx=4)
        ctk.CTkButton(linha, text="Gostei, mas ajuste o final", width=190, command=self._ajustar_final).pack(side="left", padx=4)
        self.e_evitar = ctk.CTkEntry(aba, placeholder_text="Evitar nesta rodada (ex.: charme, sola, descanso)")
        self.e_evitar.pack(fill="x", padx=4, pady=6)
        self.lista_nomes = ctk.CTkScrollableFrame(aba, height=260)
        self.lista_nomes.pack(fill="both", expand=True, padx=4)
        self.lbl_aviso = ctk.CTkLabel(aba, text="", text_color="firebrick", wraplength=900, justify="left", anchor="w")
        self.lbl_aviso.pack(fill="x", padx=4)
        self.lbl_controle = ctk.CTkLabel(aba, text="", wraplength=900, justify="left", anchor="w", text_color="gray30")
        self.lbl_controle.pack(fill="x", padx=4)
        ctk.CTkButton(aba, text="Vou usar esse", width=160, command=self._usar_nome).pack(pady=6)

    def _criar_nomes(self, mais: bool) -> None:
        if self._confirmar_produto() is None:
            return
        ok, msg = self.ctl.pode_criar_nomes
        if not ok:
            messagebox.showinfo("Antes de criar os nomes", msg)
            return
        evitar = self.e_evitar.get()
        self._rodar(lambda: self.ctl.criar_nomes(evitar=evitar), self._mostrar_nomes, "Criando nomes e conferindo as regras...")

    def _ajustar_final(self) -> None:
        nome = self.var_nome.get()
        if not nome:
            messagebox.showinfo("Gostei, mas ajuste o final", "Selecione primeiro um dos nomes da lista.")
            return
        inicio = inicio_para_ajuste(nome, self.ctl.produto)
        evitar = self.e_evitar.get()
        self._rodar(lambda: self.ctl.criar_nomes(evitar=evitar, manter_inicio=inicio), self._mostrar_nomes,
                    f"Mantendo \"{inicio}\" e criando finais novos...")

    def _mostrar_nomes(self, res) -> None:
        for w in self.lista_nomes.winfo_children():
            w.destroy()
        self.var_nome.set("")
        for n in res.nomes:
            estrela = "  ★ recomendado" if n == res.recomendada else ""
            ctk.CTkRadioButton(self.lista_nomes, text=f"({len(n)})  {n}{estrela}", variable=self.var_nome, value=n).pack(anchor="w", pady=3, padx=4)
        if res.recomendada:
            self.var_nome.set(res.recomendada)
        self.lbl_aviso.configure(text=res.aviso)
        extra = f"Recomendo o ★: {res.motivo}\n" if res.motivo else ""
        self.lbl_controle.configure(text=extra + (f"Já usados neste produto (não volto a usar): {res.controle}" if res.controle else ""))
        self._msg(f"{len(res.nomes)} nome(s) · respondeu: {res.provedor or '—'} · {len(res.rejeitados)} barrado(s) pelo validador")
        self._atualizar_topo()

    def _usar_nome(self) -> None:
        nome = self.var_nome.get()
        if not nome:
            messagebox.showinfo("Vou usar esse", "Selecione um nome da lista.")
            return
        self.ctl.aprovar_nome(nome)
        self.abas.set("Descrição")
        self._gerar_descricao()

    # ---- Descricao
    def _aba_descricao(self, aba) -> None:
        linha = ctk.CTkFrame(aba, fg_color="transparent")
        linha.pack(fill="x")
        ctk.CTkButton(linha, text="Gerar descrição", width=130, command=self._gerar_descricao).pack(side="left", padx=4)
        ctk.CTkButton(linha, text="Refazer só o final", width=140, command=self._refazer_final).pack(side="left", padx=4)
        ctk.CTkButton(linha, text="Copiar (nome + descrição)", width=190, command=self._copiar).pack(side="left", padx=4)
        self.lbl_nome_final = ctk.CTkLabel(aba, text="", font=("Segoe UI", 13, "bold"), wraplength=900, justify="left", anchor="w")
        self.lbl_nome_final.pack(fill="x", padx=4, pady=4)
        self.txt_desc = ctk.CTkTextbox(aba, font=("Segoe UI", 12), wrap="word")
        self.txt_desc.pack(fill="both", expand=True, padx=4)
        self.lbl_erros_desc = ctk.CTkLabel(aba, text="", text_color="firebrick", wraplength=900, justify="left", anchor="w")
        self.lbl_erros_desc.pack(fill="x", padx=4)

    def _gerar_descricao(self) -> None:
        if not self.ctl.nome_final:
            messagebox.showinfo("Descrição", "Escolha um nome na aba Nomes (\"Vou usar esse\") antes.")
            return
        self._rodar(self.ctl.gerar_descricao, self._mostrar_descricao, "Escrevendo a descrição...")

    def _refazer_final(self) -> None:
        self._rodar(self.ctl.refazer_final, self._mostrar_descricao, "Refazendo o parágrafo final...")

    def _mostrar_descricao(self, resultado) -> None:
        desc, erros = resultado
        self.lbl_nome_final.configure(text=self.ctl.nome_final)
        self.txt_desc.delete("1.0", "end")
        self.txt_desc.insert("1.0", desc.texto())
        self.lbl_erros_desc.configure(text=("Atenção, itens fora do padrão: " + "; ".join(erros)) if erros else "")
        self._msg("Descrição pronta. Você pode editar o texto antes de copiar.")

    def _copiar(self) -> None:
        texto = self.ctl.texto_para_copiar(self.txt_desc.get("1.0", "end").strip())
        self.clipboard_clear()
        self.clipboard_append(texto)
        self._msg("Nome e descrição copiados. Cole na Nuvemshop.")

    # ---- Verificacao
    def _aba_verificacao(self, aba) -> None:
        topo = ctk.CTkFrame(aba, fg_color="transparent")
        topo.pack(fill="x")
        self.lbl_peso = ctk.CTkLabel(topo, text="Peso: —", anchor="w")
        self.lbl_peso.pack(side="left", padx=4)
        self.lbl_cor = ctk.CTkLabel(topo, text="Campo de cor: —", anchor="w")
        self.lbl_cor.pack(side="left", padx=16)
        ctk.CTkButton(topo, text="Inserir peso na descrição", width=190, command=self._inserir_peso).pack(side="right", padx=4)
        self.frame_cartoes = ctk.CTkScrollableFrame(aba, height=170)
        self.txt_log = ctk.CTkTextbox(aba, font=("Consolas", 11), wrap="word")
        self.txt_log.pack(fill="both", expand=True, padx=4, pady=6)

    def _pesquisar(self) -> None:
        if self._confirmar_produto() is None:
            return
        self._rodar(lambda: self.ctl.pesquisar(progresso=lambda m: self.after(0, lambda: self._msg(m))), self._depois_pesquisa, "Pesquisando na internet...")

    def _depois_pesquisa(self, modo: str) -> None:
        self.abas.set("Verificação")
        pesq = self.ctl.pesquisa
        self.lbl_peso.configure(text=f"Peso: {pesq.peso}")
        self.lbl_cor.configure(text=f"Campo de cor: {pesq.cor_sugerida or '—'}")
        self.txt_log.delete("1.0", "end")
        self.txt_log.insert("1.0", self.ctl.log_texto)
        self.frame_cartoes.pack_forget()
        for w in self.frame_cartoes.winfo_children():
            w.destroy()
        if modo == "cartoes":
            self._mostrar_cartoes()
        else:
            self._msg(f"Pesquisa pronta: {len(pesq.paginas)} página(s). Veja o log abaixo.")

    def _mostrar_cartoes(self) -> None:
        cartoes = self.ctl.cartoes
        self.frame_cartoes.pack(fill="x", padx=4, before=self.txt_log)
        if not cartoes:
            ctk.CTkLabel(self.frame_cartoes, text="Não achei páginas com foto desse produto depois de várias buscas. "
                         "Tente anexar uma foto ou conferir a referência.", wraplength=800, justify="left").pack(pady=10)
            self._msg("Nenhum link com foto encontrado.")
            return
        ctk.CTkLabel(self.frame_cartoes, text="Algum desses links mostra o produto que você tem?", font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=6)
        for pg in cartoes:
            linha = ctk.CTkFrame(self.frame_cartoes)
            linha.pack(fill="x", pady=3, padx=4)
            miniatura = ctk.CTkLabel(linha, text="(carregando\nfoto)", width=90)
            miniatura.pack(side="left", padx=6, pady=6)
            tipo = "referência exata" if pg.exata else "referência parecida (mesma linha)"
            txt = f"{pg.site} — {tipo}\n{pg.titulo[:110]}\n{pg.descricao[:140]}"
            ctk.CTkLabel(linha, text=txt, wraplength=560, justify="left", anchor="w").pack(side="left", padx=6, expand=True, fill="x")
            ctk.CTkButton(linha, text="É este", width=90, command=lambda p=pg: self._confirmar_cartao(p)).pack(side="right", padx=6)
            threading.Thread(target=self._carregar_miniatura, args=(pg.imagem, miniatura), daemon=True).start()
        ctk.CTkButton(self.frame_cartoes, text="Nenhum confere", fg_color="gray50", command=self._nenhum_confere).pack(pady=6)
        self._msg("Escolha o link que mostra o seu produto para liberar \"Criar nomes\".")

    def _carregar_miniatura(self, url: str, rotulo) -> None:
        try:
            from PIL import Image
            from .pesquisa import baixar_imagem
            im = Image.open(io.BytesIO(baixar_imagem(url))).convert("RGB")
            im.thumbnail((90, 90))

            def pr():
                img = ctk.CTkImage(light_image=im, size=im.size)
                rotulo.configure(image=img, text="")
                rotulo.image = img
            self.after(0, pr)
        except Exception:  # noqa: BLE001
            self.after(0, lambda: rotulo.configure(text="(sem foto)"))

    def _confirmar_cartao(self, pg) -> None:
        self.ctl.confirmar_cartao(pg)
        self.txt_log.delete("1.0", "end")
        self.txt_log.insert("1.0", self.ctl.log_texto)
        self._msg(f"Produto confirmado ({pg.site}). Agora você pode criar os nomes.")
        messagebox.showinfo("Confirmado", "Link confirmado como base do produto. Vá para a aba Nomes e clique em Criar nomes.")

    def _nenhum_confere(self) -> None:
        self.ctl.confirmar_cartao(None)
        messagebox.showinfo("Nenhum confere", "Tente conferir a referência, anexar uma foto ou pesquisar de novo.")

    def _inserir_peso(self) -> None:
        try:
            texto = self.ctl.inserir_peso()
        except ErroIA as e:
            messagebox.showinfo("Peso", str(e))
            return
        self.txt_desc.delete("1.0", "end")
        self.txt_desc.insert("1.0", texto)
        self.abas.set("Descrição")

    # ---- Correcoes
    def _aba_correcoes(self, aba) -> None:
        ctk.CTkLabel(aba, text="Escreva uma correção (ex.: \"não use pleonasmo\", \"masculino sem charme\"). Ela entra em todos os próximos pedidos.",
                     wraplength=900, justify="left", anchor="w").pack(fill="x", padx=4, pady=4)
        self.e_corr = ctk.CTkEntry(aba)
        self.e_corr.pack(fill="x", padx=4)
        linha = ctk.CTkFrame(aba, fg_color="transparent")
        linha.pack(fill="x", pady=6)
        self.escopo = ctk.CTkSegmentedButton(linha, values=["Só este produto", "Regra geral"])
        self.escopo.set("Só este produto")
        self.escopo.pack(side="left", padx=4)
        ctk.CTkButton(linha, text="Salvar correção", command=self._salvar_correcao).pack(side="left", padx=8)
        self.txt_corr = ctk.CTkTextbox(aba)
        self.txt_corr.pack(fill="both", expand=True, padx=4)

    def _salvar_correcao(self) -> None:
        if self._confirmar_produto() is None:
            return
        self.ctl.corrigir(self.e_corr.get(), self.escopo.get() == "Regra geral")
        self.e_corr.delete(0, "end")
        self.txt_corr.delete("1.0", "end")
        self.txt_corr.insert("1.0", "\n".join("• " + c for c in self.banco.listar_correcoes(self.ctl.produto.id)))
        self._msg("Correção salva.")

    # ------------------------------------------------------------ saida
    def _fechar(self) -> None:
        try:
            if self.banco.dados_do_dia()["aprovados"] and messagebox.askyesno(
                    "Antes de sair", "Quer analisar o dia para melhorar as regras?\n(Nada muda sem a sua aprovação.)"):
                ui_janelas.analisar_dia(self)
                return
        except Exception:  # noqa: BLE001
            pass
        self.banco.fechar()
        self.destroy()


def main() -> None:
    LOGS.mkdir(exist_ok=True)
    Janela(selftest="--selftest" in sys.argv).mainloop()


if __name__ == "__main__":
    main()
