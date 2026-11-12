"""Modo offline: gera nomes e descricao SEM IA, com um banco de pecas + modelos de frase + validador."""
from __future__ import annotations

import json
import random
import re

from .banco import Banco
from .caminhos import CONFIG
from .criador import Descricao, filtrar_candidatos, ler_config, validar_descricao, frases_usadas
from .produto import Produto
from .texto import normalizar
from .validador import Contexto, Regras

TIPOS = ["acao", "beneficio_onde", "complemento", "resultado"]
CARACTERISTICAS = {  # etiqueta -> rotulo da caixa de selecao
    "tira_traseira": "Tira traseira", "slide": "Slide", "2_em_1": "2 em 1", "salto_bloco": "Salto bloco",
    "salto_fino": "Salto fino", "anabela": "Anabela", "plataforma": "Plataforma", "rasteira": "Rasteira",
    "strass": "Strass ou pedraria", "laco": "Laço", "metais": "Metais", "camurca": "Camurça", "napa": "Napa",
    "perfurados": "Perfurados", "palmilha_acolchoada": "Base acolchoada", "base_anatomica": "Base anatômica",
    "solado_frisos": "Solado com frisos", "amortecimento": "Tecnologia de amortecimento",
    "cadarco": "Cadarço", "velcro": "Velcro"}


def semear_pecas(banco: Banco) -> int:
    """Carrega config/pecas_base.json na primeira execução e aprende pecas dos nomes ja aprovados."""
    if banco.total_pecas() > 0:
        return 0
    base = json.loads((CONFIG / "pecas_base.json").read_text(encoding="utf-8"))
    n = 0
    for tipo in TIPOS:
        for item in base.get(tipo, []):
            n += banco.adicionar_peca(item["t"], tipo, item["e"], "base")
    return n


def aprender_de_nome(banco: Banco, nome: str, p: Produto) -> int:
    """Quebra o miolo de um nome aprovado em partes ('X E Y') e guarda como pecas (etiquetas = caracteristicas marcadas)."""
    from .validador import miolo
    ctx = Contexto(p.marca, p.referencia, p.categoria_completa)
    m = miolo(nome, ctx)
    if not m or " E " not in f" {m} ":
        return 0
    partes = [x.strip() for x in re.split(r"\s+E\s+", m) if len(x.strip()) >= 8]
    tags = list(p.caracteristicas)
    return sum(banco.adicionar_peca(x, "acao", tags, "aprendida") for x in partes)


def _permitida(etiquetas: list[str], p: Produto) -> bool:
    marcadas = set(p.caracteristicas)
    extras = {p.genero.lower()} | {p.publico.lower()}
    for e in etiquetas:
        if e.startswith("-"):
            if e[1:] in extras or (e[1:] == "masculino" and p.masculino):
                return False
        elif e not in marcadas and e not in extras:
            return False
    return True


def gerar_nomes_offline(banco: Banco, p: Produto, *, regras: Regras | None = None, evitar: str = "",
                        tentativas: int = 1500, semente: int | None = None) -> list[str]:
    semear_pecas(banco)
    regras, cfg = regras or Regras.carregar(), ler_config()
    rnd = random.Random(semente)
    evitar_n = [normalizar(x) for x in re.split(r"[,;]", evitar) if x.strip()]
    por_tipo: dict[str, list[str]] = {t: [] for t in TIPOS}
    for peca in banco.listar_pecas():
        if peca["tipo"] in por_tipo and _permitida(peca["etiquetas"], p) and not any(e in normalizar(peca["texto"]) for e in evitar_n):
            por_tipo[peca["tipo"]].append(peca["texto"])
    ctx = Contexto(p.marca, p.referencia, p.categoria_completa, p.genero, p.publico,
                   aprovados=banco.listar_nomes(limite=10**9), anteriores=banco.sugestoes_do_produto(p.id) if p.id else [])
    ac, bo, co, re_ = (por_tipo[t] for t in ("acao", "beneficio_onde", "complemento", "resultado"))
    estruturas = []
    if len(ac) >= 2: estruturas += [lambda: " E ".join(rnd.sample(ac, 2)),
                                    lambda: " E ".join(rnd.sample(ac, 2)) + " " + rnd.choice(co) if co else None]
    if ac and co: estruturas.append(lambda: f"{rnd.choice(ac)} {rnd.choice(co)}")
    if len(bo) >= 2: estruturas.append(lambda: " E ".join(rnd.sample(bo, 2)))
    if re_: estruturas.append(lambda: rnd.choice(re_))
    if not estruturas:
        return []
    prefixo = f"{p.categoria_completa} {p.marca.upper()}".strip()
    alvo, aceitos = cfg["sugestoes_exibidas"], []
    for _ in range(4):                       # ate 4 rodadas, parando quando a lista enche
        candidatos = []
        for _ in range(tentativas):
            meio = rnd.choice(estruturas)()
            if meio:
                candidatos.append(f"{prefixo} {meio} {p.referencia}".upper())
        novos, _rej = filtrar_candidatos(candidatos, ctx, regras, maximo=alvo - len(aceitos))
        aceitos += novos
        if len(aceitos) >= alvo:
            break
    if p.id:
        lote = banco.proximo_lote(p.id)
        for n in aceitos:
            banco.salvar_sugestao(p.id, n, "offline", lote, True)
    return aceitos


