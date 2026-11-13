"""Pesquisa na internet (DuckDuckGo via ddgs, sem chave), leitura das paginas, log e peso."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date
from urllib.parse import urlparse

from .caminhos import LOGS
from .texto import normalizar

DOMINIOS_BLOQUEADOS = ("calcados24h.com.br",)   # a propria loja: nunca usar como fonte (Parte 11 do v5)
MIN_BUSCAS = 4
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"


@dataclass
class Pagina:
    url: str
    site: str = ""
    titulo: str = ""
    descricao: str = ""
    imagem: str = ""
    texto: str = ""
    dados: dict = field(default_factory=dict)
    referencia_na_pagina: str = ""
    exata: bool = False
    irma: bool = False


@dataclass
class ResultadoPesquisa:
    consultas: list[str] = field(default_factory=list)
    paginas: list[Pagina] = field(default_factory=list)
    divergencias: list[str] = field(default_factory=list)
    peso: str = "não encontrado"
    cor_sugerida: str = ""

    def resumo_para_ia(self, limite: int = 4000) -> str:
        """So dados confirmados para ESTA referencia entram como fato; irmas ficam marcadas."""
        linhas = []
        for pg in self.paginas:
            if pg.irma and not pg.exata:
                linhas.append(f"[NÃO CONFIRMADO PARA ESTA REFERÊNCIA — referência irmã] {pg.titulo}: {json.dumps(pg.dados, ensure_ascii=False)}")
            else:
                linhas.append(f"[{pg.site}] {pg.titulo}: {json.dumps(pg.dados, ensure_ascii=False)} {pg.descricao[:300]}")
        return "\n".join(linhas)[:limite]


def bloqueado(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return any(host == d or host.endswith("." + d) for d in DOMINIOS_BLOQUEADOS)


def formatos_referencia(ref: str) -> list[str]:
    """'2282.107' -> ['2282.107', '2282-107', '2282107']"""
    ref = ref.strip()
    base = re.sub(r"[.\-/ ]", ".", ref)
    out = [ref, base, base.replace(".", "-"), base.replace(".", "")]
    return list(dict.fromkeys(x for x in out if x))


def prefixo_irma(ref: str) -> str:
    m = re.match(r"^(\w+)[.\-/]", ref.strip())
    return m.group(1) if m else ""


def montar_consultas(marca: str, ref: str, categoria: str, genero: str) -> list[str]:
    f = formatos_referencia(ref)
    cons = [f"{marca} {f[0]}", f[0]]
    cons += [x for x in f[1:]]
    cons += [f"{marca} {f[0]} {categoria} {genero}".strip(), f"{marca} {f[0]} comprar"]
    return list(dict.fromkeys(c.strip() for c in cons if c.strip()))


def classificar_referencia(texto: str, ref: str) -> tuple[bool, bool]:
    """(exata, irma). Exata = a referencia completa aparece (com ou sem pontuacao); irma = so o prefixo da linha."""
    compacto = re.sub(r"[^A-Z0-9]", "", texto.upper())
    alvo = re.sub(r"[^A-Z0-9]", "", ref.upper())
    if alvo and alvo in compacto:
        return True, False
    pre = prefixo_irma(ref)
    if pre and re.search(rf"(?<![A-Z0-9]){re.escape(pre.upper())}[.\-/ ]?\d", texto.upper()):
        return False, True
    return False, False


# ----------------------------------------------------------- extracao
CAMPOS = {
    "material": r"(?:material(?: externo| do cabedal)?|cabedal)\s*[:\-]\s*([^\n|;]{3,80})",
    "solado": r"solado\s*[:\-]\s*([^\n|;]{3,60})",
    "palmilha": r"palmilha\s*[:\-]\s*([^\n|;]{3,60})",
    "salto": r"(?:altura do salto|salto)\s*[:\-]?\s*([\d.,]+\s*cm)",
    "cor": r"\bcor(?: do produto)?\s*[:\-]\s*([^\n|;]{3,40})",
    "numeracao": r"(?:numera[cç][aã]o|tamanhos?)\s*[:\-]\s*([^\n|;]{2,40})",
}


def extrair_dados(texto: str) -> dict:
    dados = {}
    for campo, rx in CAMPOS.items():
        m = re.search(rx, texto, flags=re.IGNORECASE)
        if m:
            dados[campo] = re.sub(r"\s+", " ", m.group(1)).strip(" .:;,")
    peso = extrair_peso(texto)
    if peso:
        dados["peso"] = peso
    return dados


def extrair_peso(texto: str) -> str:
    """Procura 'peso: 350 g'. Avisa se o valor parece ser da caixa/embalagem."""
    for m in re.finditer(r"peso[^\d\n]{0,30}([\d]+(?:[.,]\d+)?)\s*(kg|g|gramas)\b", texto, flags=re.IGNORECASE):
        valor, un = m.group(1), m.group(2).lower()
        contexto = texto[max(0, m.start() - 60): m.end() + 80].lower()
        aviso = ""
        if re.search(r"caixa|embalagem|dimens|altura x|largura|comprimento", contexto):
            aviso = " (ATENÇÃO: parece peso de caixa/embalagem, não do produto)"
        par = " (do par)" if "par" in contexto else (" (de um pé)" if re.search(r"\bpé\b|unidade", contexto) else " (não informa se é de um pé ou do par)")
        return f"{valor} {'g' if un.startswith('g') else 'kg'}{par}{aviso}"
    return ""


def ler_html(url: str, html: str) -> Pagina:
    try:
        from selectolax.lexbor import LexborHTMLParser as HTMLParser   # versoes novas
    except ImportError:
        from selectolax.parser import HTMLParser
    arvore = HTMLParser(html)

    def meta(*nomes):
        for n in nomes:
            no = arvore.css_first(f'meta[property="{n}"]') or arvore.css_first(f'meta[name="{n}"]')
            if no and no.attributes.get("content"):
                return no.attributes["content"].strip()
        return ""

    titulo = meta("og:title") or (arvore.css_first("title").text().strip() if arvore.css_first("title") else "")
    for tag in arvore.css("script, style, noscript"):
        tag.decompose()
    corpo = arvore.body.text(separator="\n") if arvore.body else ""
    texto = re.sub(r"\n\s*\n+", "\n", corpo)[:20000]
    pg = Pagina(url=url, site=urlparse(url).netloc.replace("www.", ""), titulo=titulo,
                descricao=meta("og:description", "description"), imagem=meta("og:image", "twitter:image"), texto=texto)
    pg.dados = extrair_dados(titulo + "\n" + pg.descricao + "\n" + texto)
    return pg


def baixar(url: str, timeout: float = 12) -> str:
    import httpx
    r = httpx.get(url, headers={"User-Agent": UA, "Accept-Language": "pt-BR,pt;q=0.9"}, timeout=timeout, follow_redirects=True)
    r.raise_for_status()
    return r.text


def baixar_imagem(url: str, timeout: float = 10) -> bytes:
    import httpx
    r = httpx.get(url, headers={"User-Agent": UA}, timeout=timeout, follow_redirects=True)
    r.raise_for_status()
    return r.content[:3_000_000]


def busca_ddgs(consulta: str, max_resultados: int = 8) -> list[dict]:
    from ddgs import DDGS
    return list(DDGS().text(consulta, region="br-pt", max_results=max_resultados))


# ----------------------------------------------------------- orquestracao
def pesquisar(marca: str, ref: str, categoria: str, genero: str, *, busca=busca_ddgs, abrir=baixar,
              max_paginas: int = 8, progresso=lambda msg: None) -> ResultadoPesquisa:
    res = ResultadoPesquisa()
    consultas = montar_consultas(marca, ref, categoria, genero)
    if len(consultas) < MIN_BUSCAS:
        consultas += [f"{marca} {categoria} {ref}", f"{categoria} {ref}"]
    urls: dict[str, dict] = {}

    def rodar(cons):
        res.consultas.append(cons)
        progresso(f"Buscando: {cons}")
        try:
            for item in busca(cons):
                u = item.get("href") or item.get("url") or ""
                if u and not bloqueado(u) and u not in urls:
                    urls[u] = item
        except Exception as e:  # noqa: BLE001
            progresso(f"  busca falhou ({e})")

    for c in consultas:
        rodar(c)
    pre = prefixo_irma(ref)
    exatas = 0
    for u, item in list(urls.items())[: max_paginas * 2]:
        if len(res.paginas) >= max_paginas:
            break
        progresso(f"Abrindo: {u}")
        try:
            pg = ler_html(u, abrir(u))
        except Exception as e:  # noqa: BLE001
            progresso(f"  não abriu ({e})")
            continue
        pg.exata, pg.irma = classificar_referencia(pg.titulo + " " + pg.descricao + " " + pg.texto[:6000] + " " + u, ref)
        if pg.exata or pg.irma:
            res.paginas.append(pg)
            exatas += pg.exata
    if not exatas and pre:                      # procura referencias irmas da mesma linha
        rodar(f"{marca} {pre}")
    res.paginas.sort(key=lambda p: (not p.exata, p.irma))
    res.divergencias = achar_divergencias([p for p in res.paginas if p.exata])
    pesos = [p.dados["peso"] for p in res.paginas if p.exata and p.dados.get("peso")]
    res.peso = pesos[0] if pesos else "não encontrado"
    cores = [p.dados["cor"] for p in res.paginas if p.exata and p.dados.get("cor")]
    res.cor_sugerida = sugerir_cor(cores[0]) if cores else ""
    return res


def achar_divergencias(paginas: list[Pagina]) -> list[str]:
    out = []
    for campo in ("salto", "solado", "material", "peso"):
        valores = {normalizar(p.dados[campo]): (p.site, p.dados[campo]) for p in paginas if p.dados.get(campo)}
        if len(valores) > 1:
            out.append(f"{campo}: " + " x ".join(f"{v} ({s})" for s, v in valores.values()))
    return out


def candidatos_sem_foto(res: ResultadoPesquisa, limite: int = 5) -> list[Pagina]:
    """Cartoes para o usuario confirmar (Parte 3A): so paginas com imagem, exatas primeiro."""
    return [p for p in res.paginas if p.imagem][:limite]


# ----------------------------------------------------------- cor (Parte 8)
ACENTOS_COR = {"CAFE": "Café", "CONHAQUE": "Conhaque", "CARAMELO": "Caramelo", "BORDO": "Bordô", "LILAS": "Lilás",
               "AREIA": "Areia", "MARINHO": "Marinho"}
ABREV_COR = {"BC": "Branco", "MLT": "Multicolor", "PT": "Preto", "PR": "Preto", "BR": "Branco"}


def sugerir_cor(texto: str) -> str:
    """'CAFE 569/CONHAQUE 1273' -> 'Café/Conhaque'; tira os codigos numericos e padroniza."""
    partes = [x for x in re.split(r"[/]", texto.upper()) if x.strip()]
    out = []
    for parte in partes:
        palavras = [w for w in re.sub(r"\b\d+\b", "", parte).split() if w]
        if not palavras:
            continue
        nome = " ".join(ACENTOS_COR.get(w, ABREV_COR.get(w, w.capitalize())) for w in palavras)
        out.append(nome)
    return "/".join(out)


# ----------------------------------------------------------- log
def salvar_log(marca: str, ref: str, res: ResultadoPesquisa, *, etiqueta: dict | None = None, base_visual: str = "") -> str:
    pasta = LOGS / date.today().isoformat()
    pasta.mkdir(parents=True, exist_ok=True)
    nome = re.sub(r"[^A-Za-z0-9_.-]+", "_", f"{marca}_{ref}") + ".md"
    L = [f"# {marca} {ref}", "", "## Buscas feitas"] + [f"- {c}" for c in res.consultas]
    L += ["", "## Páginas abertas"]
    for p in res.paginas:
        tipo = "referência exata" if p.exata else "referência irmã (não confirmado para esta referência)"
        L += [f"- {p.url} — {tipo}", f"  - título: {p.titulo}", f"  - dados: {json.dumps(p.dados, ensure_ascii=False)}"]
    L += ["", "## Divergências entre fontes"] + ([f"- {d}" for d in res.divergencias] or ["- nenhuma encontrada"])
    L += ["", f"## Peso\n- {res.peso}", f"\n## Sugestão para o campo de cor\n- {res.cor_sugerida or 'não identificada'}"]
    if etiqueta:
        L += ["", "## Etiqueta lida da foto", f"- {json.dumps(etiqueta, ensure_ascii=False)}"]
    if base_visual:
        L += ["", f"## Base visual\n- {base_visual}"]
    caminho = pasta / nome
    caminho.write_text("\n".join(L) + "\n", encoding="utf-8")
    return "\n".join(L)
