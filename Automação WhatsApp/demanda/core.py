"""Lógica sem interface: marca/referência, pastas, lista, histórico, configuração.

Nada aqui envia mensagem ou apaga fotos/pastas do usuário.
"""
from __future__ import annotations

import datetime as dt
import difflib
import fnmatch
import hashlib
import json
import os
import re
import shutil
import sys
import threading
import unicodedata
import uuid
from pathlib import Path

# ----------------------------------------------------------------- caminhos


def app_dir() -> Path:
    """Pasta onde ficam os dados: ao lado do .exe (ou do código)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def data_dir() -> Path:
    """Onde ficam config, lista, histórico e o login do WhatsApp.

    Programa instalado em pasta protegida (ex.: Arquivos de Programas) não pode gravar ali,
    então os dados vão para %LOCALAPPDATA%\\DemandaDoDia. Caso contrário ficam ao lado do programa.
    """
    env = os.environ.get("DEMANDA_DADOS")
    if env:
        return Path(env)
    base = app_dir()
    if getattr(sys, "frozen", False):
        try:
            teste = base / ".gravavel"
            teste.write_text("ok")
            teste.unlink()
        except OSError:
            root = os.environ.get("LOCALAPPDATA") or str(Path.home())
            return Path(root) / "DemandaDoDia"
    return base


# ------------------------------------------------------------ configuração

DEFAULT_CONFIG = {
    "pasta_marcas": "",
    "grupos": [],  # vazio = qualquer grupo aberto
    "modo": "fotos_antes",  # ou "texto_antes"
    "sessao": "compartilhada",  # ou "dedicada" (segunda sessão só do monitor)
    "grupo_dedicado": "",  # nome do grupo aberto na sessão dedicada
    "intervalo_seg": 2.0,
    "espera_texto_seg": 120,
    "album_extra": 3,  # total = album_extra + N  (ponto incerto do plano)
    "pastas_ignoradas": ["nova pasta*", "fotos variadas"],
    "fixar_na_frente": True,
    "lista_destacada": False,
    "compat_grafica": True,  # desenho por software: evita a tela cinza/branca em alguns PCs
    "agrupar_por_marca": True,
    "marcas_recolhidas": [],
    "inicio_ref": "",  # "Estou fazendo": só entra o que chegar a partir desta referência
    "inicio_ok": False,  # já achou a referência no grupo?
    "largura_lista": 380,
    "geometria": "",
}


class Config:
    def __init__(self, path: Path):
        self.path = path
        self.data = dict(DEFAULT_CONFIG)
        self._lock = threading.RLock()
        self.load()

    def load(self) -> None:
        try:
            self.data.update(json.loads(self.path.read_text("utf-8")))
        except (OSError, ValueError):
            pass

    def save(self) -> None:
        with self._lock:
            _write_json(self.path, self.data)

    def __getitem__(self, k):
        return self.data.get(k, DEFAULT_CONFIG.get(k))

    def __setitem__(self, k, v):
        with self._lock:
            self.data[k] = v
            _write_json(self.path, self.data)


def _write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), "utf-8")
    os.replace(tmp, path)


# --------------------------------------------------- marca e referência

_FORBIDDEN = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def norm(s: str) -> str:
    """minúsculas, sem acento, sem apóstrofo, pontuação vira espaço."""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace("'", "").replace("’", "").replace("`", "")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return s.strip()


def safe_name(s: str) -> str:
    """Troca caracteres proibidos no Windows por espaço."""
    s = _FORBIDDEN.sub(" ", s)
    s = re.sub(r"\s+", " ", s).strip().rstrip(". ")
    return s or "sem nome"


def list_brands(root: str, ignoradas=None) -> list[str]:
    """Nomes das pastas de marca (relidas a cada chamada)."""
    ignoradas = ignoradas if ignoradas is not None else DEFAULT_CONFIG["pastas_ignoradas"]
    out = []
    try:
        for e in sorted(os.scandir(root), key=lambda x: x.name.lower()):
            if not e.is_dir():
                continue
            n = e.name
            if n.startswith("_"):
                continue
            low = n.lower()
            if any(fnmatch.fnmatch(low, p.lower()) for p in ignoradas):
                continue
            out.append(n)
    except OSError:
        pass
    return out


def split_caption(caption: str, brands: list[str]):
    """Devolve (marca_ou_None, referencia, pontuacao).

    Marca = a pasta de marca que aparece na legenda (sem maiúsculas/acentos/apóstrofo,
    aceitando erro de digitação leve). Referência = o resto, do jeito que veio.
    """
    text = re.sub(r"\s+", " ", caption or "").strip()
    words = text.split(" ") if text else []
    if not words:
        return None, "", 0.0
    best = None  # (score, ntokens, -pos, brand, pos)
    for brand in brands:
        bn = norm(brand)
        if not bn:
            continue
        n = len(bn.split())
        for pos in range(0, len(words) - n + 1):
            win = norm(" ".join(words[pos:pos + n]))
            if not win:
                continue
            score = 1.0 if win == bn else difflib.SequenceMatcher(None, win, bn).ratio()
            if score < 1.0 and (len(bn) <= 4 or score < 0.84):
                continue
            cand = (score, n, -pos, brand, pos)
            if best is None or cand[:3] > best[:3]:
                best = cand
    if best is None:
        return None, text, 0.0
    score, n, _, brand, pos = best
    rest = words[:pos] + words[pos + n:]
    while rest and not re.search(r"[0-9A-Za-zÀ-ÿ]", rest[0]):
        rest.pop(0)  # tira "-" ou ":" soltos entre a marca e a referência
    while rest and not re.search(r"[0-9A-Za-zÀ-ÿ]", rest[-1]):
        rest.pop()
    return brand, " ".join(rest), score


def target_folder(root: str, brand: str | None, ref: str, caption: str = "") -> Path:
    """<principal>\\<MARCA>\\<MARCA> <REF>  ou  <principal>\\_REVISAR\\<legenda>."""
    if brand:
        name = safe_name(f"{brand} {ref}".strip())
        return Path(root) / brand / name
    return Path(root) / "_REVISAR" / safe_name(caption or ref or "sem legenda")


# ------------------------------------------------------------------ fotos

_MAGIC = ((b"\xff\xd8\xff", ".jpg"), (b"\x89PNG", ".png"), (b"RIFF", ".webp"), (b"GIF8", ".gif"))
MIN_BYTES = 3 * 1024


def _ext(data: bytes) -> str:
    for m, e in _MAGIC:
        if data.startswith(m):
            return e
    return ".jpg"


def save_images(folder: Path, images: list[bytes]) -> int:
    """Grava foto_01.jpg... sem duplicar (SHA-1) e sem apagar nada. Devolve quantas novas."""
    folder.mkdir(parents=True, exist_ok=True)
    have = set()
    nums = [0]
    for f in folder.iterdir():
        if f.is_file():
            try:
                have.add(hashlib.sha1(f.read_bytes()).hexdigest())
            except OSError:
                pass
            m = re.match(r"foto_(\d+)", f.stem)
            if m:
                nums.append(int(m.group(1)))
    n, saved = max(nums), 0
    for data in images:
        if not data or len(data) < MIN_BYTES:
            continue
        h = hashlib.sha1(data).hexdigest()
        if h in have:
            continue
        n += 1
        (folder / f"foto_{n:02d}{_ext(data)}").write_bytes(data)
        have.add(h)
        saved += 1
    return saved


def count_photos(folder: Path) -> int:
    try:
        return sum(1 for f in folder.iterdir() if f.is_file()
                   and f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp", ".gif"))
    except OSError:
        return 0


def move_folder(src: Path, dst: Path) -> None:
    """Move a pasta; se o destino existe, mescla os arquivos (não sobrescreve)."""
    if src.resolve() == dst.resolve() or not src.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not dst.exists():
        shutil.move(str(src), str(dst))
        return
    for f in src.iterdir():
        target = dst / f.name
        i = 1
        while target.exists():
            target = dst / f"{f.stem}_{i}{f.suffix}"
            i += 1
        shutil.move(str(f), str(target))
    try:
        src.rmdir()  # só some se ficou vazia (nunca apaga conteúdo)
    except OSError:
        pass


# ---------------------------------------------------------------- lista

def today() -> str:
    return dt.date.today().isoformat()


class Store:
    """Lista de demandas (lista.json), com trava para uso entre threads."""

    def __init__(self, path: Path):
        self.path = path
        self.lock = threading.RLock()
        self.items: list[dict] = []
        self.load()

    def load(self) -> None:
        try:
            self.items = json.loads(self.path.read_text("utf-8"))
        except (OSError, ValueError):
            self.items = []
        t = today()
        # prontas de dias anteriores somem; pendentes continuam
        self.items = [d for d in self.items if not (self.is_done(d) and d.get("date") != t)]
        self.save()

    def save(self) -> None:
        with self.lock:
            _write_json(self.path, self.items)

    @staticmethod
    def is_done(d: dict) -> bool:
        return bool(d.get("site") and d.get("atacado"))

    def add(self, **kw) -> dict:
        with self.lock:
            d = {"id": uuid.uuid4().hex[:10], "brand": "", "ref": "", "folder": "",
                 "photos": 0, "sender": "", "time": dt.datetime.now().strftime("%H:%M"),
                 "date": today(), "site": False, "atacado": False, "warn": [],
                 "msg_id": "", "plus": 0}
            d.update(kw)
            self.items.append(d)
            self.save()
            return d

    def find_open(self, brand: str, ref: str):
        with self.lock:
            for d in self.items:
                if (not self.is_done(d) and norm(d["brand"]) == norm(brand)
                        and norm(d["ref"]) == norm(ref) and brand):
                    return d
        return None

    def get(self, did: str):
        with self.lock:
            return next((d for d in self.items if d["id"] == did), None)

    def update(self, did: str, **kw) -> None:
        with self.lock:
            d = self.get(did)
            if d:
                d.update(kw)
                self.save()

    def remove(self, did: str) -> None:
        with self.lock:
            self.items = [d for d in self.items if d["id"] != did]
            self.save()

    def ordered(self) -> list[dict]:
        with self.lock:
            pend = [d for d in self.items if not self.is_done(d)]
            done = [d for d in self.items if self.is_done(d)]
            return [dict(d) for d in pend + done]

    def counts(self) -> tuple[int, int]:
        with self.lock:
            done = sum(1 for d in self.items if self.is_done(d) and d.get("date") == today())
            return sum(1 for d in self.items if not self.is_done(d)), done


# ------------------------------------------------------ histórico e vistos

class History:
    def __init__(self, path: Path):
        self.path = path
        self.lock = threading.Lock()

    def add(self, evento: str, marca: str = "", ref: str = "", fotos: int | str = "",
            pasta: str = "") -> None:
        row = {"data": today(), "hora": dt.datetime.now().strftime("%H:%M:%S"),
               "evento": evento, "marca": marca, "ref": ref, "fotos": fotos, "pasta": pasta}
        with self.lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def today(self) -> list[dict]:
        out = []
        try:
            for line in self.path.read_text("utf-8").splitlines():
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if r.get("data") == today():
                    out.append(r)
        except OSError:
            pass
        return list(reversed(out))


class Seen:
    MAX = 4000

    def __init__(self, path: Path):
        self.path = path
        try:
            self.ids = json.loads(path.read_text("utf-8"))
        except (OSError, ValueError):
            self.ids = []
        self._set = set(self.ids)

    def __contains__(self, i: str) -> bool:
        return i in self._set

    def add(self, i: str) -> None:
        if i in self._set:
            return
        self._set.add(i)
        self.ids.append(i)
        if len(self.ids) > self.MAX:
            self.ids = self.ids[-self.MAX:]
            self._set = set(self.ids)
        _write_json(self.path, self.ids)


def summary_text(items: list[dict]) -> str:
    """Resumo do dia agrupado por marca."""
    d = dt.date.today().strftime("%d/%m/%Y")
    out = [f"RESUMO DO DIA — {d}", ""]
    by: dict[str, list[dict]] = {}
    for it in items:
        by.setdefault(it["brand"] or "SEM MARCA", []).append(it)
    for brand in sorted(by, key=str.lower):
        out.append(brand)
        for it in by[brand]:
            s = "OK" if it.get("site") else "--"
            a = "OK" if it.get("atacado") else "--"
            out.append(f"  - {it['ref'] or '(sem referência)'}  "
                       f"[{it.get('photos', 0)} foto(s)]  Site: {s}  Atacado: {a}")
        out.append("")
    pend, done = sum(1 for i in items if not Store.is_done(i)), sum(1 for i in items if Store.is_done(i))
    out.append(f"Pendentes: {pend} · Prontas: {done}")
    return "\n".join(out)


# ----------------------------------------------- pesquisa e agrupamento

def matches(item: dict, query: str) -> bool:
    """Todas as palavras da pesquisa têm que aparecer em marca/referência/remetente."""
    q = norm(query)
    if not q:
        return True
    alvo = norm(f"{item.get('brand', '')} {item.get('ref', '')} {item.get('sender', '')}")
    return all(t in alvo for t in q.split())


def group_by_brand(items: list[dict], query: str = "") -> list[tuple[str, list[dict]]]:
    """[(marca, [itens])]: sem marca primeiro (precisa de revisão), depois A-Z.

    Dentro de cada marca: pendentes por ordem de chegada, prontas no fim.
    """
    groups: dict[str, list[dict]] = {}
    for it in items:
        if matches(it, query):
            groups.setdefault(it.get("brand") or "", []).append(it)
    out = []
    for brand in sorted(groups, key=lambda b: (b != "", norm(b))):
        its = groups[brand]
        its = [i for i in its if not Store.is_done(i)] + [i for i in its if Store.is_done(i)]
        out.append((brand or "SEM MARCA (revisar)", its))
    return out


def caption_has_ref(caption: str, start: str) -> bool:
    """A legenda contém a referência marcada em "Estou fazendo"?"""
    a, b = norm(caption), norm(start)
    return bool(b) and f" {b} " in f" {a} "


# ------------------------------------------------- colar demandas de fora

_BULLET = re.compile(r"^\s*(?:[-–—•*·▪●■□✔✅☑]|\d{1,3}[.)])\s*")


def parse_lines(text: str) -> list[str]:
    """Uma demanda por linha. Tira marcadores (-, •, 1., 2)...), espaços e repetidas."""
    out, vistas = [], set()
    for raw in (text or "").replace("\t", " ").splitlines():
        line = raw.strip()
        while True:
            novo = _BULLET.sub("", line).strip()
            if novo == line:
                break
            line = novo
        line = re.sub(r"\s+", " ", line)
        if line and norm(line) not in vistas:
            vistas.add(norm(line))
            out.append(line)
    return out


def plan_paste(text: str, brands: list[str], items: list[dict]) -> list[dict]:
    """Prévia do que acontece com cada linha colada.

    status: nova | revisar (marca com erro de digitação) | sem_marca | repetida
    """
    existentes = {(norm(i.get("brand", "")), norm(i.get("ref", ""))) for i in items}
    out = []
    for line in parse_lines(text):
        brand, ref, score = split_caption(line, brands)
        key = (norm(brand or ""), norm(ref))
        if key in existentes:
            status = "repetida"
        elif not brand:
            status = "sem_marca"
        elif score < 1.0:
            status = "revisar"
        else:
            status = "nova"
        out.append({"line": line, "brand": brand, "ref": ref, "status": status})
    return out
