"""'Analisar o dia': propoe mudancas nas regras. NADA muda sem aprovacao; antes de aplicar, guarda backup."""
from __future__ import annotations

import json
import re
import shutil
from collections import Counter
from dataclasses import dataclass
from datetime import datetime

from .banco import Banco
from .caminhos import REGRAS
from .prompts import pedido_analise
from .provedores import extrair_json
from .texto import normalizar

TIPOS = {"adicionar_proibida": "proibidas.json", "adicionar_moderacao": "moderacao.json", "nova_estrutura": "estruturas_extra.json"}
CHAVE = {"proibidas.json": "palavras", "moderacao.json": "palavras", "estruturas_extra.json": "estruturas"}
PARADAS = set("PARA COM QUE UMA UNS SUAS SEUS ESTE ESTA MAIS MUITO TODO TODA TODOS SANDALIA TENIS TAMANCO RASTEIRA CHINELO SAPATILHA SCARPIN".split())


@dataclass
class Proposta:
    tipo: str
    valor: str
    motivo: str = ""

    def descricao(self) -> str:
        rot = {"adicionar_proibida": "Adicionar às PROIBIDAS", "adicionar_moderacao": "Mover para MODERAÇÃO",
               "nova_estrutura": "Nova ESTRUTURA de frase"}[self.tipo]
        return f"{rot}: \"{self.valor}\" — {self.motivo}"


def palavras_evitadas(correcoes: list[str]) -> Counter:
    c: Counter = Counter()
    for t in correcoes:
        if t.upper().startswith("EVITAR:"):
            for w in re.split(r"[,;]", t.split(":", 1)[1]):
                if w.strip():
                    c[w.strip().lower()] += 1
    return c


def propostas_por_codigo(dados: dict) -> list[Proposta]:
    """Analise simples, sem IA: palavras digitadas em 'Evitar' -> proibidas; palavras muito repetidas -> moderacao."""
    out = [Proposta("adicionar_proibida", w, f"você pediu para evitar {n}x hoje") for w, n in palavras_evitadas(dados["correcoes"]).most_common(10)]
    freq: Counter = Counter()
    for nome in dados["aprovados"]:
        for w in set(normalizar(nome).split()):
            if len(w) >= 5 and w not in PARADAS and not any(ch.isdigit() for ch in w):
                freq[w] += 1
    for w, n in freq.most_common(10):
        if n >= 3:
            out.append(Proposta("adicionar_moderacao", w.lower(), f"apareceu em {n} nomes aprovados hoje"))
    return out


def propostas_por_ia(ia, dados: dict) -> list[Proposta]:
    s, u = pedido_analise(dados)
    out = []
    for item in extrair_json(ia.chat(s, u).texto).get("propostas", []):
        if isinstance(item, dict) and item.get("tipo") in TIPOS and str(item.get("valor", "")).strip():
            out.append(Proposta(item["tipo"], str(item["valor"]).strip(), str(item.get("motivo", ""))))
    return out


def analisar(banco: Banco, ia=None, dia: str | None = None) -> tuple[list[Proposta], str]:
    dados = banco.dados_do_dia(dia)
    if not (dados["aprovados"] or dados["correcoes"] or dados["rejeitadas"]):
        return [], "Nada aconteceu hoje ainda: nenhum nome aprovado, correção ou sugestão."
    if ia is not None:
        try:
            props = propostas_por_ia(ia, dados)
            if props:
                return props, "Propostas feitas pela IA."
        except Exception:  # noqa: BLE001  (sem IA disponivel -> analise simples)
            pass
    return propostas_por_codigo(dados), "Análise simples (sem IA)."


def aplicar(proposta: Proposta, banco: Banco, pasta_regras=REGRAS) -> str:
    """Aplica UMA proposta aceita. Devolve o caminho do backup."""
    arquivo = pasta_regras / TIPOS[proposta.tipo]
    chave = CHAVE[arquivo.name]
    atual = json.loads(arquivo.read_text(encoding="utf-8")) if arquivo.is_file() else {chave: []}
    backup = pasta_regras / "historico_regras" / datetime.now().strftime("%Y-%m-%d_%H%M%S")
    backup.mkdir(parents=True, exist_ok=True)
    if arquivo.is_file():
        shutil.copy2(arquivo, backup / arquivo.name)
    banco.registrar_versao_regras(proposta.descricao(), json.dumps(atual, ensure_ascii=False))
    lista = atual.setdefault(chave, [])
    if proposta.valor.lower() not in [x.lower() for x in lista]:
        lista.append(proposta.valor)
    arquivo.write_text(json.dumps(atual, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(backup)
