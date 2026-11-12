"""Acesso ao SQLite (um unico arquivo: dados/banco.db)."""
from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

from .caminhos import BANCO, SEMENTE

ESQUEMA = """
CREATE TABLE IF NOT EXISTS produtos (
  id INTEGER PRIMARY KEY, marca TEXT, referencia TEXT, categoria TEXT, genero TEXT,
  publico TEXT CHECK (publico IN ('adulto','infantil','bebe','teen') OR publico IS NULL),
  cores TEXT, data TEXT,
  status TEXT NOT NULL DEFAULT 'pesquisando' CHECK (status IN ('pesquisando','nomes','descricao','concluido'))
);
CREATE TABLE IF NOT EXISTS pesquisas (
  id INTEGER PRIMARY KEY, produto_id INTEGER REFERENCES produtos(id), consulta TEXT, link TEXT,
  titulo_pagina TEXT, dados_json TEXT, data TEXT
);
CREATE TABLE IF NOT EXISTS sugestoes (
  id INTEGER PRIMARY KEY, produto_id INTEGER REFERENCES produtos(id), texto TEXT NOT NULL,
  caracteres INTEGER, provedor TEXT, lote INTEGER, aprovada INTEGER DEFAULT 0, motivo_rejeicao TEXT
);
CREATE TABLE IF NOT EXISTS nomes_aprovados (
  id INTEGER PRIMARY KEY, produto_id INTEGER REFERENCES produtos(id), texto TEXT NOT NULL UNIQUE, data TEXT
);
CREATE TABLE IF NOT EXISTS descricoes (
  id INTEGER PRIMARY KEY, produto_id INTEGER REFERENCES produtos(id), texto TEXT NOT NULL,
  frase_efeito TEXT, paragrafo_final TEXT, data TEXT
);
CREATE TABLE IF NOT EXISTS correcoes (
  id INTEGER PRIMARY KEY, produto_id INTEGER REFERENCES produtos(id), texto TEXT NOT NULL,
  escopo TEXT NOT NULL DEFAULT 'produto' CHECK (escopo IN ('produto','geral')), data TEXT
);
CREATE TABLE IF NOT EXISTS regras_versoes (
  id INTEGER PRIMARY KEY, data TEXT, resumo TEXT, conteudo_anterior TEXT
);
"""


def agora() -> str:
    return datetime.now().isoformat(timespec="seconds")


class Banco:
    def __init__(self, caminho: Path = BANCO):
        self.caminho = Path(caminho)
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(self.caminho)
        self.con.row_factory = sqlite3.Row
        self.con.executescript(ESQUEMA)
        self.con.commit()

    def fechar(self) -> None:
        self.con.close()

    # ---- nomes aprovados -------------------------------------------------
    def importar_semente(self, arquivo: Path = SEMENTE) -> int:
        """Importa nomes ja criados (um por linha). Ignora repetidos. Devolve quantos entraram."""
        if not Path(arquivo).is_file():
            return 0
        antes = self.total_nomes()
        with self.con:
            for linha in Path(arquivo).read_text(encoding="utf-8").splitlines():
                nome = linha.strip()
                if nome and not nome.startswith("#"):
                    self.con.execute(
                        "INSERT OR IGNORE INTO nomes_aprovados (produto_id, texto, data) VALUES (NULL, ?, ?)",
                        (nome, agora()),
                    )
        return self.total_nomes() - antes

    def total_nomes(self) -> int:
        return self.con.execute("SELECT COUNT(*) FROM nomes_aprovados").fetchone()[0]

    def listar_nomes(self, busca: str = "", limite: int = 500) -> list[str]:
        sql = "SELECT texto FROM nomes_aprovados"
        args: list = []
        if busca.strip():
            sql += " WHERE texto LIKE ?"
            args.append(f"%{busca.strip()}%")
        sql += " ORDER BY id DESC LIMIT ?"
        args.append(limite)
        return [r["texto"] for r in self.con.execute(sql, args)]

    def aprovar_nome(self, produto_id: int | None, texto: str) -> None:
        with self.con:
            self.con.execute(
                "INSERT OR IGNORE INTO nomes_aprovados (produto_id, texto, data) VALUES (?, ?, ?)",
                (produto_id, texto.strip(), agora()),
            )

    # ---- produtos --------------------------------------------------------
    def criar_produto(self, marca: str, referencia: str, categoria: str, genero: str, publico: str) -> int:
        with self.con:
            cur = self.con.execute(
                "INSERT INTO produtos (marca, referencia, categoria, genero, publico, data) VALUES (?,?,?,?,?,?)",
                (marca.strip(), referencia.strip(), categoria.strip(), genero.strip(), publico or None, agora()),
            )
        return cur.lastrowid

    def exportar_nomes(self, destino: Path) -> int:
        nomes = self.listar_nomes(limite=10**9)
        Path(destino).write_text("\n".join(reversed(nomes)) + "\n", encoding="utf-8")
        return len(nomes)
