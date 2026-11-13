"""Lista da demanda do dia (arquivo JSON + CSV na pasta do dia)."""
from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

CABECALHO = ["hora", "grupo", "marca", "referencia", "fotos", "situacao", "feito", "pasta", "observacao"]


@dataclass
class Item:
    chave: str
    hora: str
    grupo: str
    marca: str
    referencia: str
    fotos: int
    situacao: str          # ok | conferir
    pasta: str
    observacao: str = ""
    feito: bool = False


class ListaDoDia:
    def __init__(self, pasta_dia: Path) -> None:
        self.pasta = Path(pasta_dia)
        self.arquivo = self.pasta / "lista_do_dia.json"
        self.itens: dict[str, Item] = {}
        self.recarregar()

    def recarregar(self) -> None:
        """Le de novo do arquivo (a janela pode ter marcado 'feito' enquanto o monitor trabalhava)."""
        if self.arquivo.is_file():
            try:
                self.itens = {d["chave"]: Item(**d) for d in json.loads(self.arquivo.read_text(encoding="utf-8"))}
            except (ValueError, KeyError, TypeError):
                pass

    def registrar(self, *, chave: str, grupo: str, marca: str, referencia: str, novas_fotos: int,
                  situacao: str, pasta: str, observacao: str = "") -> Item:
        """Mesma pasta de novo = soma as fotos (nao cria linha repetida)."""
        item = self.itens.get(chave)
        if item is None:
            item = Item(chave, datetime.now().strftime("%H:%M"), grupo, marca, referencia, 0, situacao, pasta, observacao)
            self.itens[chave] = item
        item.fotos += novas_fotos
        if situacao == "ok":
            item.situacao = "ok"
        if observacao and observacao not in item.observacao:
            item.observacao = (item.observacao + " " + observacao).strip()
        self.salvar()
        return item

    def marcar_feito(self, chave: str, feito: bool) -> None:
        if chave in self.itens:
            self.itens[chave].feito = feito
            self.salvar()

    def ordenados(self) -> list[Item]:
        return sorted(self.itens.values(), key=lambda i: (i.feito, i.situacao != "conferir", i.hora))

    def salvar(self) -> None:
        self.arquivo.write_text(json.dumps([asdict(i) for i in self.itens.values()], ensure_ascii=False, indent=1), encoding="utf-8")
        with open(self.pasta / "lista_do_dia.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(CABECALHO)
            for i in sorted(self.itens.values(), key=lambda x: x.hora):
                w.writerow([i.hora, i.grupo, i.marca, i.referencia, i.fotos, "CONFERIR" if i.situacao == "conferir" else "ok",
                            "sim" if i.feito else "", i.pasta, i.observacao])


class Estado:
    """Mensagens ja processadas hoje (para nao baixar de novo ao reiniciar)."""

    def __init__(self, pasta_dia: Path) -> None:
        self.arquivo = Path(pasta_dia) / "estado.json"
        self.vistos: set[str] = set(json.loads(self.arquivo.read_text(encoding="utf-8"))) if self.arquivo.is_file() else set()

    def novo(self, id_msg: str) -> bool:
        return id_msg not in self.vistos

    def marcar(self, id_msg: str) -> None:
        self.vistos.add(id_msg)
        self.arquivo.write_text(json.dumps(sorted(self.vistos)), encoding="utf-8")
