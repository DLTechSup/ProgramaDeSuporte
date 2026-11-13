"""Regras do monitor: o que fazer com cada mensagem dos Grupos A e B."""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable

from .armazenamento import anexar_mensagens, nome_pasta_grupo, pasta_do_dia, salvar_fotos
from .config import Config, Grupo
from .legenda import dividir_legenda
from .lista import Estado, ListaDoDia
from .marcas import carregar_marcas, detectar_marca
from .referencia import chave_referencia, extrair_referencia, nome_seguro
from .regras_ref import RegrasReferencia

CONFERIR = "_Conferir"
APAGADA = {"ESTA MENSAGEM FOI APAGADA", "VOCE APAGOU ESTA MENSAGEM", "THIS MESSAGE WAS DELETED", "YOU DELETED THIS MESSAGE", "MENSAGEM APAGADA"}


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
                 agora=time.time, hoje=date.today, pasta_marcas: Path | None = None, regras_ref: RegrasReferencia | None = None) -> None:
        self.cfg, self.nav, self.evento, self.agora, self.hoje = cfg, nav, evento, agora, hoje
        self._ocr, self.ocr_pronto = ocr, ocr is not None
        self.marcas = carregar_marcas(pasta_marcas)
        self.regras_ref = regras_ref if regras_ref is not None else RegrasReferencia.carregar()
        self.pendentes: dict[tuple[str, str], Pendente] = {}   # (grupo, remetente) -> fotos esperando legenda
        self.aguardando: dict[str, int] = {}                   # msg_id -> ciclos esperando fotos carregarem
        self._dias: dict[str, date] = {}                       # grupo -> dia das pastas abertas
        self.listas: dict[str, ListaDoDia] = {}                # uma lista (e pasta) por grupo
        self.estados: dict[str, Estado] = {}
        self.pastas: dict[str, Path] = {}
        self._primeiro: set[str] = set()                       # grupos ja varridos uma vez
        self._aviso_falha: dict[str, float] = {}               # grupo -> quando avisamos pela ultima vez que nao abriu

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
        if novas > 0:
            self.evento("salvo", {"grupo": grupo, "pasta": pasta.name, "marca": marca, "referencia": ref, "novas": novas,
                                  "total": item.fotos, "nova": item.fotos == novas, "situacao": situacao, "obs": obs})

    # ---- ciclo -------------------------------------------------------------
    def ciclo(self) -> None:
        for g in self.cfg.grupos:
            self._preparar_dia(g.nome)
            self.listas[g.nome].recarregar()
            if not self.nav.abrir_conversa(g.nome):
                if self.agora() - self._aviso_falha.get(g.nome, -10**9) >= 180:       # avisa de 3 em 3 minutos, nao a cada rodada
                    self._aviso_falha[g.nome] = self.agora()
                    visto = self.nav.resumo_conversas() if hasattr(self.nav, "resumo_conversas") else ""
                    self.evento("log", f"Não consegui abrir o grupo \"{g.nome}\" (nome diferente? está na lista de conversas?)" + (f" — {visto}" if visto else "") + " Continuo tentando.")
                continue
            self._processar_grupo(g)
        self._vencer_pendentes()

    def _processar_grupo(self, g: Grupo) -> None:
        primeira = g.nome not in self._primeiro
        self._primeiro.add(g.nome)
        if primeira and self.cfg.pegar_antigas and hasattr(self.nav, "rolar_para_o_inicio_do_dia"):
            self._varredura(g)                      # tudo o que chegou hoje, mesmo o que o WhatsApp nao mostra de primeira
        else:
            self._passada(g, ignorar_existentes=primeira and not self.cfg.pegar_antigas)

    def _varredura(self, g: Grupo) -> None:
        """Sobe ate o inicio do dia e desce tela por tela (as fotos so carregam quando aparecem), processando tudo."""
        self.evento("log", f"{g.nome}: lendo tudo o que chegou hoje (pode levar um pouco)...")
        self.nav.rolar_para_o_inicio_do_dia(self.hoje())
        for _ in range(120):
            self._passada(g)
            if not self.nav.rolar_um_passo():
                break
        self._passada(g)
        self.nav.rolar_para_o_fim()

    def _passada(self, g: Grupo, ignorar_existentes: bool = False) -> None:
        if g.tipo == "I":
            return self._conversa_individual(g, ignorar_existentes)
        estado = self.estados[g.nome]
        if ignorar_existentes:                     # modo "so o que chegar de novo": tudo o que ja esta na conversa e historico
            self._marcar_historico(g)
            return
        _, msgs = self.nav.ler()
        for m in msgs:
            if m.minha or not estado.novo(m.id):
                continue
            if m.dia != self.hoje():
                estado.marcar(m.id)                # antiga ou sem data: ignora para sempre
                continue
            if m.blobs or m.carregando:
                espera = self.aguardando.get(m.id, 0)
                if m.carregando:                   # foto ainda borrada: espera baixar (sem perder a foto)
                    limite = 10 if m.blobs else 300
                    if espera < limite:
                        self.aguardando[m.id] = espera + 1
                        continue
                if not m.blobs:
                    self.evento("log", f"{g.nome}: uma foto de {m.remetente or 'alguém'} não carregou; confira no WhatsApp.")
                    estado.marcar(m.id)
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

    def _marcar_historico(self, g: Grupo) -> None:
        """Marca como 'ja visto' tudo o que ja esta na conversa. Espera o WhatsApp terminar de carregar o historico
        (senao o resto dele chegaria depois e seria tratado como novidade)."""
        estado = self.estados[g.nome]
        anterior = -1
        for _ in range(8):
            _, msgs = self.nav.ler()
            for m in msgs:
                estado.marcar(m.id)
            if msgs and len(msgs) == anterior:
                break
            anterior = len(msgs)
            if hasattr(self.nav, "aguardar"):
                self.nav.aguardar(1000)
        self.evento("log", f"{g.nome}: pronto. Daqui para frente salvo só o que chegar de novo.")

    LADO_MINIMO = 1000     # abaixo disso a foto do chat e so uma miniatura: abrimos a foto inteira

    @staticmethod
    def _lado_medio(fotos: list[bytes]) -> float:
        """Maior lado (em pixels) medio das fotos; 0 se nao der para medir."""
        import io
        from PIL import Image
        lados = []
        for f in fotos:
            try:
                with Image.open(io.BytesIO(f)) as im:
                    lados.append(max(im.size))
            except Exception:  # noqa: BLE001
                pass
        return sum(lados) / len(lados) if lados else 0

    def _fotos_da_mensagem(self, m) -> list[bytes]:
        fotos = self.nav.baixar(m.blobs)
        if m.mais and self.cfg.tentar_escondidas:                  # album grande: abre o visualizador e passa todas
            esperado = len(m.blobs) + m.mais - 1
            completo = self.nav.baixar_album_completo(m, esperado)
            if len(completo) >= len(fotos):
                m.observacao_album = "" if len(completo) >= esperado else f"álbum incompleto: esperadas {esperado}, baixadas {len(completo)}"
                return completo
            m.observacao_album = f"álbum incompleto: esperadas {esperado}, baixadas {len(fotos)} (faltam {esperado - len(fotos)})"
        elif m.mais:
            m.observacao_album = f"álbum com +{m.mais} foto(s) escondida(s): baixe o restante na mão"
        elif self.cfg.tentar_escondidas and fotos and 0 < self._lado_medio(fotos) < self.LADO_MINIMO:
            completo = self.nav.baixar_album_completo(m, len(fotos))       # miniaturas pequenas: tenta a foto inteira
            if len(completo) >= len(fotos) and self._lado_medio(completo) > self._lado_medio(fotos):
                return completo
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
            return
        nome = f"{CONFERIR} sem foto {nome_seguro(m.legenda)[:60]}"
        self._registrar(g.nome, "?", m.legenda, nome, [], "conferir",
                        "não encontrei a foto desta mensagem (pode ter sido enviada de um jeito que não reconheço); confira no WhatsApp")
        self.evento("log", f"{g.nome}: texto de {m.remetente or 'alguém'} sem foto correspondente — "
                          f"\"{m.legenda[:60]}\"; salvei em _Conferir para você revisar.")

    def _salvar_com_legenda(self, grupo: str, legenda: str, fotos: list[bytes], obs: str) -> None:
        d = dividir_legenda(legenda, self.marcas)
        if d.completa:
            ref, completa = self.regras_ref.aplicar(d.marca, d.referencia)
            d.referencia = ref
            nota = (obs + f" ref. completa na legenda: {completa}").strip() if completa else obs
            self._registrar(grupo, d.marca, ref, d.nome_pasta, fotos, "ok", nota)
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
        achados: dict[str, tuple[str, str, list[bytes], str]] = {}   # chave -> (marca, ref, fotos, ref completa)
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
                ref, completa = self.regras_ref.aplicar(marca, ref)
                chave = chave_referencia(ref)
                achados.setdefault(chave, (marca or "", ref, [], completa))[2].append(f)
            else:
                sem_leitura.append(f)
            if self.cfg.todas_do_grupo_b:          # copia numa pasta unica, com o nome do que foi lido (confere rapido)
                lido = f"{marca or ''} {ref}".strip() if ref else "não lida"
                salvar_fotos(self.pastas[g.nome], "_Todas as fotos", [f], prefixo=f"{m.hora.replace(':', 'h')} - {nome_seguro(lido)} - ")
        for marca, ref, lote, completa in achados.values():
            nome = f"{marca} {ref}".strip()
            obs = " ".join(x for x in ("" if marca else "marca não identificada na foto",
                                        f"etiqueta completa: {completa}" if completa else "") if x)
            self._registrar(g.nome, marca or "?", ref, nome, lote, "ok", obs)
        if sem_leitura:
            self._registrar(g.nome, "?", "não lida", f"{CONFERIR} etiqueta {m.hora.replace(':', 'h')} {m.id[-6:]}", sem_leitura,
                            "conferir", "não consegui ler a referência na foto")

    # ---- Conversa individual: salva o TEXTO do que a pessoa escreveu ----------
    def _conversa_individual(self, g: Grupo, ignorar_existentes: bool = False) -> None:
        from .texto import normalizar
        estado = self.estados[g.nome]
        if ignorar_existentes:
            self._marcar_historico(g)
            return
        _, msgs = self.nav.ler()
        mensagens: list[list[str]] = []
        previa = ""
        n_fotos = 0
        for m in msgs:
            if m.minha or not estado.novo(m.id):
                continue
            if m.dia != self.hoje():
                estado.marcar(m.id)
                continue
            if m.carregando and self.aguardando.get(m.id, 0) < 10:       # foto ainda borrada: espera baixar
                self.aguardando[m.id] = self.aguardando.get(m.id, 0) + 1
                continue
            if m.blobs:                                                    # foto: salva com o nome do contato
                try:
                    _, novas = salvar_fotos(self.pastas[g.nome], "fotos", self._fotos_da_mensagem(m),
                                            prefixo=f"{nome_pasta_grupo(g.nome)} - ")
                    n_fotos += novas
                except Exception as e:  # noqa: BLE001
                    self.evento("log", f"Erro ao baixar foto de {g.nome}: {e}")
                    continue
            texto = (m.legenda or "").strip()
            if texto and normalizar(texto) in APAGADA:
                texto = "[mensagem apagada antes de o monitor ler]"
            elif not texto:
                texto = "[foto]" if (m.blobs or m.carregando) else "[mídia sem texto: áudio, figurinha ou arquivo]"
            elif m.blobs or m.carregando:
                texto = "[foto] " + texto
            partes = texto.split("\n")
            mensagens.append([f"[{m.hora or '--:--'}] {partes[0]}"] + [f"        {p}" for p in partes[1:]])
            previa = previa or texto
            estado.marcar(m.id)
        if not mensagens:
            return
        n = len(mensagens)
        arq = anexar_mensagens(self.pastas[g.nome], mensagens)
        if n_fotos:
            self.evento("log", f"{g.nome}: {n_fotos} foto(s) salva(s) na pasta fotos")
        self.evento("log", f"{g.nome}: {n} mensagem(ns) salva(s) em {arq.name}")
        self.evento("salvo", {"grupo": g.nome, "tipo": "I", "mensagens": n, "fotos": n_fotos, "previa": previa[:80], "situacao": "ok", "obs": ""})
