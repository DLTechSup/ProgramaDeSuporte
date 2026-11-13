"""Logica do programa, separada da janela (para poder testar sem interface)."""
from __future__ import annotations

import json
from pathlib import Path

from . import criador, offline, pesquisa as pq
from .banco import Banco
from .criador import Descricao, ResultadoNomes
from .produto import Produto
from .provedores import ErroIA
from .validador import Contexto, Regras


class Controlador:
    def __init__(self, banco: Banco, ia, buscar=None, abrir=None) -> None:
        self.banco, self.ia = banco, ia
        self.regras = Regras.carregar()
        self._buscar, self._abrir = buscar or pq.busca_ddgs, abrir or pq.baixar
        self.modo = "Online"
        self.produto = Produto()
        self.fotos: list[Path] = []
        self.etiqueta: dict = {}
        self.pesquisa: pq.ResultadoPesquisa | None = None
        self.base_pagina: pq.Pagina | None = None
        self.cartoes: list[pq.Pagina] = []
        self.resultado: ResultadoNomes | None = None
        self.nome_final = ""
        self.descricao: Descricao | None = None
        self.log_texto = ""
        offline.semear_pecas(banco)

    # ---- produto ------------------------------------------------------
    @property
    def online(self) -> bool:
        return self.modo == "Online"

    def definir_produto(self, marca, referencia, categoria, genero, publico, caracteristicas=()) -> Produto:
        novo = (marca.strip(), referencia.strip()) != (self.produto.marca, self.produto.referencia) or self.produto.id is None
        if novo:
            pid = self.banco.criar_produto(marca, referencia, categoria, genero, publico)
            self.produto = Produto(pid)
            self.resultado, self.descricao, self.nome_final = None, None, ""
            self.pesquisa, self.base_pagina, self.cartoes, self.etiqueta = None, None, [], {}
        p = self.produto
        p.marca, p.referencia, p.categoria = marca.strip(), referencia.strip(), categoria.strip()
        p.genero, p.publico, p.caracteristicas = genero.strip(), publico, list(caracteristicas)
        return p

    @property
    def pode_criar_nomes(self) -> tuple[bool, str]:
        if not (self.produto.marca and self.produto.referencia and self.produto.categoria):
            return False, "Preencha marca, referência e categoria."
        if self.online and not self.fotos and self.base_pagina is None:
            return False, "Sem foto: clique em Pesquisar e confirme qual link é o seu produto."
        return True, ""

    # ---- pesquisa -------------------------------------------------------
    def pesquisar(self, progresso=lambda m: None) -> str:
        """Devolve 'foto' (log pronto) ou 'cartoes' (esperando confirmacao do usuario)."""
        p = self.produto
        if self.online and self.fotos:
            try:
                progresso("Lendo a etiqueta da caixa nas fotos...")
                self.etiqueta = criador.ler_etiqueta(self.ia, self.fotos)
            except ErroIA as e:
                progresso(f"Não consegui ler a etiqueta pela IA: {e}")
        aviso = ""
        ref_foto = str(self.etiqueta.get("referencia", "")).strip()
        if ref_foto and pq.classificar_referencia(ref_foto, p.referencia) != (True, False):
            aviso = f"ATENÇÃO: a referência lida na foto ({ref_foto}) é diferente da digitada ({p.referencia}). Confira antes de seguir."
        self.pesquisa = pq.pesquisar(p.marca, p.referencia, p.categoria, p.genero, busca=self._buscar, abrir=self._abrir, progresso=progresso)
        for pg in self.pesquisa.paginas:
            self.banco.salvar_pesquisa(p.id, "; ".join(self.pesquisa.consultas), pg.url, pg.titulo, json.dumps(pg.dados, ensure_ascii=False))
        if not self.pesquisa.cor_sugerida and self.etiqueta.get("cor"):
            self.pesquisa.cor_sugerida = pq.sugerir_cor(f"{self.etiqueta.get('cor')} {self.etiqueta.get('codigo_cor', '')}")
        self.log_texto = (aviso + "\n\n" if aviso else "") + pq.salvar_log(p.marca, p.referencia, self.pesquisa, etiqueta=self.etiqueta or None)
        if self.fotos:
            return "foto"
        self.cartoes = pq.candidatos_sem_foto(self.pesquisa)
        return "cartoes"

    def confirmar_cartao(self, pagina: pq.Pagina | None) -> None:
        self.base_pagina = pagina
        if pagina is not None and self.pesquisa is not None:
            self.log_texto += f"\n\n## Base visual\n- Link confirmado pelo usuário (não foi enviada foto): {pagina.url}"

    def _dados_ia(self) -> tuple[str, str]:
        pesq = self.pesquisa.resumo_para_ia() if self.pesquisa else ""
        if self.base_pagina is not None:
            pesq = f"[BASE CONFIRMADA PELO USUÁRIO] {self.base_pagina.url}: {self.base_pagina.titulo} {json.dumps(self.base_pagina.dados, ensure_ascii=False)}\n" + pesq
        et = json.dumps(self.etiqueta, ensure_ascii=False) if self.etiqueta else ""
        return pesq, et

    # ---- nomes ----------------------------------------------------------
    def registrar_evitar(self, evitar: str) -> None:
        if evitar.strip() and self.produto.id:
            self.banco.adicionar_correcao(self.produto.id, "EVITAR: " + evitar.strip(), "produto")

    def criar_nomes(self, evitar: str = "", manter_inicio: str = "") -> ResultadoNomes:
        ok, msg = self.pode_criar_nomes
        if not ok:
            raise ErroIA(msg)
        self.registrar_evitar(evitar)
        if self.online:
            pesq, et = self._dados_ia()
            self.resultado = criador.gerar_nomes(self.ia, self.banco, self.produto, pesquisa=pesq, etiqueta=et,
                                                 fotos=(self.fotos if (self.fotos and self.pesquisa is None) else None),
                                                 evitar=evitar, manter_inicio=manter_inicio, regras=self.regras)
        else:
            nomes = offline.gerar_nomes_offline(self.banco, self.produto, regras=self.regras, evitar=evitar)
            r = ResultadoNomes(nomes=nomes, provedor="offline", recomendada=nomes[0] if nomes else "",
                               motivo="Primeiro da lista que passou em todas as regras.")
            if len(nomes) < 8:
                r.aviso = f"Só {len(nomes)} nome(s) possíveis com as características marcadas. Marque mais características ou cadastre peças."
            self.resultado = r
        return self.resultado

    def aprovar_nome(self, nome: str) -> None:
        self.nome_final = nome
        self.banco.aprovar_nome(self.produto.id, nome)
        self.banco.definir_status(self.produto.id, "descricao")
        offline.aprender_de_nome(self.banco, nome, self.produto)

    # ---- descricao ------------------------------------------------------
    def gerar_descricao(self) -> tuple[Descricao, list[str]]:
        if self.online:
            pesq, et = self._dados_ia()
            self.descricao, erros = criador.gerar_descricao(self.ia, self.banco, self.produto, self.nome_final,
                                                            pesquisa=pesq, etiqueta=et, regras=self.regras)
        else:
            self.descricao, erros = offline.gerar_descricao_offline(self.banco, self.produto, self.nome_final, regras=self.regras)
            self.banco.salvar_descricao(self.produto.id, self.descricao.texto(), self.descricao.frase_efeito, self.descricao.paragrafo_final)
        self.banco.definir_status(self.produto.id, "concluido")
        return self.descricao, erros

    def refazer_final(self) -> tuple[Descricao, list[str]]:
        if self.descricao is None:
            raise ErroIA("Gere a descrição primeiro.")
        if self.online:
            self.descricao, erros = criador.refazer_final(self.ia, self.banco, self.produto, self.nome_final, self.descricao, regras=self.regras)
        else:
            d, erros = offline.gerar_descricao_offline(self.banco, self.produto, self.nome_final, regras=self.regras)
            self.descricao.paragrafo_final = d.paragrafo_final
        return self.descricao, erros

    def inserir_peso(self) -> str:
        if self.descricao is None:
            raise ErroIA("Gere a descrição primeiro.")
        peso = self.pesquisa.peso if self.pesquisa else "não encontrado"
        if peso.startswith("não"):
            raise ErroIA("Peso não encontrado na pesquisa.")
        self.descricao.topicos["Peso"] = peso.split(" (ATENÇÃO")[0]
        return self.descricao.texto()

    def texto_para_copiar(self, texto_descricao: str | None = None) -> str:
        corpo = texto_descricao if texto_descricao is not None else (self.descricao.texto() if self.descricao else "")
        return f"{self.nome_final}\n\n{corpo}".strip()

    # ---- correcoes ------------------------------------------------------
    def corrigir(self, texto: str, geral: bool) -> None:
        if texto.strip():
            self.banco.adicionar_correcao(self.produto.id, texto, "geral" if geral else "produto")


CONECTORES_CORTE = {"E", "COM", "PARA", "QUE"}


def inicio_para_ajuste(nome: str, produto: Produto) -> str:
    """'Gostei, mas ajuste o final': mantem categoria + marca + o comeco do miolo (ate o primeiro conector)."""
    tokens = nome.split()
    n_pref = len(produto.categoria_completa.split()) + len(produto.marca.split())
    n_ref = len(produto.referencia.split())
    miolo_t = tokens[n_pref:len(tokens) - n_ref] if n_ref and len(tokens) > n_pref + n_ref else tokens[n_pref:]
    corte = next((i for i, w in enumerate(miolo_t) if w.upper() in CONECTORES_CORTE and i >= 2), len(miolo_t) // 2)
    return " ".join(tokens[:n_pref] + miolo_t[:corte])
