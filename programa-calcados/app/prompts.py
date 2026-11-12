"""Monta os pedidos para a IA a partir das regras do arquivo v5 (as regras vao em TODO pedido)."""
from __future__ import annotations

import json
import re

from rapidfuzz import fuzz

from .caminhos import REGRAS
from .produto import Produto
from .texto import normalizar
from .validador import BENEFICIOS, Contexto, miolo

ARQUIVO_REGRAS = REGRAS / "instrucoes_v5.md"


def carregar_partes(texto: str | None = None) -> dict[str, str]:
    """Quebra o arquivo v5 em partes: {'1': '...', '3A': '...', ...}."""
    if texto is None:
        texto = ARQUIVO_REGRAS.read_text(encoding="utf-8") if ARQUIVO_REGRAS.is_file() else ""
    achados = list(re.finditer(r"^## PARTE (\d+A?) ", texto, flags=re.MULTILINE))
    partes = {}
    for i, m in enumerate(achados):
        fim = achados[i + 1].start() if i + 1 < len(achados) else len(texto)
        partes[m.group(1)] = texto[m.start():fim].strip()
    return partes


def regras_para(etapa: str, partes: dict[str, str] | None = None) -> str:
    """Partes do v5 relevantes para cada etapa (a Parte 10, a lista de nomes, vai separada)."""
    partes = partes if partes is not None else carregar_partes()
    escolha = {"nomes": ["1", "2", "4", "5", "7"], "descricao": ["1", "4", "6", "7", "11"],
               "etiqueta": [], "analise": ["1", "5", "7"]}[etapa]
    return "\n\n".join(partes[n] for n in escolha if n in partes)


def exemplos_proximos(aprovados: list[str], produto: Produto, n: int = 10) -> list[str]:
    alvo = normalizar(f"{produto.categoria_completa} {produto.marca}")
    pontuados = sorted(aprovados, key=lambda a: fuzz.token_set_ratio(alvo, normalizar(a)), reverse=True)
    return pontuados[:n]


def linha_controle(anteriores: list[str], ctx: Contexto) -> str:
    """Verbos/beneficios/aberturas ja usados neste produto (Parte 2.5 do v5)."""
    usados: list[str] = []
    for nome in anteriores:
        m = miolo(nome, ctx)
        if not m:
            continue
        for w in [m.split()[0]] + [b for b in BENEFICIOS if b in m]:
            w = w.lower()
            if w not in usados:
                usados.append(w)
    return ", ".join(usados)


def _ficha(p: Produto, pesquisa: str, etiqueta: str) -> str:
    return (f"Categoria: {p.categoria_completa}\nMarca: {p.marca}\nReferência: {p.referencia}\n"
            f"Gênero: {p.genero or 'não informado'}\nPúblico: {p.publico or 'adulto'}\n"
            f"Etiqueta da caixa (lida da foto): {etiqueta or 'não disponível'}\n"
            f"Dados da pesquisa:\n{pesquisa or 'nenhum dado confirmado'}")


def pedido_nomes(p: Produto, ctx: Contexto, *, pesquisa="", etiqueta="", correcoes=(), evitar="",
                 quantidade=20, rejeicoes=(), manter_inicio="") -> tuple[str, str]:
    sistema = (
        "Você cria NOMES (títulos) de calçados para uma loja online brasileira. Siga rigorosamente o manual abaixo.\n"
        "Ignore as partes do manual que falam de conversa, formato de resposta em tópicos, contagem na tela ou "
        "'Instruções recebidas': quem conta caracteres e confere repetição é o programa. "
        "Responda SOMENTE com um objeto JSON válido, sem texto antes ou depois.\n\n"
        "=== MANUAL ===\n" + regras_para("nomes"))
    partes = [
        "FICHA DO PRODUTO\n" + _ficha(p, pesquisa, etiqueta),
        f"Crie {quantidade} nomes inéditos, em MAIÚSCULAS, no máximo 85 caracteres, começando por \"{p.categoria_completa}\", "
        f"com a marca \"{p.marca}\" e terminando com a referência \"{p.referencia}\". Use ângulos diferentes em cada nome, "
        "ligação verbal e benefício real. Sem cor no nome.",
    ]
    ex = exemplos_proximos(ctx.aprovados, p)
    if ex:
        partes.append("EXEMPLOS DE NÍVEL DE QUALIDADE (já aprovados; NÃO copie nem reaproveite frases):\n- " + "\n- ".join(ex))
    if ctx.anteriores:
        partes.append("JÁ SUGERIDOS PARA ESTE PRODUTO (proibido repetir, parecer ou trocar palavras de lugar):\n- " + "\n- ".join(ctx.anteriores)
                      + "\nJá usados neste produto (não volte a usar): " + linha_controle(ctx.anteriores, ctx))
    extra = REGRAS / "estruturas_extra.json"
    if extra.is_file():
        est = json.loads(extra.read_text(encoding="utf-8")).get("estruturas", [])
        if est:
            partes.append("ESTRUTURAS DE FRASE EXTRAS APROVADAS PELO USUÁRIO (pode usar):\n- " + "\n- ".join(est))
    if correcoes:
        partes.append("CORREÇÕES DO USUÁRIO (valem como regra):\n- " + "\n- ".join(correcoes))
    if evitar.strip():
        partes.append(f"EVITAR NESTA RODADA (e sinônimos diretos): {evitar.strip()}")
    if manter_inicio:
        partes.append(f"O usuário gostou do início \"{manter_inicio}\". Mantenha EXATAMENTE esse início em todos os nomes e crie finais novos e diferentes entre si.")
    if rejeicoes:
        partes.append("NA TENTATIVA ANTERIOR O PROGRAMA REJEITOU (evite esses erros):\n- " + "\n- ".join(list(rejeicoes)[:15]))
    partes.append('Formato da resposta: {"sugestoes": ["NOME 1", "NOME 2", ...], "recomendada": 0, "motivo": "uma ou duas frases"} '
                  '(recomendada = posição do melhor nome na lista, começando em 0).')
    return sistema, "\n\n".join(partes)