# ------------------------------------------------------------- descricao
ROTULO_USO = ["passeios", "viagens", "dias de praia", "encontros", "fins de semana", "momentos de lazer"]
ABERTURAS = [
    "Leve o {m} {r} para os seus próximos programas e descubra como é fácil combinar estilo e praticidade.",
    "Que tal um par que acompanha vários momentos com leveza? O {m} {r} foi feito para isso.",
    "Quer facilidade na hora de escolher o que usar? O {m} {r} resolve com muito estilo.",
    "Do passeio ao lazer, o {m} {r} entrega visual e conforto em um só par.",
    "Experimente o {m} {r} e transforme os seus programas em momentos mais confortáveis.",
]
FRASES_EFEITO = {
    "slide": "Praticidade que vai da praia à cidade.", "strass": "Brilho que valoriza cada produção.",
    "salto_bloco": "Altura estável e visual elegante.", "anabela": "Altura leve para brilhar com conforto.",
    "amortecimento": "Amortecimento que acompanha o seu ritmo de treino.", "rasteira": "Leveza e estilo para o seu momento.",
    "default": "Estilo e conforto em um par só."}
TOPICOS = {"tira_traseira": ("Ajuste / Fechamento", "tira traseira"), "velcro": ("Ajuste / Fechamento", "velcro"),
           "cadarco": ("Ajuste / Fechamento", "cadarço"), "salto_bloco": ("Salto / Altura", "salto bloco"),
           "salto_fino": ("Salto / Altura", "salto fino"), "anabela": ("Salto / Altura", "anabela"),
           "plataforma": ("Salto / Altura", "plataforma"), "solado_frisos": ("Solado", "solado com frisos"),
           "palmilha_acolchoada": ("Palmilha / Base", "base acolchoada"), "base_anatomica": ("Palmilha / Base", "base anatômica"),
           "camurca": ("Cabedal", "camurça"), "napa": ("Cabedal", "napa"), "perfurados": ("Detalhes", "perfurados"),
           "strass": ("Detalhes", "strass ou pedraria"), "laco": ("Detalhes", "laço"), "metais": ("Detalhes", "metais"),
           "amortecimento": ("Tecnologia", "amortecimento")}


def gerar_descricao_offline(banco: Banco, p: Produto, nome_final: str, *, regras: Regras | None = None,
                            semente: int | None = None) -> tuple[Descricao, list[str]]:
    regras, rnd = regras or Regras.carregar(), random.Random(semente)
    marcadas = [c for c in p.caracteristicas if c in CARACTERISTICAS]
    frase = next((FRASES_EFEITO[c] for c in marcadas if c in FRASES_EFEITO), FRASES_EFEITO["default"])
    detalhes = [CARACTERISTICAS[c].lower() for c in marcadas]
    cat = p.categoria_completa.capitalize()
    paragrafo = (f"{cat} {p.marca} {p.referencia}: um modelo pensado para {', '.join(rnd.sample(ROTULO_USO, 4))} e outras ocasiões. "
                 + (f"O design reúne {', '.join(detalhes)}, " if detalhes else "O design traz acabamento cuidadoso, ")
                 + "para um visual atual e um uso confortável em vários momentos.")
    topicos = {"Marca": p.marca, "Referência": p.referencia, "Tipo": p.categoria_completa.capitalize()}
    for c in marcadas:
        if c in TOPICOS:
            k, v = TOPICOS[c]
            topicos[k] = (topicos[k] + ", " + v) if k in topicos else v
    usadas = frases_usadas(banco)
    final = ""
    for ab in rnd.sample(ABERTURAS, len(ABERTURAS)):
        cand = ab.format(m=p.marca, r=p.referencia)
        if normalizar(cand) not in [normalizar(u) for u in usadas]:
            final = cand
            break
    base = p.categoria_completa.lower()
    chaves = [f"{base} {p.marca.lower()}", base, f"{base} {p.referencia}", f"{p.marca.lower()} {p.referencia}",
              f"{base} confortável", f"{base} casual", f"{base} para passeio", f"{p.marca.lower()}"]
    for d in detalhes[:2]:
        chaves.append(f"{base} {d}")
    chaves = list(dict.fromkeys(chaves))[:10]
    while len(chaves) < 8:
        chaves.append(f"{base} {len(chaves)}")
    d = Descricao(frase, paragrafo, topicos, final, chaves)
    return d, validar_descricao(d, p, nome_final, regras, usadas)
