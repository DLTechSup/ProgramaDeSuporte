"""Validador: regras do arquivo v5 checadas por codigo (seção 7 do plano)."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from rapidfuzz import fuzz

from .caminhos import CONFIG, REGRAS
from .texto import contem_frase, normalizar

CONECTORES = {"E", "COM", "QUE", "PARA", "DA", "DE", "DO", "NA", "NO", "EM", "AO", "POR", "SEM", "PELO", "PELA"}
VERBOS = {"AMORTECE", "TRAZ", "LEVA", "ALIVIA", "ESTABILIZA", "FACILITA", "VAI", "DEVOLVE", "VALORIZA",
          "DESCOMPLICA", "ILUMINA", "ABRACA", "SURPREENDE", "CONQUISTA", "COMPLETA", "TRANSFORMA", "ABSORVE",
          "HARMONIZA", "REFLETE", "ENCANTA", "ENVOLVE", "MUDA", "ACOMPANHA", "GARANTE", "OFERECE", "UNE", "ALIA"}
# Palavras-chave de beneficio, para a regra de diversidade dentro do lote.
BENEFICIOS = ["CONFORTO", "PRATICIDADE", "VERSATILIDADE", "ESTABILIDADE", "LEVEZA", "MACIEZ", "AMORTEC",
              "ALTURA", "ADERENCIA", "AJUSTE", "ELEGANCIA", "FIRMEZA", "SEGURANCA", "ENERGIA"]
MASC_PROIBIDAS = ["CHARME", "ENCANT", "DELICAD", "ACONCHEG"]


def _ler(caminho, chave):
    return json.loads(caminho.read_text(encoding="utf-8")).get(chave, [])


@dataclass
class Regras:
    limite: int = 85
    similaridade: int = 85
    proibidas: list[str] = field(default_factory=list)
    moderacao: list[str] = field(default_factory=list)
    cores: list[str] = field(default_factory=list)
    sob_demanda: list[str] = field(default_factory=list)

    @classmethod
    def carregar(cls) -> "Regras":
        cfg = json.loads((CONFIG / "configuracoes.json").read_text(encoding="utf-8"))
        livres = _ler(REGRAS / "sob_demanda.json", "palavras") if (REGRAS / "sob_demanda.json").is_file() else []
        livres_n = {normalizar(x) for x in livres}
        tirar = lambda lista: [x for x in lista if normalizar(x) not in livres_n]
        return cls(cfg["limite_caracteres"], cfg["similaridade_minima_repeticao"],
                   tirar(_ler(REGRAS / "proibidas.json", "palavras")), tirar(_ler(REGRAS / "moderacao.json", "palavras")),
                   _ler(REGRAS / "cores.json", "palavras"), list(livres))


def palavras_evitar(*textos: str) -> list[str]:
    """Junta palavras de 'Evitar nesta rodada' / correcoes 'EVITAR: a, b' numa lista."""
    out: list[str] = []
    for t in textos:
        t = t.split(":", 1)[1] if t.upper().startswith("EVITAR:") else t
        for w in re.split(r"[,;]", t):
            w = w.strip()
            if w and w.lower() not in out:
                out.append(w.lower())
    return out


@dataclass
class Contexto:
    marca: str = ""
    referencia: str = ""
    categoria: str = ""
    genero: str = ""          # "Feminino", "Masculino", "Unissex"
    publico: str = ""         # "adulto", "infantil", "bebe", "teen"
    aprovados: list[str] = field(default_factory=list)       # nomes aprovados de todos os produtos
    anteriores: list[str] = field(default_factory=list)      # sugestoes ja dadas para ESTE produto
    lote: list[str] = field(default_factory=list)            # nomes ja aceitos neste mesmo lote
    evitar: list[str] = field(default_factory=list)          # palavras que o usuario pediu para nao usar


@dataclass
class Item:
    regra: str
    ok: bool
    mensagem: str
    ajuste: str = ""


@dataclass
class Resultado:
    nome: str
    itens: list[Item]

    @property
    def aprovado(self) -> bool:
        return all(i.ok for i in self.itens)

    @property
    def motivos(self) -> list[str]:
        return [f"{i.regra}: {i.mensagem}" for i in self.itens if not i.ok]


def miolo(nome: str, ctx: Contexto) -> str:
    """Trecho entre a marca e a referencia."""
    n, marca, ref = normalizar(nome), normalizar(ctx.marca), normalizar(ctx.referencia)
    if marca and f" {marca} " in f" {n} ":
        n = f" {n} ".split(f" {marca} ", 1)[1].strip()
    if ref and n.endswith(ref):
        n = n[: -len(ref)].strip()
    return n


def palavras_apos_marca(nome: str, ctx: Contexto) -> list[str]:
    return miolo(nome, ctx).split()


def _beneficio_principal(m: str) -> str | None:
    for b in BENEFICIOS:
        if b in m:
            return b
    return None


def validar(nome: str, ctx: Contexto, regras: Regras | None = None) -> Resultado:
    r = regras or Regras.carregar()
    nome = nome.strip()
    n = normalizar(nome)
    m = miolo(nome, ctx)
    itens: list[Item] = []

    def add(regra, ok, msg_ok, msg_erro, ajuste=""):
        itens.append(Item(regra, ok, msg_ok if ok else msg_erro, "" if ok else ajuste))

    # 1. tamanho
    tam = len(nome)
    add("85 caracteres", tam <= r.limite, f"{tam} caracteres", f"{tam} caracteres (máximo {r.limite})",
        f"Corte {tam - r.limite} caractere(s): encurte o complemento do meio.")

    # 2. categoria e marca
    cat, marca, ref = normalizar(ctx.categoria), normalizar(ctx.marca), normalizar(ctx.referencia)
    add("Começa pela categoria", bool(cat) and n.startswith(cat), "ok",
        f"O nome deve começar por \"{ctx.categoria.upper()}\"." if cat else "Categoria não informada.",
        "Comece o nome pela categoria.")
    add("Contém a marca", bool(marca) and f" {marca} " in f" {n} ", "ok",
        "A marca não aparece no nome." if marca else "Marca não informada.", "Coloque a marca logo depois da categoria.")

    # 3. referencia no final
    compacto, ref_c = n.replace(" ", ""), ref.replace(" ", "")
    add("Termina com a referência", bool(ref_c) and compacto.endswith(ref_c), "ok",
        "O nome não termina com a referência." if ref_c else "Referência não informada.",
        f"Termine o nome com {ctx.referencia}.")

    # 4. proibidas
    achadas = [p for p in r.proibidas if contem_frase(n, p)]
    add("Sem palavras proibidas", not achadas, "ok", "Contém: " + ", ".join(achadas),
        "Troque ou retire: " + ", ".join(achadas))

    # 4b. palavras que o usuario pediu para evitar (inclui as "so se eu pedir")
    pedidas = [w for w in ctx.evitar if contem_frase(n, w)]
    add("Palavras que você pediu para evitar", not pedidas, "ok", "Contém: " + ", ".join(pedidas),
        "Troque ou retire: " + ", ".join(pedidas))

    # 5. cor
    cores = [c for c in r.cores if contem_frase(n, c)]
    add("Sem cor no nome", not cores, "ok", "Contém cor: " + ", ".join(cores), "Retire a cor; o nome serve para todas as cores.")

    # 6. repeticao
    exato = next((a for a in ctx.aprovados + ctx.anteriores if normalizar(a) == n), None)
    parecido = None
    for outro in ctx.aprovados + ctx.anteriores:
        if outro and fuzz.token_sort_ratio(n, normalizar(outro)) >= r.similaridade:
            parecido = outro
            break
    mesmo_miolo = None
    if len(m) >= 15:
        for outro in ctx.aprovados:
            if fuzz.partial_ratio(m, normalizar(outro)) >= 92:
                mesmo_miolo = outro
                break
    if exato:
        add("Não repetido", False, "", "Igual a um nome já usado.", "Crie um nome com ângulo, verbo e benefício novos.")
    elif parecido:
        add("Não repetido", False, "", f"Parecido demais com: {parecido}", "Mude o verbo, o benefício e a abertura (não basta trocar palavras de lugar ou um sinônimo).")
    elif mesmo_miolo:
        add("Não repetido", False, "", f"Mesmo miolo de: {mesmo_miolo}", "Crie uma frase nova entre a marca e a referência.")
    else:
        add("Não repetido", True, "ok", "")

    # 7. diversidade no lote
    inicio = palavras_apos_marca(nome, ctx)[:1]
    ben = _beneficio_principal(m)
    conflito = None
    for outro in ctx.lote:
        mo = miolo(outro, ctx)
        if inicio and mo.split()[:1] == inicio:
            conflito = f"começa com a mesma palavra de \"{outro}\""
            break
        if ben and _beneficio_principal(mo) == ben:
            conflito = f"mesmo benefício principal ({ben.lower()}) de \"{outro}\""
            break
    add("Diversidade no lote", conflito is None, "ok", f"Nome do lote {conflito}.", "Troque o ângulo (veja a tabela 2.4 do arquivo v5).")

    # 8. moderacao
    mod_usadas = [p for p in r.moderacao if contem_frase(n, p) and any(contem_frase(normalizar(o), p) for o in ctx.lote)]
    add("Palavras de moderação", not mod_usadas, "ok", "Já usada(s) em outro nome do lote: " + ", ".join(mod_usadas),
        "Use cada palavra de moderação em no máximo 1 nome por lista.")

    # 9. ligacao verbal
    palavras = set(m.split())
    liga = bool(palavras & (CONECTORES | VERBOS))
    add("Ligação verbal", liga, "ok", "O miolo parece uma lista de palavras soltas.",
        "Ligue as ideias com verbo e conectores (ex.: \"AMORTECE O IMPACTO E DEVOLVE ENERGIA\").")

    # 10. masculino
    if ctx.genero.lower().startswith("masc"):
        ruins = [p for p in MASC_PROIBIDAS if p in n]
        add("Tom masculino", not ruins, "ok", "Evite em nome masculino: " + ", ".join(ruins).lower(),
            "Prefira praticidade, versatilidade, estilo casual e resultado.")
        add("Indica gênero masculino", "MASCULIN" in n, "ok", "Escreva MASCULINO/MASCULINA logo depois da categoria.",
            "Ex.: SANDÁLIA MASCULINA BR SPORT ...")
    if ctx.publico == "bebe":
        add("Bebê sem \"masculino\"", "MASCULIN" not in n, "ok", "Não use MASCULINO junto de BEBÊ.", "Retire a palavra MASCULINO.")

    return Resultado(nome, itens)
