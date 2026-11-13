"""Criacao online: pede nomes/descricao a IA, filtra pelo validador e tenta de novo se sobrar pouco."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from .banco import Banco
from .caminhos import CONFIG, REGRAS
from .prompts import linha_controle, pedido_descricao, pedido_etiqueta, pedido_nomes
from .produto import Produto
from .provedores import extrair_json
from .texto import contem_frase, normalizar
from .validador import Contexto, Regras, palavras_evitar, validar


def ler_config() -> dict:
    return json.loads((CONFIG / "configuracoes.json").read_text(encoding="utf-8"))


@dataclass
class ResultadoNomes:
    nomes: list[str] = field(default_factory=list)
    recomendada: str = ""
    motivo: str = ""
    provedor: str = ""
    rejeitados: list[str] = field(default_factory=list)
    controle: str = ""
    aviso: str = ""


def contexto_do_produto(p: Produto, banco: Banco, evitar: str = "") -> Contexto:
    """Contexto do validador. 'evitar' = texto do campo + correcoes EVITAR ja salvas (geral ou deste produto)."""
    salvas = [c for c in (banco.listar_correcoes(p.id) if p.id else []) if c.upper().startswith("EVITAR:")]
    return Contexto(p.marca, p.referencia, p.categoria_completa, p.genero, p.publico,
                    aprovados=banco.listar_nomes(limite=10**9),
                    anteriores=banco.sugestoes_do_produto(p.id) if p.id else [],
                    evitar=palavras_evitar(evitar, *salvas))


def filtrar_candidatos(candidatos: list[str], ctx: Contexto, regras: Regras, *, maximo: int,
                       manter_inicio: str = "") -> tuple[list[str], list[tuple[str, str]]]:
    """Devolve (aceitos, [(nome, motivo)]). Cada aceito entra no lote e nas 'anteriores'."""
    aceitos, rejeitados, vistos = [], [], set()
    inicio = normalizar(manter_inicio)
    for bruto in candidatos:
        nome = re.sub(r"\s+", " ", str(bruto)).strip().upper()
        if not nome or nome in vistos:
            continue
        vistos.add(nome)
        if len(aceitos) >= maximo:
            rejeitados.append((nome, "excedente (a lista já está cheia)"))
            continue
        if inicio and not normalizar(nome).startswith(inicio):
            rejeitados.append((nome, "não manteve o início pedido"))
            continue
        r = validar(nome, ctx, regras)
        if r.aprovado:
            aceitos.append(nome)
            ctx.lote.append(nome)
            ctx.anteriores.append(nome)
        else:
            rejeitados.append((nome, "; ".join(r.motivos)))
    return aceitos, rejeitados


def gerar_nomes(ia, banco: Banco, p: Produto, *, pesquisa="", etiqueta="", fotos=None, evitar="",
                manter_inicio="", regras: Regras | None = None, tentativas: int = 3) -> ResultadoNomes:
    cfg, regras = ler_config(), regras or Regras.carregar()
    ctx = contexto_do_produto(p, banco, evitar)
    correcoes = banco.listar_correcoes(p.id) if p.id else []
    lote = banco.proximo_lote(p.id) if p.id else 1
    alvo, minimo = cfg["sugestoes_exibidas"], 8
    res, motivos_prompt = ResultadoNomes(), []
    recomendada_bruta, motivo_ia = "", ""
    for i in range(tentativas):
        sistema, usuario = pedido_nomes(p, ctx, pesquisa=pesquisa, etiqueta=etiqueta, correcoes=correcoes, evitar=evitar,
                                        quantidade=cfg["sugestoes_pedidas"], rejeicoes=motivos_prompt, manter_inicio=manter_inicio, liberadas=regras.sob_demanda)
        resp = ia.chat(sistema, usuario, imagens=fotos if i == 0 else None)
        res.provedor = resp.provedor
        dados = extrair_json(resp.texto)
        cands = [str(x) for x in dados.get("sugestoes", [])]
        if not recomendada_bruta and isinstance(dados.get("recomendada"), int) and 0 <= dados["recomendada"] < len(cands):
            recomendada_bruta = re.sub(r"\s+", " ", cands[dados["recomendada"]]).strip().upper()
            motivo_ia = str(dados.get("motivo", ""))
        aceitos, rejeitados = filtrar_candidatos(cands, ctx, regras, maximo=alvo - len(res.nomes), manter_inicio=manter_inicio)
        res.nomes += aceitos
        res.rejeitados += [f"{n} -> {m}" for n, m in rejeitados]
        if p.id:
            for n in aceitos:
                banco.salvar_sugestao(p.id, n, resp.provedor, lote, True)
            for n, m in rejeitados:
                banco.salvar_sugestao(p.id, n, resp.provedor, lote, False, m)
        if len(res.nomes) >= alvo:
            break
        motivos_prompt = [f"{n} -> {m}" for n, m in rejeitados][:15]
    if len(res.nomes) < minimo:
        res.aviso = f"Só {len(res.nomes)} nome(s) passaram no validador. Clique em \"Mais sugestões\" ou ajuste as palavras a evitar."
    res.recomendada = recomendada_bruta if recomendada_bruta in res.nomes else (res.nomes[0] if res.nomes else "")
    res.motivo = motivo_ia if res.recomendada == recomendada_bruta else "Primeiro da lista que passou em todas as regras."
    res.controle = linha_controle(ctx.anteriores, ctx)
    return res


# ---------------------------------------------------------------- descricao
PROIBIDO_DESCRICAO = ["dia a dia", "rotina", "trabalho", "escritório", "expediente", "golada",
                      "últimas peças", "corra", "vai esgotar", "esgot", "ortopédic", "postura", "alivia dores",
                      "impermeável", "foto", "etiqueta", "pesquisa", "link", "peso"]
ORDEM_TOPICOS = ["Marca", "Referência", "Tipo", "Cabedal", "Palmilha / Base", "Solado", "Salto / Altura",
                 "Ajuste / Fechamento", "Detalhes", "Tecnologia", "Peso"]


@dataclass
class Descricao:
    frase_efeito: str = ""
    paragrafo: str = ""
    topicos: dict[str, str] = field(default_factory=dict)
    paragrafo_final: str = ""
    palavras_chave: list[str] = field(default_factory=list)

    def texto(self) -> str:
        linhas = [f"**{self.frase_efeito.strip()}**", "", self.paragrafo.strip(), ""]
        for k in ORDEM_TOPICOS:
            if self.topicos.get(k, "").strip():
                linhas.append(f"- **{k}:** {self.topicos[k].strip()}")
        linhas += ["", self.paragrafo_final.strip(), "", "**Palavras-chave:** " + ", ".join(self.palavras_chave)]
        return "\n".join(linhas)


def validar_descricao(d: Descricao, p: Produto, nome_final: str, regras: Regras, usadas: list[str]) -> list[str]:
    erros = []
    corpo = normalizar(d.texto())
    for pal in PROIBIDO_DESCRICAO:
        if contem_frase(corpo, pal) or (pal == "esgot" and "ESGOT" in corpo):
            erros.append(f"contém \"{pal}\"")
    for c in regras.cores:
        if contem_frase(normalizar(d.frase_efeito + " " + d.paragrafo + " " + d.paragrafo_final), c):
            erros.append(f"cita a cor \"{c}\" (a descrição não cita cor)")
            break
    final = normalizar(d.paragrafo_final)
    if not d.paragrafo_final.strip():
        erros.append("falta o parágrafo final")
    else:
        if normalizar(p.marca) not in final or normalizar(p.referencia).replace(" ", "") not in final.replace(" ", ""):
            erros.append("o parágrafo final deve citar a marca e a referência")
        if nome_final and contem_frase(final, nome_final):
            erros.append("o parágrafo final não deve repetir o nome inteiro do produto")
    n = len(d.palavras_chave)
    if not 8 <= n <= 10:
        erros.append(f"palavras-chave: {n} (devem ser de 8 a 10)")
    if not d.frase_efeito.strip() or not d.paragrafo.strip():
        erros.append("faltam a frase de efeito ou o parágrafo")
    for u in usadas:
        un = normalizar(u)
        if un and (un in corpo or normalizar(d.paragrafo_final) == un):
            erros.append(f"repete frase já usada: \"{u}\"")
    return erros


def frases_usadas(banco: Banco) -> list[str]:
    fixas = json.loads((REGRAS / "descricoes_usadas.json").read_text(encoding="utf-8")).get("frases", [])
    return fixas + banco.descricoes_finais()


def gerar_descricao(ia, banco: Banco, p: Produto, nome_final: str, *, pesquisa="", etiqueta="",
                    regras: Regras | None = None, tentativas: int = 3) -> tuple[Descricao, list[str]]:
    """Devolve (descricao, erros_restantes). Erros vazios = passou em tudo."""
    regras = regras or Regras.carregar()
    usadas = frases_usadas(banco)
    correcoes = banco.listar_correcoes(p.id) if p.id else []
    rejeicoes: list[str] = []
    d, erros = Descricao(), ["não gerada"]
    for _ in range(tentativas):
        s, u = pedido_descricao(p, nome_final, pesquisa=pesquisa, etiqueta=etiqueta, correcoes=correcoes,
                                usadas=usadas, rejeicoes=rejeicoes)
        dados = extrair_json(ia.chat(s, u).texto)
        d = Descricao(str(dados.get("frase_efeito", "")), str(dados.get("paragrafo", "")),
                      {str(k): str(v) for k, v in (dados.get("topicos") or {}).items() if str(v).strip()},
                      str(dados.get("paragrafo_final", "")), [str(x) for x in dados.get("palavras_chave", [])])
        erros = validar_descricao(d, p, nome_final, regras, usadas)
        if not erros:
            break
        rejeicoes = erros
    if p.id:
        banco.salvar_descricao(p.id, d.texto(), d.frase_efeito, d.paragrafo_final)
    return d, erros


def refazer_final(ia, banco: Banco, p: Produto, nome_final: str, atual: Descricao, *, regras: Regras | None = None,
                  tentativas: int = 3) -> tuple[Descricao, list[str]]:
    regras = regras or Regras.carregar()
    usadas = frases_usadas(banco) + [atual.paragrafo_final]
    rejeicoes: list[str] = []
    novo, erros = atual, ["não gerado"]
    for _ in range(tentativas):
        s, u = pedido_descricao(p, nome_final, usadas=usadas, so_final=True, rejeicoes=rejeicoes,
                                correcoes=banco.listar_correcoes(p.id) if p.id else [])
        final = str(extrair_json(ia.chat(s, u).texto).get("paragrafo_final", ""))
        novo = Descricao(atual.frase_efeito, atual.paragrafo, atual.topicos, final, atual.palavras_chave)
        erros = validar_descricao(novo, p, nome_final, regras, usadas)
        if not erros:
            break
        rejeicoes = erros
    return novo, erros


def ler_etiqueta(ia, fotos: list) -> dict:
    s, u = pedido_etiqueta()
    return extrair_json(ia.chat(s, u, imagens=fotos).texto)
