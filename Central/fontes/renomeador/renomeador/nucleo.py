"""Regras de renomeacao em sequencia (sem interface; tudo testavel)."""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

INVALIDOS = r'[<>:"/\\|?*\x00-\x1f]'
ORDENS = {
    "data": "Data do arquivo (mais antigo primeiro)",
    "foto": "Data em que a foto foi tirada",
    "nome": "Nome do arquivo (1, 2, 10...)",
    "selecao": "Ordem em que foram selecionados",
}
SEPARADORES = {"espaco": " ", "traco": "-", "sublinhado": "_", "nenhum": ""}


def nome_seguro(nome: str) -> str:
    """Tira caracteres que o Windows nao aceita e pontos/espacos nas pontas."""
    return re.sub(INVALIDOS, "", nome).strip(" .")


def chave_natural(caminho: str | Path):
    """Ordem natural: 'foto 2' antes de 'foto 10'."""
    nome = os.path.basename(str(caminho)).lower()
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", nome)]


def data_da_foto(caminho: str | Path) -> float:
    """Data em que a foto foi tirada (EXIF); se nao tiver, usa a data do arquivo."""
    try:
        from PIL import Image
        with Image.open(caminho) as im:
            exif = im.getexif()
            bruto = (exif.get_ifd(0x8769).get(0x9003) if hasattr(exif, "get_ifd") else None) or exif.get(0x0132)
        if bruto:
            return datetime.strptime(str(bruto)[:19], "%Y:%m:%d %H:%M:%S").timestamp()
    except Exception:  # noqa: BLE001
        pass
    return os.path.getmtime(caminho)


def ordenar(arquivos: list[str], ordem: str) -> list[str]:
    arqs = list(arquivos)
    if ordem == "data":
        arqs.sort(key=lambda p: (os.path.getmtime(p), chave_natural(p)))
    elif ordem == "foto":
        arqs.sort(key=lambda p: (data_da_foto(p), chave_natural(p)))
    elif ordem == "nome":
        arqs.sort(key=chave_natural)
    return arqs


@dataclass
class Opcoes:
    nome: str = ""
    inicio: int | None = None          # None = automatico (continua a numeracao que ja existe na pasta, ou 1)
    zeros: bool = True                 # 01, 02, 03...
    separador: str = "espaco"          # espaco | traco | sublinhado | nenhum
    ordem: str = "data"
    continuar: bool = True             # se a pasta ja tem 'branco 01..05', comeca em 06
    extensao_minuscula: bool = True


@dataclass
class Plano:
    pares: list[tuple[str, str]] = field(default_factory=list)       # (antigo, novo)
    inicio: int = 1
    avisos: list[str] = field(default_factory=list)
    erro: str = ""


def _maior_numero_existente(pasta: Path, base: str, sep: str, ignorar: set[str]) -> int:
    rx = re.compile(r"^" + re.escape(base) + re.escape(sep) + r"(\d+)(?:\.[^.]+)?$", re.IGNORECASE)
    maior = 0
    try:
        for f in pasta.iterdir():
            if f.is_file() and str(f).lower() not in ignorar:
                m = rx.match(f.name)
                if m:
                    maior = max(maior, int(m.group(1)))
    except OSError:
        pass
    return maior


