"""Rodizio entre IAs gratuitas, usando a biblioteca freelm (MIT, 1 dependencia: httpx).

O freelm cuida de: trocar de provedor/chave ao bater o limite (429), pausar quem falha,
descobrir quais modelos estao gratuitos hoje e escolher modelo com visao para fotos.
"""
from __future__ import annotations

import base64
import io
import json
import os
import re
from dataclasses import dataclass

from dotenv import load_dotenv, set_key

from .caminhos import CONFIG, ENV


class ErroIA(Exception):
    """Erro ja traduzido para o usuario (portugues)."""


@dataclass
class RespostaIA:
    texto: str
    provedor: str = ""
    modelo: str = ""


def extrair_json(texto: str) -> dict:
    """Pega o primeiro objeto JSON da resposta (tolera ```json ... ``` e texto em volta)."""
    texto = re.sub(r"^```(?:json)?|```$", "", texto.strip(), flags=re.MULTILINE).strip()
    inicio = texto.find("{")
    if inicio < 0:
        raise ErroIA("A IA não respondeu no formato esperado.")
    nivel, em_texto, escape = 0, False, False
    for i in range(inicio, len(texto)):
        c = texto[i]
        if em_texto:
            if escape:
                escape = False
            elif c == "\\":
                escape = True
            elif c == '"':
                em_texto = False
        elif c == '"':
            em_texto = True
        elif c == "{":
            nivel += 1
        elif c == "}":
            nivel -= 1
            if nivel == 0:
                try:
                    return json.loads(texto[inicio:i + 1])
                except json.JSONDecodeError as e:
                    raise ErroIA(f"Resposta da IA com JSON inválido: {e}") from e
    raise ErroIA("A resposta da IA veio cortada (JSON incompleto).")


def foto_para_data_url(caminho, lado_max: int = 1024, qualidade: int = 80) -> str:
    """Reduz a foto (max 1024 px, JPEG 80) para economizar banda e cota."""
    from PIL import Image, ImageOps
    with Image.open(caminho) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        im.thumbnail((lado_max, lado_max))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=qualidade)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def traduzir_erro(e: Exception) -> str:
    nome = type(e).__name__
    msg = str(e)
    if nome == "NoProvidersAvailable":
        return "Nenhuma IA gratuita disponível agora (limite atingido ou chave inválida). Tente de novo em alguns minutos ou use o modo offline."
    if nome == "ConfigError":
        return "Nenhuma chave de IA configurada. Abra Configurações e cole pelo menos a chave do Google AI Studio."
    if nome == "AuthError":
        return "Chave recusada pelo provedor. Gere outra chave e cole em Configurações."
    return f"Erro ao falar com a IA: {msg[:200]}"


class Provedores:
    def __init__(self) -> None:
        load_dotenv(ENV)
        self.cfg = json.loads((CONFIG / "provedores.json").read_text(encoding="utf-8"))
        self.llm = None
        self.ultimo_provedor = ""
        self.reconstruir()

    # ---- configuracao -------------------------------------------------
    @property
    def itens(self) -> list[dict]:
        return sorted((p for p in self.cfg["provedores"] if p.get("ativo", True)), key=lambda p: p["prioridade"])

    def chave(self, item: dict) -> str:
        return os.environ.get(item["variavel_chave"], "").strip()

    def reconstruir(self) -> None:
        import freelm
        provs = []
        for item in self.itens:
            k = self.chave(item)
            if k:
                provs.append(getattr(freelm, item["classe"])(k, priority=item["prioridade"]))
        self.llm = freelm.FreeLLM(provs, persist=True) if provs else None

    def salvar_chave(self, item: dict, valor: str) -> None:
        valor = valor.strip()
        ENV.touch(exist_ok=True)
        set_key(str(ENV), item["variavel_chave"], valor, quote_mode="never")
        os.environ[item["variavel_chave"]] = valor
        self.reconstruir()

    def status(self) -> list[tuple[str, str]]:
        """[(nome, 'conectado' | 'em pausa' | 'não configurado')]"""
        saude = self.llm.health() if self.llm else []
        out = []
        for item in self.itens:
            if not self.chave(item):
                out.append((item["nome"], "não configurado"))
                continue
            h = [x for x in saude if x["provider"].lower().startswith(item["id"][:4])]
            pausa = bool(h) and not any(x["ready"] and not x["disabled"] for x in h)
            out.append((item["nome"], "em pausa (limite)" if pausa else "conectado"))
        return out

    def resumo(self) -> str:
        st = self.status()
        ok = sum(1 for _, s in st if s == "conectado")
        return f"IA: {ok} de {len(st)} provedores disponíveis" + (f" · última resposta: {self.ultimo_provedor}" if self.ultimo_provedor else "")

    @property
    def tem_alguma(self) -> bool:
        return self.llm is not None

    # ---- chamadas -------------------------------------------------------
    def chat(self, sistema: str, usuario: str, imagens: list | None = None, max_tokens: int = 3000) -> RespostaIA:
        if self.llm is None:
            raise ErroIA("Nenhuma chave de IA configurada. Abra Configurações e cole pelo menos a chave do Google AI Studio.")
        if imagens:
            conteudo = [{"type": "text", "text": usuario}] + [
                {"type": "image_url", "image_url": {"url": foto_para_data_url(f)}} for f in imagens]
            modelo = self.cfg["modelos"]["visao"]
        else:
            conteudo, modelo = usuario, self.cfg["modelos"]["texto"]
        msgs = [{"role": "system", "content": sistema}, {"role": "user", "content": conteudo}]
        try:
            r = self.llm.chat(msgs, model=modelo, max_tokens=max_tokens)
        except Exception as e:  # noqa: BLE001
            raise ErroIA(traduzir_erro(e)) from e
        self.ultimo_provedor = f"{r.provider}"
        return RespostaIA(r.text, str(r.provider), str(r.model))

    def testar(self, item: dict, chave: str) -> tuple[bool, str]:
        """Chamada minima so para ver se a chave funciona."""
        import freelm
        try:
            llm = freelm.FreeLLM([getattr(freelm, item["classe"])(chave.strip())])
            r = llm.chat([{"role": "user", "content": "Responda apenas: ok"}], model="auto", max_tokens=256)
            return True, f"Funcionando ({r.provider})."
        except Exception as e:  # noqa: BLE001
            return False, traduzir_erro(e)


PADROES_CHAVE = {"google": r"AIza[0-9A-Za-z_\-]{30,}", "groq": r"gsk_[0-9A-Za-z]{20,}", "openrouter": r"sk-or-[0-9A-Za-z_\-]{20,}"}


def detectar_chave(texto: str, item_id: str) -> str:
    """Procura na area de transferencia algo com cara de chave do provedor. Devolve '' se nao achar."""
    m = re.search(PADROES_CHAVE.get(item_id, r"$^"), texto or "")
    return m.group(0) if m else ""
