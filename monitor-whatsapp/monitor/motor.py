"""Regras do monitor: o que fazer com cada mensagem dos Grupos A e B."""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable

from .armazenamento import pasta_do_dia, salvar_fotos
from .config import Config, Grupo
from .legenda import dividir_legenda
from .lista import Estado, ListaDoDia
from .marcas import carregar_marcas, detectar_marca
from .referencia import chave_referencia, extrair_referencia, nome_seguro

CONFERIR = "_Conferir"


@dataclass
class Pendente:
    fotos: list[bytes]
    t0: float
    msg_id: str
    remetente: str
    grupo: str


def ler_etiqueta(ler, dados: bytes, marcas) -> tuple[str | None, str | None]:
    """OCR da foto da caixa -> (marca, referencia). Para assim que acha as duas; senao tenta as variacoes."""
    from .ocr import ler_bytes
    textos: list[str] = []
    for t in ler_bytes(ler, dados):
        textos.append(t)
        junto = "\n".join(textos)
        marca, ref = detectar_marca(junto, marcas), extrair_referencia(junto)
        if marca and ref:
            return marca.upper(), ref
    junto = "\n".join(textos)
    marca = detectar_marca(junto, marcas)
    return (marca.upper() if marca else None), extrair_referencia(junto)


class Processador:
    def __init__(self, cfg: Config, nav, *, ocr=None, evento: Callable[[str, object], None] = lambda t, d: None,
                 agora=time.time, hoje=date.today, pasta_marcas: Path | None = None) -> None:
        self.cfg, self.nav, self.evento, self.agora, self.hoje = cfg, nav, evento, agora, hoje
        self._ocr, self.ocr_pronto = ocr, ocr is not None
        self.marcas = carregar_marcas(pasta_marcas)
        self.pendentes: dict[tuple[str, str], Pendente] = {}   # (grupo, remetente) -> fotos esperando legenda
        self.aguardando: dict[str, int] = {}                   # msg_id -> ciclos esperando fotos carregarem
        self._dias: dict[str, date] = {}                       # grupo -> dia das pastas abertas
        self.listas: dict[str, ListaDoDia] = {}                # uma lista (e pasta) por grupo
        self.estados: dict[str, Estado] = {}
        self.pastas: dict[str, Path] = {}
        self._primeiro: set[str] = set()                       # grupos ja varridos uma vez

    # ---- infra -------------------------------------------------------------
    def _preparar_dia(self, grupo: str) -> None:
        d = self.hoje()
        if self._dias.get(grupo) != d:
            self._dias[grupo] = d
            self.pastas[grupo] = pasta_do_dia(Path(self.cfg.pasta_base), grupo, d)
            self.listas[grupo], self.estados[grupo] = ListaDoDia(self.pastas[grupo]), Estado(self.pastas[grupo])
            self.evento("lista", None)

    def _motor_ocr(self):
        if not self.ocr_pronto:
            from .ocr import criar_motor
            self.evento("status", "Carregando o leitor de etiquetas (a primeira vez demora)...")
            self._ocr, self.ocr_pronto = criar_motor(), True
        return self._ocr

    def _registrar(self, grupo: str, marca: str, ref: str, pasta_nome: str, fotos: list[bytes], situacao: str, obs: str = "") -> None:
        lista = self.listas[grupo]
        pasta, novas = salvar_fotos(self.pastas[grupo], pasta_nome, fotos)
        if novas == 0 and chave_referencia(pasta_nome) in {chave_referencia(i.pasta) for i in lista.itens.values()}:
            return                                     # tudo repetido: nao mexe na lista
        item = lista.registrar(chave=chave_referencia(pasta_nome) or pasta_nome, grupo=grupo, marca=marca, referencia=ref,
                                    novas_fotos=novas, situacao=situacao, pasta=pasta.name, observacao=obs)
        self.evento("lista", item)
        self.evento("log", f"{grupo}: {pasta.name} (+{novas} foto(s))" + (f" — {obs}" if obs else ""))

    # ---- ciclo -------------------------------------------------------------
    def ciclo(self) -> None:
        for g in self.cfg.grupos:
            self._preparar_dia(g.nome)
            self.listas[g.nome].recarregar()
            if not self.nav.abrir_conversa(g.nome):
                self.evento("log", f"Não consegui abrir o grupo \"{g.nome}\" (nome diferente? está na lista de conversas?)")
                continue
            self._processar_grupo(g)
        self._vencer_pendentes()

    def _processar_grupo(self, g: Grupo) -> None:
        _, msgs = self.nav.ler()
        primeira_vez = g.nome not in self._primeiro
        self._primeiro.add(g.nome)
        for i, m in enumerate(msgs):
            estado = self.estados[g.nome]
            if m.minha or not estado.novo(m.id):
                continue
            if m.dia != self.hoje():
                estado.marcar(m.id)               # antiga ou sem data: ignora para sempre
                continue
            if primeira_vez and not self.cfg.incluir_hoje:
                estado.marcar(m.id)
                continue
            if m.blobs or m.carregando:
                if m.carregando and self.aguardando.get(m.id, 0) < 10:   # miniatura ainda borrada: espera baixar
                    self.aguardando[m.id] = self.aguardando.get(m.id, 0) + 1
                    continue
                try:
                    fotos = self._fotos_da_mensagem(m)
                except Exception as e:  # noqa: BLE001
                    self.evento("log", f"Erro ao baixar fotos de {g.nome}: {e}")
                    continue
                if g.tipo == "B":
                    self._grupo_b(g, m, fotos)
                else:
                    self._grupo_a(g, m, fotos)
            elif g.tipo == "A" and m.legenda:
                self._texto_avulso(g, m)
            estado.marcar(m.id)

    def _fotos_da_mensagem(self, m) -> list[bytes]:
        fotos = self.nav.baixar(m.blobs)
        if m.mais and self.cfg.tentar_escondidas:
            esperado = len(m.blobs) + m.mais - 1
            completo = self.nav.baixar_album_completo(m, esperado)
            if len(completo) >= len(fotos):
                m.observacao_album = "" if len(completo) >= esperado else f"álbum incompleto: esperadas {esperado}, baixadas {len(completo)}"
                return completo
            m.observacao_album = f"álbum incompleto: esperadas {esperado}, baixadas {len(fotos)} (faltam {esperado - len(fotos)})"
        elif m.mais:
            m.observacao_album = f"álbum com +{m.mais} foto(s) escondida(s): baixe o restante na mão"
        return fotos

    # ---- Grupo A -----------------------------------------------------------
    def _grupo_a(self, g: Grupo, m, fotos: list[bytes]) -> None:
        obs = m.observacao_album
        if not m.legenda.strip():
            self.pendentes[(g.nome, m.remetente)] = Pendente(fotos, self.agora(), m.id, m.remetente, g.nome)
            self.evento("log", f"{g.nome}: {len(fotos)} foto(s) de {m.remetente or 'alguém'} sem legenda; esperando o texto...")
            return
        self._salvar_com_legenda(g.nome, m.legenda, fotos, obs)

    def _texto_avulso(self, g: Grupo, m) -> None:
        p = self.pendentes.pop((g.nome, m.remetente), None)
        if p:
            self._salvar_com_legenda(g.nome, m.legenda, p.fotos, "legenda veio depois das fotos")

    def _salvar_com_legenda(self, grupo: str, legenda: str, fotos: list[bytes], obs: str) -> None:
        d = dividir_legenda(legenda, self.marcas)
        if d.completa:
            self._registrar(grupo, d.marca, d.referencia, d.nome_pasta, fotos, "ok", obs)
        else:
            nome = f"{CONFERIR} {nome_seguro(legenda)[:60]}"
            self._registrar(grupo, d.marca or "?", d.referencia or legenda, nome, fotos, "conferir",
                            (obs + " marca não reconhecida: confira").strip())

    def _vencer_pendentes(self) -> None:
        agora = self.agora()
        for chave, p in list(self.pendentes.items()):
            if agora - p.t0 >= self.cfg.espera_legenda_seg:
                del self.pendentes[chave]
                self._registrar(p.grupo, "?", "sem legenda", f"{CONFERIR} sem legenda {p.remetente or ''} {p.msg_id[-6:]}".strip(),
                                p.fotos, "conferir", "fotos sem marca e referência")

    # ---- Grupo B -----------------------------------------------------------
    def _grupo_b(self, g: Grupo, m, fotos: list[bytes]) -> None:
        achados: dict[str, tuple[str, str, list[bytes]]] = {}   # chave -> (marca, ref, fotos)
        sem_leitura: list[bytes] = []
        try:
            ler = self._motor_ocr()
        except Exception as e:  # noqa: BLE001
            self.evento("log", f"Leitor de etiquetas indisponível: {e}")
            ler = None
        for f in fotos:
            marca = ref = None
            if ler is not None and len(f) >= 3000:
                try:
                    marca, ref = ler_etiqueta(ler, f, self.marcas)
                except Exception as e:  # noqa: BLE001
                    self.evento("log", f"Não consegui ler uma foto: {e}")
            if ref:
                chave = chave_referencia(ref)
                achados.setdefault(chave, (marca or "", ref, []))[2].append(f)
            else:
                sem_leitura.append(f)
        for marca, ref, lote in achados.values():
            nome = f"{marca} {ref}".strip()
            obs = "" if marca else "marca não identificada na foto"
            self._registrar(g.nome, marca or "?", ref, nome, lote, "ok", obs)
        if sem_leitura:
            self._registrar(g.nome, "?", "não lida", f"{CONFERIR} etiqueta {m.hora.replace(':', 'h')} {m.id[-6:]}", sem_leitura,
                            "conferir", "não consegui ler a referência na foto")