def montar_plano(arquivos: list[str], op: Opcoes) -> Plano:
    """Calcula (antigo -> novo) sem mexer em nada."""
    plano = Plano()
    base = nome_seguro(op.nome)
    if not arquivos:
        plano.erro = "Nenhum arquivo selecionado."
        return plano
    if not base:
        plano.erro = "Digite o novo nome."
        return plano
    sep = SEPARADORES.get(op.separador, " ")
    arqs = ordenar(arquivos, op.ordem)
    pasta = Path(arqs[0]).parent
    selecionados = {str(Path(a)).lower() for a in arqs}
    inicio = op.inicio
    if inicio is None:
        inicio = (_maior_numero_existente(pasta, base, sep, selecionados) + 1) if op.continuar else 1
        if inicio > 1:
            plano.avisos.append(f"Já existem arquivos \"{base}{sep}…\" na pasta: a numeração continua do {inicio}.")
    plano.inicio = inicio
    ultimo = inicio + len(arqs) - 1
    largura = max(2 if op.zeros else 1, len(str(ultimo))) if op.zeros else 1
    for i, a in enumerate(arqs):
        ext = Path(a).suffix
        ext = ext.lower() if op.extensao_minuscula else ext
        numero = str(inicio + i).zfill(largura)
        plano.pares.append((str(a), str(Path(a).parent / f"{base}{sep}{numero}{ext}")))
    # conflitos com arquivos que NAO estao na selecao
    for _, novo in plano.pares:
        if Path(novo).exists() and str(novo).lower() not in selecionados:
            plano.erro = f"Já existe um arquivo que não está na seleção: {Path(novo).name}. Escolha outro nome ou outro número inicial."
            break
    if len({n.lower() for _, n in plano.pares}) != len(plano.pares):
        plano.erro = "Dois arquivos ficariam com o mesmo nome."
    return plano


def executar(pares: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Renomeia com seguranca: primeiro nomes temporarios (evita colisao entre nomes novos e antigos).
    Se algo falhar, desfaz tudo. Devolve [(novo, antigo)] para poder desfazer."""
    temporarios: list[tuple[str, str, str]] = []
    try:
        for i, (a, n) in enumerate(pares):
            if os.path.normcase(a) == os.path.normcase(n):
                continue
            tmp = str(Path(a).parent / f"__ren_tmp_{i}_{Path(a).name}")
            os.rename(a, tmp)
            temporarios.append((tmp, a, n))
        feitos = []
        for tmp, a, n in temporarios:
            os.rename(tmp, n)
            feitos.append((n, a))
        return feitos
    except Exception:
        for tmp, a, n in temporarios:           # volta tudo ao que era
            try:
                if os.path.exists(tmp):
                    os.rename(tmp, a)
                elif os.path.exists(n):
                    os.rename(n, a)
            except OSError:
                pass
        raise


def desfazer(feitos: list[tuple[str, str]]) -> int:
    """Volta os nomes originais. Devolve quantos voltaram; avisa (erro) se algum arquivo sumiu."""
    faltando = [n for n, _ in feitos if not os.path.exists(n)]
    if faltando:
        raise FileNotFoundError(f"Não achei mais: {Path(faltando[0]).name}. Os arquivos foram movidos ou renomeados depois.")
    for i, (novo, _) in enumerate(feitos):
        os.rename(novo, str(Path(novo).parent / f"__des_tmp_{i}__"))
    for i, (novo, antigo) in enumerate(feitos):
        os.rename(str(Path(novo).parent / f"__des_tmp_{i}__"), antigo)
    return len(feitos)


# ------------------------------------------------------------------ historico (desfazer mesmo depois de fechar)
class Historico:
    def __init__(self, arquivo: Path, limite: int = 20) -> None:
        self.arquivo, self.limite = Path(arquivo), limite

    def _ler(self) -> list[dict]:
        try:
            return json.loads(self.arquivo.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []

    def registrar(self, feitos: list[tuple[str, str]], nome: str) -> None:
        itens = self._ler()
        itens.append({"quando": datetime.now().isoformat(timespec="seconds"), "nome": nome, "feitos": feitos})
        self.arquivo.parent.mkdir(parents=True, exist_ok=True)
        self.arquivo.write_text(json.dumps(itens[-self.limite:], ensure_ascii=False), encoding="utf-8")

    def ultimo(self) -> dict | None:
        itens = self._ler()
        return itens[-1] if itens else None

    def remover_ultimo(self) -> None:
        itens = self._ler()
        if itens:
            self.arquivo.write_text(json.dumps(itens[:-1], ensure_ascii=False), encoding="utf-8")