def pedido_descricao(p: Produto, nome_final: str, *, pesquisa="", etiqueta="", correcoes=(), usadas=(),
                     so_final=False, rejeicoes=()) -> tuple[str, str]:
    sistema = (
        "Você escreve DESCRIÇÕES de calçados para uma loja online brasileira. Siga rigorosamente o manual abaixo. "
        "Não invente dados. Responda SOMENTE com um objeto JSON válido.\n\n=== MANUAL ===\n" + regras_para("descricao"))
    partes = ["FICHA DO PRODUTO\n" + _ficha(p, pesquisa, etiqueta), f"Nome escolhido: {nome_final}"]
    if usadas:
        partes.append("FRASES E CHAMADAS FINAIS JÁ USADAS (não repetir nem imitar):\n- " + "\n- ".join(usadas))
    if correcoes:
        partes.append("CORREÇÕES DO USUÁRIO (valem como regra):\n- " + "\n- ".join(correcoes))
    if rejeicoes:
        partes.append("A TENTATIVA ANTERIOR FOI REJEITADA PELO PROGRAMA (corrija):\n- " + "\n- ".join(rejeicoes))
    if so_final:
        partes.append('Escreva APENAS um novo parágrafo final (chamativo, só marca + referência, sem escassez). '
                      'Formato: {"paragrafo_final": "..."}')
    else:
        partes.append(
            'Formato: {"frase_efeito": "...", "paragrafo": "design + conforto + vários usos", '
            '"topicos": {"Marca": "...", "Referência": "...", "Tipo": "...", "Cabedal": "...", "Palmilha / Base": "...", '
            '"Solado": "...", "Salto / Altura": "...", "Ajuste / Fechamento": "...", "Detalhes": "...", "Tecnologia": "..."}, '
            '"paragrafo_final": "...", "palavras_chave": ["8 a 10 termos"]}. '
            'Inclua em "topicos" só os campos com dado confirmado. Não cite cor, peso, foto, etiqueta, pesquisa nem links.')
    return sistema, "\n\n".join(partes)


def pedido_etiqueta() -> tuple[str, str]:
    return ("Você lê etiquetas de caixas de calçados em fotos. Responda SOMENTE com JSON válido. Não invente: o que não "
            "estiver legível deve ficar em branco.",
            'Leia a etiqueta da caixa nas fotos. Formato: {"marca": "", "referencia": "", "material": "", "cor": "", '
            '"codigo_cor": "", "observacoes": "características visíveis do calçado: tiras, salto, solado, detalhes"}')


def pedido_analise(dia: dict) -> tuple[str, str]:
    sistema = ("Você ajuda a melhorar as regras de um programa de nomes de calçados. Proponha mudanças pequenas e "
               "justificadas pelo que aconteceu hoje. Responda SOMENTE com JSON válido.\n\n=== REGRAS ATUAIS ===\n" + regras_para("analise"))
    usuario = ("O QUE ACONTECEU HOJE:\n" + json.dumps(dia, ensure_ascii=False, indent=1) +
               '\n\nFormato: {"propostas": [{"tipo": "adicionar_proibida" | "adicionar_moderacao" | "nova_estrutura", '
               '"valor": "palavra, expressão ou estrutura", "motivo": "por quê"}]}')
    return sistema, usuario
